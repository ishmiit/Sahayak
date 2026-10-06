"""Zero-egress evidence, read on the node itself.

Three independent readings, shown live on the node's status page:

1. Sahayak's own process. A Python audit hook sees every socket connect and DNS lookup the
   node makes; any aimed outside the local network is counted. By design this stays at 0.
2. The whole machine. Open TCP connections to addresses outside the local network, from any
   program (psutil). On a demo node whose Wi-Fi has no uplink this is 0 too.
3. The firewall. Whether the "block everything except the local network" rules from
   scripts/firewall/ are in place.

Plus bytes in and out per network interface since the node started, so the panel also shows
the local traffic that is happening: phones talking to the node.
"""
from __future__ import annotations

import ipaddress
import json
import platform
import subprocess
import sys
import threading
import time
from collections import deque

import psutil

STARTED = time.time()
_lock = threading.Lock()
_counts = {"external_connects": 0, "external_lookups": 0, "local_connects": 0}
_recent: deque = deque(maxlen=20)
_installed = False
_LOCAL_NAMES = {"localhost", "localhost.localdomain", "ip6-localhost"}


def is_local(host: str | None) -> bool:
    """Loopback, private (RFC 1918 / ULA), link-local, or a local hostname."""
    if not host:
        return True
    host = host.strip("[]").split("%")[0]
    if host.lower() in _LOCAL_NAMES or host.lower().endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False  # a name that needs DNS: not local
    return ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_unspecified


def _note(kind: str, host: str, port) -> None:
    with _lock:
        _counts[kind] += 1
        _recent.append({"kind": kind, "host": str(host), "port": port, "at": time.strftime("%H:%M:%S")})


def _hook(event: str, args: tuple) -> None:
    # Called for every audit event in the process: return fast unless it is about sockets.
    if event == "socket.connect":
        addr = args[1]
        if isinstance(addr, tuple) and addr:
            if is_local(str(addr[0])):
                with _lock:
                    _counts["local_connects"] += 1
            else:
                _note("external_connects", addr[0], addr[1] if len(addr) > 1 else None)
    elif event == "socket.getaddrinfo":
        host = args[0]
        if isinstance(host, bytes):
            host = host.decode("ascii", "replace")
        if host and not is_local(str(host)):
            _note("external_lookups", host, args[1] if len(args) > 1 else None)


def install() -> None:
    """Start counting. Audit hooks cannot be removed, so this runs once per process."""
    global _installed
    if not _installed:
        sys.addaudithook(_hook)
        _installed = True


def machine_connections() -> dict:
    """Open TCP connections from this machine to anything outside the local network."""
    out = []
    try:
        conns = psutil.net_connections(kind="inet")
    except (psutil.AccessDenied, OSError):
        return {"available": False, "external": None, "sample": []}
    for c in conns:
        if c.status == psutil.CONN_ESTABLISHED and c.raddr and not is_local(c.raddr.ip):
            name = ""
            if c.pid:
                try:
                    name = psutil.Process(c.pid).name()
                except (psutil.Error, OSError):
                    name = ""
            out.append({"remote": f"{c.raddr.ip}:{c.raddr.port}", "program": name})
    return {"available": True, "external": len(out), "sample": out[:8]}


_IO_START = {k: (v.bytes_sent, v.bytes_recv) for k, v in psutil.net_io_counters(pernic=True).items()}


def interfaces() -> list[dict]:
    """Bytes sent and received per interface since the node started (all of it local on a node with no uplink)."""
    rows = []
    stats = psutil.net_if_stats()
    for name, io in psutil.net_io_counters(pernic=True).items():
        if not stats.get(name) or not stats[name].isup or name.lower().startswith(("loopback", "lo")):
            continue
        sent0, recv0 = _IO_START.get(name, (io.bytes_sent, io.bytes_recv))
        rows.append({"name": name, "sent": io.bytes_sent - sent0, "received": io.bytes_recv - recv0})
    return rows


_fw_cache: dict = {"at": 0.0, "value": None, "busy": False}


def firewall() -> dict:
    """Is the offline firewall in place? The check shells out and can take seconds, so it runs in
    the background every 30 s and the live panel always gets the last answer straight away."""
    stale = time.time() - _fw_cache["at"] > 30
    if stale and not _fw_cache["busy"]:
        _fw_cache["busy"] = True
        threading.Thread(target=_refresh_firewall, daemon=True).start()
    return _fw_cache["value"] or {"system": platform.system(), "offline_rules": None, "detail": "checking…"}


def _refresh_firewall() -> None:
    try:
        _fw_cache.update(value=_check_firewall(), at=time.time())
    finally:
        _fw_cache["busy"] = False


def _check_firewall() -> dict:
    value = {"system": platform.system(), "offline_rules": None, "detail": "not checked"}
    try:
        if platform.system() == "Windows":
            # scripts/firewall/windows-offline.ps1 adds enabled BLOCK rules named "Sahayak: block internet …"
            cmd = ("$r = @(Get-NetFirewallRule -DisplayName 'Sahayak: block internet*' -ErrorAction SilentlyContinue | "
                   "Where-Object { $_.Enabled -eq 'True' -and $_.Direction -eq 'Outbound' -and $_.Action -eq 'Block' }).Count;"
                   "$on = @(Get-NetFirewallProfile | Where-Object { $_.Enabled -eq 'True' }).Count;"
                   "@{rules=$r; profiles_on=$on} | ConvertTo-Json -Compress")
            raw = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", cmd],
                                 capture_output=True, text=True, timeout=20).stdout
            data = json.loads(raw or "{}")
            on = data.get("rules", 0) > 0 and data.get("profiles_on", 0) > 0
            value = {"system": "Windows", "offline_rules": on,
                     "detail": "Sahayak block rule active (windows-offline.ps1)" if on
                     else "Sahayak block rule not installed (run scripts/firewall/windows-offline.ps1 as Administrator)"}
        elif platform.system() == "Linux":
            r = subprocess.run(["nft", "list", "table", "inet", "sahayak"], capture_output=True, text=True, timeout=10)
            value = {"system": "Linux", "offline_rules": r.returncode == 0,
                     "detail": "nftables table inet sahayak" + (" present" if r.returncode == 0 else " absent or not readable")}
        elif platform.system() == "Darwin":
            r = subprocess.run(["pfctl", "-a", "sahayak", "-s", "rules"], capture_output=True, text=True, timeout=10)
            value = {"system": "macOS", "offline_rules": r.returncode == 0 and "block" in r.stdout,
                     "detail": "pf anchor sahayak" + (" loaded" if r.returncode == 0 else " not readable")}
    except (OSError, subprocess.SubprocessError, ValueError) as e:
        value["detail"] = f"could not check: {e}"
    return value


def snapshot() -> dict:
    with _lock:
        counts, recent = dict(_counts), list(_recent)
    return {
        "since": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(STARTED)),
        "uptime_s": round(time.time() - STARTED),
        "sahayak": {**counts, "watching": _installed, "recent_external": recent},
        "machine": machine_connections(),
        "interfaces": interfaces(),
        "firewall": firewall(),
    }
