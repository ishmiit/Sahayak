"""Stress test a Sahayak node the way a busy counter or a jury table would: many phones at once, bursts of checks,
speech for everyone at the same moment, a long soak watching memory, and hostile input on every endpoint.

It starts its own node on a free port (a throw-away SAHAYAK_HOME; speech models from SAHAYAK_MODELS or the usual
~/.sahayak/models), runs the scenarios, stops the node, and writes bench/results/stress_v0.json and .md.

  python bench/stress/run_stress.py [--quick] [--report]

Scenarios (each phone is an asyncio client; the node is one process, as on a CSC laptop):
  session N  N phones each: open the app, examples, check 3 benchmark messages and ask for the explanation,
             a full benefits interview, one spoken reply (a sentence the node has not said before)
  burst N    N checks sent at the same instant
  tts N      N new sentences to speak at the same instant (the slowest thing a node does)
  asr N      N recordings to recognise at the same instant
  soak N     N checks, 20 at a time, with the node's memory measured before and after
  fuzz       malformed and oversized input on every endpoint, path traversal, console without a login, PIN guessing
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import io
import json
import os
import platform
import random
import socket
import statistics
import struct
import subprocess
import sys
import tempfile
import time
import wave
import zlib
from pathlib import Path

import httpx
import psutil

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "bench" / "results"
MSGS = [json.loads(line) for line in (ROOT / "bench/scambench/scambench_v0.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
PERSONAS = [json.loads(line) for line in (ROOT / "bench/schemebench/schemebench_v1.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
PIN = "246810"


# ---------------------------------------------------------------- the node

def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_node(models: Path | None) -> tuple[subprocess.Popen, str, Path]:
    home = Path(tempfile.mkdtemp(prefix="sahayak-stress-"))
    port = free_port()
    env = dict(os.environ, SAHAYAK_HOME=str(home), SAHAYAK_PORT=str(port), SAHAYAK_HOST="127.0.0.1",
               SAHAYAK_CONSOLE_PIN=PIN, SAHAYAK_LLM="none")
    if models:
        env["SAHAYAK_MODELS"] = str(models)
    log = open(home / "node.log", "w")  # noqa: SIM115 - closed with the process
    proc = subprocess.Popen([sys.executable, "-m", "sahayak"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    for _ in range(120):
        try:
            if httpx.get(f"{base}/api/health", timeout=1).status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    else:
        proc.kill()
        raise SystemExit(f"node did not start; see {home / 'node.log'}")
    time.sleep(6)  # the warm-up thread loads the models
    return proc, base, home


def rss_mb(pid: int) -> float:
    return round(psutil.Process(pid).memory_info().rss / 1e6, 1)


# ---------------------------------------------------------------- load

class Load:
    def __init__(self):
        self.lat: dict[str, list[float]] = {}
        self.errors: dict[str, int] = {}

    async def call(self, client, name, method, url, **kw):
        t0 = time.perf_counter()
        try:
            r = await client.request(method, url, **kw)
            ok = r.status_code < 400
        except httpx.HTTPError as e:
            ok, r = False, e
        self.lat.setdefault(name, []).append((time.perf_counter() - t0) * 1000)
        if not ok:
            self.errors[name] = self.errors.get(name, 0) + 1
        return r

    def summary(self) -> dict:
        out = {}
        for k, v in self.lat.items():
            v = sorted(v)
            out[k] = {"n": len(v), "p50_ms": round(statistics.median(v)), "p95_ms": round(v[min(len(v) - 1, int(0.95 * len(v)))]),
                      "max_ms": round(v[-1]), "errors": self.errors.get(k, 0)}
        return out


def wav_bytes(seconds: float = 1.5, rate: int = 16000) -> bytes:
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(rate)
        w.writeframes(bytes(int(seconds * rate) * 2))
    return b.getvalue()


async def session(load: Load, client, i: int):
    await load.call(client, "page", "GET", "/")
    await load.call(client, "health", "GET", "/api/health")
    await load.call(client, "examples", "GET", "/api/examples")
    for m in random.sample(MSGS, 3):
        r = await load.call(client, "check", "POST", "/api/check", json={"text": m["text"], "lang": "hi"})
        if isinstance(r, httpx.Response) and r.status_code == 200:
            await load.call(client, "explain", "POST", "/api/explain", json={"id": r.json()["id"]})
    persona, answers = random.choice(PERSONAS), {}
    while True:
        r = await load.call(client, "nav next", "POST", "/api/navigator/next", json={"answers": answers})
        if not isinstance(r, httpx.Response) or r.status_code != 200 or r.json()["done"]:
            break
        q = r.json()["question"]
        answers[q["id"]] = persona["answers"][q["id"]]
    await load.call(client, "nav result", "POST", "/api/navigator/result", json={"answers": answers, "session": f"s{i}", "lang": "hi"})
    await load.call(client, "speech (new)", "POST", "/api/tts", json={"text": f"यह ठगी है। {random.randint(1, 10**6)} पर कॉल न करें।", "lang": "hi"})


async def scenario(base: str, pid: int, name: str, n: int) -> dict:
    load = Load()
    limits = httpx.Limits(max_connections=500, max_keepalive_connections=500)
    async with httpx.AsyncClient(base_url=base, timeout=120, limits=limits) as client:
        rss0, t0 = rss_mb(pid), time.perf_counter()
        if name == "session":
            await asyncio.gather(*(session(load, client, i) for i in range(n)))
        elif name == "burst":
            await asyncio.gather(*(load.call(client, "check", "POST", "/api/check", json={"text": random.choice(MSGS)["text"]})
                                   for _ in range(n)))
        elif name == "tts":
            await asyncio.gather(*(load.call(client, "speech (new)", "POST", "/api/tts",
                                             json={"text": f"आपकी उम्र {random.randint(1, 10**6)} है, क्या यह सही है?", "lang": "hi"})
                                   for _ in range(n)))
        elif name == "asr":
            wav = wav_bytes()
            await asyncio.gather(*(load.call(client, "recognise", "POST", "/api/asr?lang=hi&question=age", content=wav,
                                             headers={"Content-Type": "audio/wav"}) for _ in range(n)))
        elif name == "soak":
            sem = asyncio.Semaphore(20)

            async def one():
                async with sem:
                    await load.call(client, "check", "POST", "/api/check",
                                    json={"text": random.choice(MSGS)["text"] + f" {random.random()}"})
            await asyncio.gather(*(one() for _ in range(n)))
        wall = time.perf_counter() - t0
    out = {"scenario": name, "n": n, "wall_s": round(wall, 2), "rss_before_mb": rss0, "rss_after_mb": rss_mb(pid),
           "endpoints": load.summary()}
    print(f"{name} x{n}: wall {wall:.1f} s, RSS {rss0} -> {out['rss_after_mb']} MB, "
          + ", ".join(f"{k} p50 {v['p50_ms']} / p95 {v['p95_ms']} / max {v['max_ms']} ms, {v['errors']} errors"
                      for k, v in out["endpoints"].items()), flush=True)
    return out


# ---------------------------------------------------------------- hostile input

def png_declaring(width: int, height: int) -> bytes:
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    rows = zlib.compress(b"".join(b"\x00" * (width + 1) for _ in range(height)), 9)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
            + chunk(b"IDAT", rows) + chunk(b"IEND", b""))


def fuzz(base: str, pid: int) -> dict:
    c = httpx.Client(base_url=base, timeout=60)
    cases, bad = 0, []

    def expect(what, method, url, ok, **kw):
        nonlocal cases
        cases += 1
        try:
            r = c.request(method, url, **kw)
            code = r.status_code
        except httpx.HTTPError as e:
            code = type(e).__name__
        if code not in ok:
            bad.append({"case": what, "got": code})
        return code

    rnd = random.Random(7)
    for i in range(300):  # Unicode soup of every length
        t = "".join(chr(rnd.choice([rnd.randint(32, 126), rnd.randint(0x900, 0x97F), rnd.randint(0xA0, 0xD7FF)]))
                    for _ in range(rnd.randint(1, 600))).strip() or "x"
        expect(f"check soup {i}", "POST", "/api/check", {200, 422}, json={"text": t, "sender": t[:40]})
    for body, what in [({"text": ""}, "empty"), ({"text": "a" * 4001}, "4001 chars"), ({}, "no text"), ({"text": 5}, "number"),
                       ({"text": "x", "input_type": "fax"}, "bad type"), ({"text": "x", "lang": "fr"}, "bad lang")]:
        expect(f"check {what}", "POST", "/api/check", {422}, json=body)
    expect("check not json", "POST", "/api/check", {400, 422}, content=b"{not json", headers={"Content-Type": "application/json"})
    expect("check 20,000-deep json", "POST", "/api/check", {400, 422}, content=b"[" * 20000 + b"]" * 20000,
           headers={"Content-Type": "application/json"})
    for ep in ("/api/navigator/next", "/api/navigator/result"):
        for body in [{"answers": {"nope": 1}}, {"answers": {"age": "old"}}, {"answers": {"age": 10**30}}, {"answers": []},
                     {"answers": {f"k{i}": i for i in range(5000)}}]:
            expect(f"{ep} odd answers", "POST", ep, {200, 422}, json=body)
    for body, ok in [({"text": "।।।"}, {422, 503}), ({"text": "x" * 600}, {200, 503}), ({"text": "a", "speed": 9}, {422})]:
        expect("tts odd text", "POST", "/api/tts", ok, json=body)
    for body, what in [(b"", "empty"), (os.urandom(5000), "random bytes"), (b"RIFF" + b"\xff" * 40, "broken header")]:
        expect(f"asr {what}", "POST", "/api/asr?lang=hi", {422}, content=body)
    expect("asr 3 MB", "POST", "/api/asr?lang=hi", {413}, content=b"\x00" * (3 * 1024 * 1024))
    bomb = png_declaring(12000, 12000)  # 144 megapixels in about 140 KB
    memory = {}
    for ep in ("/api/qr", "/api/ocr"):
        for body, what, ok in [(b"", "empty", {422, 503}), (os.urandom(10000), "random", {422, 503}), (b"\x00" * (9 * 1024 * 1024), "9 MB", {413})]:
            expect(f"{ep} {what}", "POST", ep, ok, content=body)
        before = rss_mb(pid)
        expect(f"{ep} decompression bomb", "POST", ep, {413, 422}, content=bomb)
        memory[f"{ep} bomb"] = round(rss_mb(pid) - before, 1)
    for ep in ("/api/qr", "/api/asr", "/api/check"):
        before = rss_mb(pid)
        expect(f"{ep} 200 MB body", "POST", ep, {413}, content=b"x" * (200 * 1024 * 1024),
               headers={"Content-Type": "application/json" if ep == "/api/check" else "application/octet-stream"})
        memory[f"{ep} 200 MB body"] = round(rss_mb(pid) - before, 1)
    leaks = 0
    for path in ["/app/..%2f..%2fsahayak/server.py", "/app/%2e%2e/%2e%2e/etc/passwd", "/app/.git/config",
                 "/phone-packs/..%2fkeys%2fsahayak-packs.json", "/phone-packs/keys.json", "/docs", "/openapi.json"]:
        cases += 1
        r = c.get(path)
        if any(s in r.text for s in ("PRIVATE KEY", "root:", "def api_", "[core]")):
            leaks += 1
            bad.append({"case": f"GET {path}", "got": "leak"})
    for m, path in [("GET", "/api/console/queue"), ("GET", "/api/console/caselog"), ("POST", "/api/console/delete-everything"),
                    ("GET", "/api/console/export"), ("POST", "/api/console/counters/reset")]:
        expect(f"{m} {path} without a login", m, path, {401})
    codes = []
    for i in range(12):
        cases += 1
        codes.append(c.post("/api/console/login", json={"pin": f"{i:04d}99"}).status_code)
    locked = codes[5:] == [429] * (len(codes) - 5)
    if not locked:
        bad.append({"case": "PIN guessing locks the console after 5 tries", "got": codes})
    alive = c.get("/api/health").status_code == 200
    headers = {k.lower() for k in c.get("/").headers}
    missing = [h for h in ("content-security-policy", "x-content-type-options", "referrer-policy") if h not in headers]
    out = {"cases": cases, "unexpected": bad, "path_leaks": leaks, "memory_growth_mb": memory, "pin_lockout_after": 5 if locked else None,
           "node_alive_after": alive, "security_headers_missing": missing}
    print(f"fuzz: {cases} cases, {len(bad)} unexpected, leaks {leaks}, node alive {alive}, memory {memory}", flush=True)
    return out


# ---------------------------------------------------------------- a low-end phone

def low_end_phone(base: str) -> dict | None:
    """Chromium as a slow Android phone (CPU 6x slower, DevTools "Slow 3G"): the first visit, the on-phone check
    (the first one includes starting the engine), a second check, and a benefits result."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    scam = ("Dear customer your SBI account KYC has expired. Update immediately or your account will be blocked today: "
            "http://sbi-kyc-update.xyz")
    out: dict = {"cpu_slowdown": 6, "network": "400 ms RTT, 400 kbit/s"}
    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 360, "height": 740}, device_scale_factor=2, is_mobile=True, has_touch=True)
        page = ctx.new_page()
        cdp = ctx.new_cdp_session(page)
        cdp.send("Emulation.setCPUThrottlingRate", {"rate": 6})
        cdp.send("Network.enable")
        cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 400, "downloadThroughput": 50000,
                                                      "uploadThroughput": 50000})
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        t0 = time.perf_counter()
        page.goto(base + "/?lang=en", wait_until="load")
        out["first_visit_s"] = round(time.perf_counter() - t0, 1)
        page.wait_for_function("""caches.keys().then(ks => Promise.all(ks.map(k => caches.open(k).then(c => c.keys()))))
            .then(l => l.flat().filter(r => r.url.includes('phone-packs')).length >= 5)""", timeout=180000)
        out["offline_ready_s"] = round(time.perf_counter() - t0, 1)
        ctx.set_offline(True)  # away from the node: the phone answers
        for key, text in (("first_check_s", scam), ("second_check_s", scam + " now")):
            page.goto(base + "/?lang=en&screen=check", wait_until="load")
            page.wait_for_selector("#msg", state="visible", timeout=60000)
            page.fill("#msg", text)
            t1 = time.perf_counter()
            page.click("#btn-check")
            page.wait_for_selector("#verdict.scam", timeout=60000)
            out[key] = round(time.perf_counter() - t1, 2)
        t2 = time.perf_counter()
        page.goto(base + "/?nav=senior74", wait_until="load")
        page.wait_for_selector('[data-screen="benefits-result"]:not([hidden]) .scheme', timeout=60000)
        out["benefits_result_s"] = round(time.perf_counter() - t2, 2)
        out["js_errors"] = errors
        browser.close()
    print(f"low-end phone: {out}", flush=True)
    return out


# ---------------------------------------------------------------- report

def render(res: dict) -> str:
    md = ["# Stress test v0", "",
          f"{res['date']} on {res['machine']}. One node process, as on a CSC laptop; every phone is a client on the same "
          "machine. Reproduce: `python bench/stress/run_stress.py --report`.", "",
          "| Scenario | Wall time | Endpoint | p50 | p95 | Slowest | Errors | Node memory |", "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for s in res["load"]:
        first = True
        for ep, v in s["endpoints"].items():
            md.append(f"| {s['scenario']} × {s['n']} | {s['wall_s']} s | {ep} | {v['p50_ms']} ms | {v['p95_ms']} ms | {v['max_ms']} ms | "
                      f"{v['errors']} | {s['rss_before_mb']} → {s['rss_after_mb']} MB |" if first else
                      f"| | | {ep} | {v['p50_ms']} ms | {v['p95_ms']} ms | {v['max_ms']} ms | {v['errors']} | |")
            first = False
    f = res["fuzz"]
    md += ["", f"Hostile input: {f['cases']} cases, {len(f['unexpected'])} unexpected answers, {f['path_leaks']} files leaked, "
           f"node still answering: {'yes' if f['node_alive_after'] else 'NO'}. The console locks after "
           f"{f['pin_lockout_after']} wrong PINs. Memory growth from a 144-megapixel PNG of 140 KB and from 200 MB bodies: "
           + ", ".join(f"{k} {v:+} MB" for k, v in f["memory_growth_mb"].items()) + "."]
    if f["unexpected"]:
        md += ["", "Unexpected answers:", ""] + [f"- {u['case']}: {u['got']}" for u in f["unexpected"]]
    ph = res.get("phone")
    if ph:
        md += ["", f"A low-end phone (Chromium, CPU {ph['cpu_slowdown']}× slower, {ph['network']}): first visit "
               f"{ph['first_visit_s']} s, ready to work offline after {ph['offline_ready_s']} s; offline, the first scam check took "
               f"{ph['first_check_s']} s from tap to verdict (it starts the engine), the next {ph['second_check_s']} s; a benefits "
               f"result {ph['benefits_result_s']} s. Script errors: {len(ph['js_errors'])}."]
    md += ["", "**What this does not show.** The clients run on the node's own machine, so Wi-Fi is not part of the "
           "test; a travel router serving 30 phones adds its own delay. Speech numbers are for sentences the node has not "
           "said before; the fixed sentences of every screen are made ahead of time (scripts/build_speech_cache.py) and "
           "play from disk."]
    return "\n".join(md) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="smaller numbers, for a quick check")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--models", type=Path, default=Path(os.environ["SAHAYAK_MODELS"]) if os.environ.get("SAHAYAK_MODELS")
                    else Path.home() / ".sahayak" / "models")
    args = ap.parse_args()
    random.seed(7)
    plan = [("session", 30), ("burst", 300), ("tts", 20), ("asr", 10), ("soak", 5000)]
    if args.quick:
        plan = [("session", 5), ("burst", 50), ("tts", 4), ("asr", 2), ("soak", 500)]
    proc, base, home = start_node(args.models if args.models.is_dir() else None)
    try:
        load = [asyncio.run(scenario(base, proc.pid, name, n)) for name, n in plan]
        hostile = fuzz(base, proc.pid)
        phone = low_end_phone(base)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
    try:
        chip = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True, text=True).stdout.strip()
    except OSError:
        chip = ""
    res = {"date": dt.date.today().isoformat(), "machine": f"{chip or platform.processor()}, {os.cpu_count()} cores, "
           f"{round(psutil.virtual_memory().total / 2**30)} GB", "load": load, "fuzz": hostile, "phone": phone}
    if args.report:
        (RESULTS / "stress_v0.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        (RESULTS / "stress_v0.md").write_text(render(res), encoding="utf-8")
        print(f"wrote {RESULTS / 'stress_v0.md'}")
    ok = not hostile["unexpected"] and hostile["node_alive_after"] and not (phone and phone["js_errors"]) and all(
        v["errors"] == 0 for s in load for v in s["endpoints"].values())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
