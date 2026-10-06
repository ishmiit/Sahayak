"""Operator console and impact counters: PIN, queue, consented encrypted case log, and an export
that carries no personal data."""
import base64
import json
import time

import pytest
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from fastapi.testclient import TestClient

from sahayak.node import console, counters
from sahayak.server import app

PIN = "246810"
PERSONAL = ["Ramesh Kumar", "9876543210", "ramesh@okaxis", "sbi-kyc-update.xyz", "4421", "Sunita"]
SCAMS = [
    "Dear Ramesh Kumar, your SBI KYC expired. Update now at http://sbi-kyc-update.xyz or call 9876543210",
    "Send Rs 25,000 to ramesh@okaxis to stop your arrest. This is Delhi Police.",
    "Sunita ji, aapke card XX4421 ka OTP batao turant warna block ho jayega",
]


@pytest.fixture
def client():
    console._auth = console.Auth(PIN)  # a known PIN for the tests
    console.QUEUE.clear()
    counters.reset()
    c = TestClient(app)
    yield c
    console._auth = None


def login(c):
    r = c.post("/api/console/login", json={"pin": PIN})
    assert r.status_code == 200 and "sahayak_console" in r.cookies
    return c


def test_console_needs_the_pin(client):
    assert client.get("/api/console/queue").status_code == 401
    assert client.post("/api/console/login", json={"pin": "000000"}).status_code == 401
    assert login(client).get("/api/console/queue").status_code == 200


def test_wrong_pins_lock_logins_for_a_minute(client):
    for _ in range(5):
        client.post("/api/console/login", json={"pin": "111111"})
    assert client.post("/api/console/login", json={"pin": PIN}).status_code == 429


def test_generated_pin_is_never_a_default():
    pins = {console.Auth(None).pin for _ in range(5)}
    assert len(pins) > 1 and all(len(p) == 6 and p.isdigit() for p in pins)


def test_ask_the_agent_queue(client):
    card = client.post("/api/check", json={"text": SCAMS[0], "lang": "hi"}).json()
    ticket = client.post("/api/queue", json={"kind": "check", "check_id": card["id"], "lang": "hi"}).json()["ticket"]
    benefits = client.post("/api/queue", json={"kind": "benefits", "answers": {"age": 67, "situation": ["widow"],
                                               "ration": "aay", "bank": "yes", "work": "not_working"}}).json()["ticket"]
    assert ticket != benefits and ticket.startswith("A-")
    login(client)
    items = client.get("/api/console/queue").json()["items"]
    assert [i["ticket"] for i in items] == [ticket, benefits]
    blob = json.dumps(items)
    assert "Ramesh" not in blob and "9876543210" not in blob  # the queue shows the verdict, not the message
    assert items[1]["summary"]["groups"]["likely"] == ["IGNOAPS", "IGNWPS"]
    assert client.get(f"/api/console/case/{card['id']}").json()["verdict"] == "scam"
    assert client.post(f"/api/console/queue/{ticket}", json={"state": "done"}).status_code == 200
    assert [i["ticket"] for i in client.get("/api/console/queue").json()["items"]] == [benefits]


def test_case_log_needs_consent_is_encrypted_and_expires(client):
    login(client)
    entry = {"kind": "check", "verdict": "scam", "category": "kyc", "rupees_at_risk": 0, "lang": "hi",
             "name": "Ramesh Kumar", "phone": "9876543210"}  # fields that must be dropped
    assert client.post("/api/console/caselog", json={"consent": False, "entry": entry}).status_code == 422
    saved = client.post("/api/console/caselog", json={"consent": True, "entry": entry}).json()
    assert "name" not in saved and "phone" not in saved
    raw = console.caselog().path.read_bytes()
    assert b"kyc" not in raw and b"scam" not in raw  # encrypted at rest
    # an entry older than 30 days disappears on the next read
    log = console.caselog()
    old = log._read() + [{"kind": "check", "verdict": "scam", "ts": time.time() - 31 * 86400, "id": "old", "at": "x"}]
    log._write(old)
    ids = [e["id"] for e in client.get("/api/console/caselog").json()["entries"]]
    assert "old" not in ids and saved["id"] in ids
    client.post("/api/console/delete-everything", json={})
    assert client.get("/api/console/caselog").json()["entries"] == []


def test_counter_export_has_no_personal_data_and_is_signed(client):
    for text in SCAMS:
        client.post("/api/check", json={"text": text, "lang": "hi"})
    client.post("/api/check", json={"text": "Beta khana kha liya?", "lang": "en", "input_type": "call"})
    answers = {"age": 67, "situation": ["widow"], "ration": "aay", "bank": "yes", "work": "not_working"}
    for _ in range(3):  # the same interview viewed three times counts once
        client.post("/api/navigator/result", json={"answers": answers, "session": "s-one", "lang": "hi"})
    client.post("/api/counters/slip", json={"kind": "scheme"})
    raw = counters.view()
    assert raw["verdicts"]["scam"] == 3 and raw["checks"]["call"] == 1 and raw["schemes"]["ignoaps"] == 1
    assert raw["rupees_at_risk"] == 25000
    out = login(client).get("/api/console/export").json()
    text = out["csv"]
    for secret in PERSONAL + SCAMS:
        assert secret not in text
    allowed = {"checks", "verdicts", "categories", "schemes", "slips", "languages", "rupees_at_risk", "escalations"}
    rows = [line.split(",") for line in text.strip().splitlines()[1:]]
    assert all(r[1] in allowed for r in rows)
    assert ["verdicts", "scam", "<5"] == rows[[r[1:3] for r in rows].index(["verdicts", "scam"])][1:]
    assert any(r[1] == "rupees_at_risk" and r[3].startswith("withheld") for r in rows)  # under 5 scams
    key = load_pem_public_key(out["public_key"].encode())
    key.verify(base64.b64decode(out["signature"]), text.encode())  # raises if altered


def test_reference_lists_categories_with_what_to_say(client):
    cats = login(client).get("/api/console/reference").json()["categories"]
    assert len(cats) >= 10 and all(c["actions"]["hi"] and c["actions"]["en"] for c in cats)
