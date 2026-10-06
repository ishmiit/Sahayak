"""Captive-portal DNS: every name resolves to the node.

On the demo network a travel router with no internet uplink hands out this node as the DNS
server. Every lookup, including the phones' "is there internet?" probes
(connectivitycheck.gstatic.com, captive.apple.com, www.msftconnecttest.com), gets the node's
address, so the phone shows "Sign in to network" and opens Sahayak by itself. Nothing is
forwarded anywhere: this server only ever answers with the one local address.

  python -m sahayak.node.dns --ip 10.0.0.2 [--port 53]
"""
from __future__ import annotations

import argparse
import socket
import struct

TTL = 60
TYPE_A, CLASS_IN = 1, 1


def response(query: bytes, ip: str) -> bytes | None:
    """The answer to one DNS query: an A record pointing at `ip` for A questions, an empty
    NOERROR answer for anything else (AAAA, HTTPS…) so phones fall back to IPv4. None for junk."""
    if len(query) < 17:
        return None
    tid, flags, qdcount = struct.unpack(">HHH", query[:6])
    if flags & 0x8000 or qdcount != 1:  # a response, or not a single question
        return None
    i = 12
    while True:  # walk the question name
        if i >= len(query):
            return None
        length = query[i]
        if length == 0:
            i += 1
            break
        if length & 0xC0:
            return None
        i += 1 + length
    if i + 4 > len(query):
        return None
    qtype, qclass = struct.unpack(">HH", query[i:i + 4])
    question = query[12:i + 4]
    rd = flags & 0x0100
    answer_it = qtype == TYPE_A and qclass == CLASS_IN
    header = struct.pack(">HHHHHH", tid, 0x8000 | 0x0400 | rd | 0x0080, 1, 1 if answer_it else 0, 0, 0)
    if not answer_it:
        return header + question
    record = b"\xc0\x0c" + struct.pack(">HHIH", TYPE_A, CLASS_IN, TTL, 4) + socket.inet_aton(ip)
    return header + question + record


def serve(ip: str, port: int = 53, host: str = "0.0.0.0") -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((host, port))
    print(f"captive DNS on {host}:{port}: every name -> {ip}")
    while True:
        data, addr = sock.recvfrom(512)
        reply = response(data, ip)
        if reply:
            sock.sendto(reply, addr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--ip", required=True, help="the node's address on the Sahayak Wi-Fi")
    ap.add_argument("--port", type=int, default=53)
    args = ap.parse_args()
    socket.inet_aton(args.ip)  # validate
    serve(args.ip, args.port)


if __name__ == "__main__":
    main()
