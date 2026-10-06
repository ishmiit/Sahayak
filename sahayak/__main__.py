"""Start the Sahayak node: `python -m sahayak` (settings come from SAHAYAK_* env vars).

Plain HTTP on SAHAYAK_PORT by default. With SAHAYAK_TLS_CERT, SAHAYAK_TLS_KEY and
SAHAYAK_PUBLIC_HOST set, HTTPS on SAHAYAK_PORT plus a redirect from plain HTTP on
SAHAYAK_HTTP_PORT, so phones get a secure page (needed for the microphone) and captive-portal
probes open the app.
"""
import asyncio

import uvicorn

from .config import get_settings
from .node import egress


def main() -> None:
    egress.install()  # count any outbound attempt from the very start
    s = get_settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    llm = f"LLM: {s.llm_backend} {s.llm_model} @ {s.llm_url}"
    if not (s.tls_cert and s.tls_key):
        print(f"Sahayak node on http://{s.host}:{s.port}  ({llm})")
        uvicorn.run("sahayak.server:app", host=s.host, port=s.port, log_level="info")
        return
    if not s.public_host:
        raise SystemExit("SAHAYAK_PUBLIC_HOST is required with HTTPS (the name on the certificate)")
    from .node.redirect import make_redirect_app
    print(f"Sahayak node on https://{s.public_host}:{s.port} (redirect from http port {s.http_port}; {llm})")
    https = uvicorn.Server(uvicorn.Config("sahayak.server:app", host=s.host, port=s.port, log_level="info",
                                          ssl_certfile=s.tls_cert, ssl_keyfile=s.tls_key))
    redirect = uvicorn.Server(uvicorn.Config(make_redirect_app(s.public_host, s.port), host=s.host,
                                             port=s.http_port, log_level="warning", lifespan="off"))

    async def both() -> None:
        await asyncio.gather(https.serve(), redirect.serve())

    asyncio.run(both())


if __name__ == "__main__":
    main()
