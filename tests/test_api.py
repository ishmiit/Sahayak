"""Node API: routes, validation, privacy headers, and explain with no model available."""
from fastapi.testclient import TestClient

from sahayak.server import app

client = TestClient(app)


def test_health_lists_packs_and_backend():
    h = client.get("/api/health").json()
    assert h["status"] == "ok"
    assert {p["name"] for p in h["packs"]} >= {"fraud", "demo"}
    assert h["llm"]["backend"] == "none"


def test_every_response_locks_the_browser_to_this_node():
    r = client.get("/")
    csp = r.headers["content-security-policy"]
    assert "default-src 'self'" in csp and "connect-src 'self'" in csp
    assert r.headers["x-content-type-options"] == "nosniff"


def test_check_and_explain_without_a_model():
    card = client.post("/api/check", json={"text": "Share the OTP you received to stop the block", "sender": "9812345678"}).json()
    assert card["verdict"] == "scam"
    out = client.post("/api/explain", json={"id": card["id"]}).json()
    assert out["source"] == "template"
    assert out["explanation"]["hi"] and out["explanation"]["en"]


def test_validation_and_unknown_check():
    assert client.post("/api/check", json={"text": ""}).status_code == 422
    assert client.post("/api/check", json={"text": "x" * 5000}).status_code == 422
    assert client.post("/api/check", json={"text": "hi", "input_type": "fax"}).status_code == 422
    assert client.post("/api/explain", json={"id": "nope12345"}).status_code == 404


def test_docs_are_off_and_unknown_pages_open_the_app():
    r = client.get("/docs")
    assert r.status_code == 200 and "Sahayak" in r.text  # the app, not Swagger (which loads from a CDN)
    assert client.get("/generate_204").status_code == 200  # captive-portal probes land on the app
    assert client.get("/api/nothing-here").status_code == 404


def test_examples_pack():
    ex = client.get("/api/examples").json()["examples"]
    assert len(ex) >= 5 and all(e["text"] for e in ex)


def test_fake_scheme_example_raises_the_flag_the_app_uses_to_offer_real_benefits():
    ex = next(e for e in client.get("/api/examples").json()["examples"] if e["id"] == "scheme_apk")
    card = client.post("/api/check", json={"text": ex["text"], "sender": ex["sender"]}).json()
    assert card["verdict"] == "scam"
    assert "govt_scheme_bait" in {s["id"] for s in card["signals"]}
