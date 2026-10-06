"""The plain-HTTP side of an HTTPS node: every request is redirected to the HTTPS address.

Phones check for internet with plain-HTTP probes (/generate_204, /hotspot-detect.html). With the
captive DNS pointing every name at the node, those probes land here, get a redirect instead of
the answer they expect, and the phone shows "Sign in to network", which opens Sahayak over HTTPS:
the secure page browsers require before they allow the microphone and the camera.
"""
from __future__ import annotations


def make_redirect_app(public_host: str, https_port: int = 443):
    base = f"https://{public_host}" + ("" if https_port == 443 else f":{https_port}")

    async def app(scope, receive, send):  # minimal ASGI app (run with lifespan="off")
        if scope["type"] != "http":
            return
        path = scope.get("path", "/")
        query = scope.get("query_string", b"").decode("latin-1")
        probe = path in ("/generate_204", "/gen_204", "/hotspot-detect.html", "/connecttest.txt", "/ncsi.txt")
        target = base + ("/" if probe else path + (f"?{query}" if query else ""))
        await send({"type": "http.response.start", "status": 302,
                    "headers": [(b"location", target.encode("latin-1")), (b"content-length", b"0"),
                                (b"cache-control", b"no-store")]})
        await send({"type": "http.response.body", "body": b""})

    return app
