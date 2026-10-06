"""The node around the app: captive DNS, HTTPS redirect, zero-egress counting, signed packs."""
import asyncio
import shutil
import socket
import struct
import sys
import threading

import pytest
from fastapi.testclient import TestClient

from sahayak.config import REPO_ROOT, get_settings
from sahayak.node import dns, egress
from sahayak.node.redirect import make_redirect_app
from sahayak.packs import get_pack, install, installed_packs, load_pack_file, rollback
from sahayak.server import app
from sahayak.signing import PackSignatureError

client = TestClient(app)


def dns_query(name: str, qtype: int = 1) -> bytes:
    qname = b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\x00"
    return struct.pack(">HHHHHH", 0x1234, 0x0100, 1, 0, 0, 0) + qname + struct.pack(">HH", qtype, 1)


# ---------------------------------------------------------------- captive DNS

def test_every_name_resolves_to_the_node():
    for name in ("connectivitycheck.gstatic.com", "captive.apple.com", "www.msftconnecttest.com", "sbi.co.in"):
        reply = dns.response(dns_query(name), "10.0.0.2")
        tid, flags, qd, an = struct.unpack(">HHHH", reply[:8])
        assert tid == 0x1234 and flags & 0x8000 and qd == 1 and an == 1
        assert reply.endswith(socket.inet_aton("10.0.0.2"))


def test_ipv6_and_junk_queries():
    reply = dns.response(dns_query("example.com", qtype=28), "10.0.0.2")  # AAAA: no answer, so phones use IPv4
    assert struct.unpack(">H", reply[6:8])[0] == 0
    assert dns.response(b"\x00\x01garbage", "10.0.0.2") is None
    answer = dns.response(dns_query("a.b"), "10.0.0.2")
    assert dns.response(answer, "10.0.0.2") is None  # never answers a response


def test_dns_server_over_udp():
    srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    srv.bind(("127.0.0.1", 0))
    port = srv.getsockname()[1]

    def once():
        data, addr = srv.recvfrom(512)
        srv.sendto(dns.response(data, "192.168.4.1"), addr)

    threading.Thread(target=once, daemon=True).start()
    cli = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cli.settimeout(5)
    cli.sendto(dns_query("clients3.google.com"), ("127.0.0.1", port))
    reply, _ = cli.recvfrom(512)
    assert reply.endswith(socket.inet_aton("192.168.4.1"))
    cli.close()
    srv.close()


# ---------------------------------------------------------------- HTTPS redirect

def call_asgi(app_, path, query=b""):
    sent = []

    async def receive():
        return {"type": "http.request"}

    async def send(msg):
        sent.append(msg)

    asyncio.run(app_({"type": "http", "path": path, "query_string": query}, receive, send))
    headers = dict(sent[0]["headers"])
    return sent[0]["status"], headers[b"location"].decode()


def test_plain_http_redirects_to_https_and_probes_land_on_the_app():
    redirect = make_redirect_app("sahayak.example.in", 443)
    assert call_asgi(redirect, "/generate_204") == (302, "https://sahayak.example.in/")
    assert call_asgi(redirect, "/hotspot-detect.html") == (302, "https://sahayak.example.in/")
    assert call_asgi(redirect, "/app/node.html", b"x=1") == (302, "https://sahayak.example.in/app/node.html?x=1")
    assert call_asgi(make_redirect_app("n.in", 8443), "/")[1] == "https://n.in:8443/"


# ---------------------------------------------------------------- zero egress

@pytest.mark.parametrize("host,local", [
    ("127.0.0.1", True), ("10.0.0.2", True), ("192.168.29.246", True), ("172.20.1.1", True), ("169.254.3.4", True),
    ("::1", True), ("fe80::1%eth0", True), ("localhost", True), ("8.8.8.8", False), ("2404:6800::1", False),
    ("api.example.com", False),
])
def test_what_counts_as_local(host, local):
    assert egress.is_local(host) is local


def test_outbound_attempts_by_the_node_are_counted():
    egress.install()
    before = egress.snapshot()["sahayak"]
    sys.audit("socket.connect", None, ("8.8.8.8", 53))  # what Python raises on a real connect, without the network
    sys.audit("socket.getaddrinfo", "updates.example.com", 443, 0, 0, 0, 0)
    sys.audit("socket.connect", None, ("127.0.0.1", 11434))  # the local model: fine
    after = egress.snapshot()["sahayak"]
    assert after["external_connects"] == before["external_connects"] + 1
    assert after["external_lookups"] == before["external_lookups"] + 1
    assert after["local_connects"] >= before["local_connects"] + 1
    assert after["recent_external"][-1]["host"] == "updates.example.com"


def test_egress_and_status_endpoints():
    e = client.get("/api/egress").json()
    assert {"sahayak", "machine", "interfaces", "firewall"} <= set(e) and e["sahayak"]["watching"]
    s = client.get("/api/status").json()
    assert {p["name"] for p in s["packs"]} >= {"fraud", "schemes", "voice"}
    assert s["app_qr"].startswith("data:image/png;base64,") and s["app_url"].startswith("http")


# ---------------------------------------------------------------- signed packs

def test_every_pack_in_the_repo_is_signed_by_the_team_key():
    for p in installed_packs():
        assert p["signed_by"] == "sahayak-packs", f"{p['file']}: run python scripts/sign_packs.py"


@pytest.fixture
def temp_packs(tmp_path, monkeypatch):
    """A copy of the packs folder (with signatures and the public key) the tests may tamper with."""
    packs = tmp_path / "packs"
    shutil.copytree(REPO_ROOT / "packs", packs, ignore=shutil.ignore_patterns(".previous"))
    monkeypatch.setenv("SAHAYAK_PACKS", str(packs))
    get_settings.cache_clear()
    get_pack.cache_clear()
    yield packs
    monkeypatch.delenv("SAHAYAK_PACKS")
    get_settings.cache_clear()
    get_pack.cache_clear()


def test_an_altered_pack_is_refused(temp_packs):
    f = temp_packs / "schemes.v1.json"
    f.write_bytes(f.read_bytes().replace("₹200".encode(), "₹900".encode(), 1))  # someone edits an amount
    with pytest.raises(PackSignatureError):
        load_pack_file(f)


def test_unsigned_packs_are_refused_only_in_strict_mode(temp_packs, monkeypatch):
    (temp_packs / "demo.v1.json.sig").unlink()
    assert load_pack_file(temp_packs / "demo.v1.json").signed_by is None
    monkeypatch.setenv("SAHAYAK_REQUIRE_SIGNED", "1")
    with pytest.raises(PackSignatureError):
        load_pack_file(temp_packs / "demo.v1.json")


def test_install_swaps_atomically_and_rolls_back(temp_packs, tmp_path):
    incoming = tmp_path / "incoming"
    incoming.mkdir()
    for name in ("demo.v1.json", "demo.v1.json.sig"):
        shutil.copy(temp_packs / name, incoming / name)
    version = load_pack_file(incoming / "demo.v1.json").version
    install(incoming / "demo.v1.json")  # same pack, genuine signature: accepted, old copy kept
    assert (temp_packs / ".previous" / "demo.v1.json").exists()
    bad = incoming / "demo.v1.json"
    bad.write_bytes(bad.read_bytes().replace(f'"{version}"'.encode(), b'"9.9.9"', 1))
    with pytest.raises(PackSignatureError):
        install(bad)  # altered in transit: refused, nothing touched
    assert load_pack_file(temp_packs / "demo.v1.json").version == version
    assert rollback("demo.v1.json").exists()


# ---------------------------------------------------------------- phone recordings

def test_phone_recorder_formats_are_decoded():
    av = pytest.importorskip("av")
    import io
    import numpy as np
    from sahayak.voice import read_audio
    tone = (np.sin(np.linspace(0, 2 * np.pi * 440, 16000)) * 8000).astype("<i2")
    buf = io.BytesIO()
    with av.open(buf, "w", format="mp4") as out:
        st = out.add_stream("aac", rate=16000)
        st.layout = "mono"
        frame = av.AudioFrame.from_ndarray(tone.reshape(1, -1), format="s16", layout="mono")
        frame.sample_rate = 16000
        for f in av.AudioResampler(format=st.format.name, layout="mono", rate=16000).resample(frame):
            for pkt in st.encode(f):
                out.mux(pkt)
        for pkt in st.encode(None):
            out.mux(pkt)
    pcm, seconds = read_audio(buf.getvalue())
    assert 0.9 < seconds < 1.2 and len(pcm) == int(seconds * 16000) * 2
    assert client.post("/api/asr", content=b"\x00\x01not audio").status_code == 422
