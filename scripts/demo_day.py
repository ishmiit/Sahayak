"""Demo-day preflight: is this node ready for a live demo? One command, a checklist, then the address to give out.

  python scripts/demo_day.py                   # check everything; start the node if it is not running, then try it
  python scripts/demo_day.py --no-start        # only check (a node that is already running, or the offline parts)
  python scripts/demo_day.py --reset-counters  # also zero the console counters of a node that was already running
  python scripts/demo_day.py --stop            # stop the node this script started

What it checks, in order:
  1. Content packs: each loads and its signature verifies (the node refuses an altered pack), and how old the scam
     rules are (the phone warns after 45 days).
  2. Speech: the two Hindi voices, the English voice and both recognisers are installed, and how many fixed sentences
     are in the speech cache (a missing one is synthesised live, which is slower when many phones ask at once).
  3. The node answers, and gives the expected verdict on every demo card: the 8 messages and the 3 UPI QR codes of
     the jury kit, plus a Tamil message ("could not check"); the benefits interview starts; a cached sentence plays;
     the phone's offline packs match the node's.
  4. Zero egress: Sahayak's own outside connections and lookups (must be 0), the machine's, and the offline firewall.
  5. HTTPS: without it phones get no hold-to-talk and keep no offline copy (docs/NODE_HTTPS.md).
  6. Power and disk.
It ends with READY (or what to fix) and prints the phone address with a QR code, the console address and its PIN.
A node it starts keeps running after it exits; the smoke checks are then cleared from the console counters.
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402
import psutil  # noqa: E402

from sahayak.config import get_settings  # noqa: E402

OK, WARN, FAIL = "OK  ", "WARN", "FAIL"
RESULTS: list[tuple[str, str, str]] = []

# What each jury-kit card must get (docs/jury_kit.html builds the cards from the demo pack).
EXPECTED = {"kyc_hi": "scam", "otp_call": "scam", "upi_receive": "scam", "digital_arrest": "scam",
            "scheme_apk": "scam", "ayushman_fee": "scam", "electricity": "scam", "genuine_otp": "no_signs"}
EXPECTED_QR = {"qr_cashback": "scam", "qr_kyc": "scam", "qr_shop": "no_signs"}
TAMIL = "உங்கள் வங்கி கணக்கு இன்று முடக்கப்படும். உடனே வந்த எண்ணை இந்த நம்பருக்கு சொல்லுங்கள்."
PUBLIC_SITE = "https://roshworldwide.github.io/optum-v2/"


def report(status: str, what: str, detail: str = "") -> None:
    RESULTS.append((status, what, detail))
    print(f"  [{status}] {what}" + (f": {detail}" if detail else ""), flush=True)


def section(title: str) -> None:
    print(f"\n{title}", flush=True)


# ---------------------------------------------------------------- 1. packs

def check_packs() -> None:
    section("1. Content packs")
    from sahayak.packs import get_pack, installed_packs, require_signed
    try:
        packs = installed_packs()
    except Exception as e:  # noqa: BLE001  (an altered pack raises; the node would refuse it too)
        report(FAIL, "content packs", f"{type(e).__name__}: {e}")
        return
    for p in packs:
        if p["signed_by"]:
            report(OK, f"{p['name']} {p['version']} ({p['date']})", f"signed by {p['signed_by']}")
        else:
            report(FAIL if require_signed() else WARN, f"{p['name']} {p['version']} ({p['date']})",
                   "unsigned (python scripts/sign_packs.py)")
    age = (dt.date.today() - dt.date.fromisoformat(get_pack("fraud").date)).days
    report(OK if age <= 45 else WARN, "scam rules age", f"{age} days (phones show a warning after 45)")


# ---------------------------------------------------------------- 2. speech

def check_speech() -> None:
    section("2. Speech")
    from sahayak.voice.asr import MODELS
    from sahayak.voice.speech import speakable
    from sahayak.voice.tts import VOICES, Speaker
    s = get_settings()
    for lang, voice in (("hi", "female"), ("hi", "male"), ("en", "female")):
        model = VOICES[lang][voice]
        there = (s.models_dir / model).is_dir()
        report(OK if there else (FAIL if lang == "hi" and voice == "female" else WARN),
               f"voice {lang}/{voice}", model if there else "missing (python scripts/get_models.py)")
    for lang, model in MODELS.items():
        there = (s.models_dir / model).is_dir()
        report(OK if there else (FAIL if lang == "hi" else WARN), f"speech recogniser {lang}",
               model if there else "missing (python scripts/get_models.py)")
    sys.path.insert(0, str(ROOT / "scripts"))
    from build_speech_cache import collect
    cache = s.data_dir / "tts_cache"
    want = have = 0
    for lang, texts in collect().items():
        voices = ("female", "male") if lang == "hi" else ("female",)
        for voice in voices:
            model = VOICES[lang][voice]
            if not (s.models_dir / model).is_dir():
                continue
            for text in texts:
                spoken = speakable(text, lang).rstrip("।. ")
                if not spoken:
                    continue
                want += 1
                have += (cache / f"{Speaker.key(model, 0.9, spoken)}.wav").exists()
    if want == 0:
        report(WARN, "speech cache", "no voices installed, nothing to cache")
    else:
        missing = want - have
        report(OK if missing == 0 else WARN, "speech cache", f"{have} of {want} fixed sentences ready"
               + (f"; {missing} would be synthesised live (python scripts/build_speech_cache.py)" if missing else ""))


# ---------------------------------------------------------------- 3. the node

def base_url() -> str:
    s = get_settings()
    return f"{'https' if s.tls_cert else 'http'}://127.0.0.1:{s.port}"


def node_up(client: httpx.Client) -> dict | None:
    try:
        r = client.get(base_url() + "/api/health", timeout=3)
        return r.json() if r.status_code == 200 else None
    except httpx.HTTPError:
        return None


def pid_file() -> Path:
    return get_settings().data_dir / "demo_node.pid"


def start_node(pin: str) -> None:
    s = get_settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    log = open(s.data_dir / "demo_node.log", "ab")  # noqa: SIM115  (the node keeps it open)
    env = {**os.environ, "SAHAYAK_CONSOLE_PIN": pin}
    kwargs: dict = {"stdout": log, "stderr": subprocess.STDOUT, "cwd": str(ROOT), "env": env}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen([sys.executable, "-m", "sahayak"], **kwargs)
    pid_file().write_text(str(proc.pid), encoding="utf-8")
    print(f"  started the node (pid {proc.pid}; log {s.data_dir / 'demo_node.log'})", flush=True)


def stop_node() -> int:
    try:
        pid = int(pid_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        print("no node started by this script (no pid file)")
        return 1
    try:
        proc = psutil.Process(pid)
        proc.terminate()
        proc.wait(timeout=10)
        print(f"stopped the node (pid {pid})")
    except psutil.NoSuchProcess:
        print(f"the node (pid {pid}) was not running")
    except psutil.TimeoutExpired:
        proc.kill()
        print(f"killed the node (pid {pid})")
    pid_file().unlink(missing_ok=True)
    return 0


def check_node(client: httpx.Client, health: dict) -> dict:
    section("3. The node answers, with the expected verdict on every demo card")
    url = base_url()
    report(OK, "node", f"version {health.get('version')}, up {health.get('uptime_s')} s")
    llm = health.get("llm") or {}
    backend = llm.get("backend") or llm.get("name") or "none"
    report(OK if backend in ("none", None) else WARN, "language model",
           "off (the default)" if backend in ("none", None) else f"{backend} on: explanations wait for it")
    from sahayak.packs import get_pack
    demo = get_pack("demo").data
    for ex in demo.get("examples", []):
        want = EXPECTED.get(ex["id"])
        try:
            card = client.post(url + "/api/check", json={"text": ex["text"], "sender": ex.get("sender"),
                                                         "input_type": ex.get("input_type", "text")}, timeout=15).json()
            got = card.get("verdict")
        except (httpx.HTTPError, ValueError) as e:
            got = f"error {type(e).__name__}"
        report(OK if want is None or got == want else FAIL, f"card {ex['id']}", got if want is None else
               (got if got == want else f"got {got}, expected {want}"))
    for ex in demo.get("qr_examples", []):
        want = EXPECTED_QR.get(ex["id"])
        try:
            png = client.get(url + f"/api/demo/qr/{ex['id']}", timeout=15).content
            got = client.post(url + "/api/qr", content=png, headers={"Content-Type": "image/png"},
                              timeout=30).json().get("verdict")
        except (httpx.HTTPError, ValueError) as e:
            got = f"error {type(e).__name__}"
        report(OK if want is None or got == want else FAIL, f"QR card {ex['id']}",
               got if got == want else f"got {got}, expected {want}")
    try:
        got = client.post(url + "/api/check", json={"text": TAMIL}, timeout=15).json().get("verdict")
    except (httpx.HTTPError, ValueError) as e:
        got = f"error {type(e).__name__}"
    report(OK if got == "unreadable" else FAIL, "a Tamil message", "could not check" if got == "unreadable" else
           f"got {got}, expected unreadable")
    try:
        q = client.post(url + "/api/navigator/next", json={"answers": {}}, timeout=15).json()
        first = (q.get("question") or {}).get("text", {}).get("hi") or (q.get("question") or {}).get("id")
        report(OK if first else FAIL, "benefits interview", f"first question: {first}" if first else str(q)[:120])
    except (httpx.HTTPError, ValueError) as e:
        report(FAIL, "benefits interview", f"error {type(e).__name__}")
    hi_voices = (health.get("voice") or {}).get("tts", {}).get("hi", [])
    if hi_voices:
        label = get_pack("fraud").data["verdicts"]["scam"]["label"]["hi"]
        try:
            t0 = time.perf_counter()
            r = client.post(url + "/api/tts", json={"text": label, "lang": "hi"}, timeout=60)
            ms = (time.perf_counter() - t0) * 1000
            cached = r.headers.get("X-Sahayak-Cached", "?")
            ok = r.status_code == 200 and r.content[:4] == b"RIFF"
            report(OK if ok and ms < 1500 else WARN, "speech reply", f"{ms:.0f} ms ({cached})" if ok else
                   f"HTTP {r.status_code}")
        except httpx.HTTPError as e:
            report(FAIL, "speech reply", f"error {type(e).__name__}")
    try:
        phone = client.get(url + "/phone-packs/fraud.json", timeout=15).json()
        node_v = get_pack("fraud").version
        report(OK if phone.get("version") == node_v else FAIL, "the phone's offline scam rules",
               f"{phone.get('version')} (node {node_v})")
    except (httpx.HTTPError, ValueError) as e:
        report(WARN, "the phone's offline scam rules", f"error {type(e).__name__}")
    try:
        return client.get(url + "/api/status", timeout=15).json()
    except (httpx.HTTPError, ValueError):
        return {}


# ---------------------------------------------------------------- 4. egress

def check_egress(client: httpx.Client) -> None:
    section("4. Zero egress")
    snap: dict = {}
    for _ in range(12):  # the firewall reading runs in the background on the node; give it a few seconds
        try:
            snap = client.get(base_url() + "/api/egress", timeout=15).json()
        except (httpx.HTTPError, ValueError):
            break
        if (snap.get("firewall") or {}).get("detail") != "checking…":
            break
        time.sleep(2)
    if not snap:
        report(FAIL, "egress", "the node did not answer /api/egress")
        return
    own = snap.get("sahayak", {})
    n = own.get("external_connects", 0) + own.get("external_lookups", 0)
    report(OK if n == 0 and own.get("watching") else FAIL, "Sahayak's own outside connections and lookups",
           f"{n}" + ("" if own.get("watching") else " (the audit hook is not installed)"))
    machine = snap.get("machine", {})
    ext = machine.get("external")
    if ext is None:
        report(WARN, "this machine's outside connections", "cannot read (run as administrator to see them)")
    else:
        report(OK if ext == 0 else WARN, "this machine's outside connections",
               f"{ext}" + ("" if ext == 0 else "; fine while setting up, switch the uplink off before the demo"))
    fw = snap.get("firewall", {})
    on = fw.get("offline_rules")
    report(OK if on else WARN, "offline firewall", "in place" if on else
           f"{fw.get('detail', 'not in place')} (scripts/firewall/ for this system)")


# ---------------------------------------------------------------- 5-6. https, power, disk

def check_https_power_disk() -> None:
    section("5. HTTPS, power and disk")
    s = get_settings()
    if s.tls_cert:
        there = Path(s.tls_cert).is_file() and Path(s.tls_key).is_file()
        report(OK if there and s.public_host else FAIL, "HTTPS", f"https://{s.public_host}:{s.port}/" if there else
               "certificate or key file missing (docs/NODE_HTTPS.md)")
    else:
        report(WARN, "HTTPS", "plain HTTP: phones get no hold-to-talk (they fall back to the recorder app) and keep "
               f"no offline copy. Speak on the node's own browser, use {PUBLIC_SITE} for offline phone checks, or "
               "set up docs/NODE_HTTPS.md")
    battery = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    if battery is not None:
        report(OK if battery.power_plugged or battery.percent >= 80 else WARN, "power",
               f"{battery.percent:.0f}%" + (", plugged in" if battery.power_plugged else ", on battery: plug it in"))
    free_gb = shutil.disk_usage(s.data_dir if s.data_dir.exists() else s.home).free / 1e9
    report(OK if free_gb >= 2 else WARN, "free disk", f"{free_gb:.1f} GB")


# ---------------------------------------------------------------- the end

def reset_counters(client: httpx.Client, pin: str) -> None:
    try:
        r = client.post(base_url() + "/api/console/login", json={"pin": pin}, timeout=10)
        if r.status_code != 200:
            report(WARN, "console counters", f"login refused (HTTP {r.status_code}); not reset")
            return
        r = client.post(base_url() + "/api/console/counters/reset", timeout=10)
        report(OK if r.status_code == 200 else WARN, "console counters", "zeroed for the demo" if r.status_code == 200
               else f"reset refused (HTTP {r.status_code})")
    except httpx.HTTPError as e:
        report(WARN, "console counters", f"error {type(e).__name__}")


def show_addresses(status: dict, pin: str | None) -> None:
    app_url = status.get("app_url")
    if not app_url:
        return
    print(f"\nPhones (on the node's Wi-Fi): {app_url}")
    print(f"Operator console: {app_url}app/console.html" + (f"   PIN {pin}" if pin else "   (PIN: printed in the node's log)"))
    print(f"Node page (zero egress, live): {app_url}app/node.html")
    try:
        import qrcode
        qr = qrcode.QRCode(border=1)
        qr.add_data(app_url)
        qr.print_ascii(invert=True)
    except (ImportError, UnicodeEncodeError):
        pass


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")  # a Windows console without UTF-8 still prints the checklist
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--no-start", action="store_true", help="do not start the node if it is not running")
    ap.add_argument("--reset-counters", action="store_true", help="zero the console counters of a running node")
    ap.add_argument("--pin", help="console PIN for a node this script starts (default: SAHAYAK_CONSOLE_PIN or random)")
    ap.add_argument("--stop", action="store_true", help="stop the node this script started, then exit")
    args = ap.parse_args()
    if args.stop:
        return stop_node()

    print(f"Sahayak demo-day preflight, {dt.datetime.now():%d %b %Y %H:%M}")
    check_packs()
    check_speech()

    status: dict = {}
    pin = os.environ.get("SAHAYAK_CONSOLE_PIN")
    started = False
    with httpx.Client(verify=False) as client:  # the node's certificate names its public host, not 127.0.0.1
        health = node_up(client)
        if health is None and not args.no_start:
            pin = args.pin or pin or f"{secrets.randbelow(10**6):06d}"
            start_node(pin)
            started = True
            for _ in range(90):
                time.sleep(1)
                health = node_up(client)
                if health:
                    break
        if health is None:
            section("3. The node")
            report(FAIL, "node", f"not answering at {base_url()}" + (" (see the log above)" if started else
                   " (start it: python -m sahayak, or run this without --no-start)"))
        else:
            status = check_node(client, health)
            check_egress(client)
        check_https_power_disk()
        if health is not None and (started or args.reset_counters):
            if args.reset_counters and not pin:
                pin = input("Console PIN (printed when the node started): ").strip()
            if pin:
                reset_counters(client, pin)

    fails = [r for r in RESULTS if r[0] == FAIL]
    warns = [r for r in RESULTS if r[0] == WARN]
    print()
    if fails:
        print(f"NOT READY: {len(fails)} to fix" + (f", {len(warns)} warnings" if warns else ""))
        for _, what, detail in fails:
            print(f"  - {what}: {detail}")
    else:
        print("READY" + (f" ({len(warns)} warnings above)" if warns else ""))
    show_addresses(status, pin)
    if started:
        print("\nThe node keeps running. Stop it with: python scripts/demo_day.py --stop")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
