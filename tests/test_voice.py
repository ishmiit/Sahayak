"""Voice: numbers as words, speakable text, answer matching, and the speech API end to end."""
import io
import wave

import pytest
from fastapi.testclient import TestClient

from sahayak.server import app
from sahayak.voice import grammar, match, parse, speakable, words
from sahayak.voice.asr import read_wav, AudioError
from sahayak.voice.tts import get_speaker
from sahayak.voice.asr import get_listener

client = TestClient(app)
HAVE_TTS = bool(get_speaker().voices().get("hi"))
HAVE_ASR = "hi" in get_listener().languages()
needs_models = pytest.mark.skipif(not (HAVE_TTS and HAVE_ASR), reason="speech models not installed (scripts/get_models.py)")


# ---------------------------------------------------------------- numbers

@pytest.mark.parametrize("lang", ["hi", "en"])
def test_every_age_survives_words_and_back(lang):
    for n in range(0, 121):
        assert parse(words(n, lang), lang) == n, (n, words(n, lang))


@pytest.mark.parametrize("n,hi,en", [
    (200, "दो सौ", "two hundred"), (436, "चार सौ छत्तीस", "four hundred thirty six"), (6000, "छह हज़ार", "six thousand"),
    (200000, "दो लाख", "two lakh"), (250000, "दो लाख पचास हज़ार", "two lakh fifty thousand"), (10000000, "एक करोड़", "one crore"),
])
def test_indian_number_words(n, hi, en):
    assert words(n, "hi") == hi and words(n, "en") == en
    assert parse(hi, "hi") == n and parse(en, "en") == n


@pytest.mark.parametrize("text,lang,want", [
    ("मेरी उम्र सड़सठ साल है", "hi", 67), ("सडसठ", "hi", 67), ("एक सौ बीस", "hi", 120), ("दस हज़ार पाँच सौ", "hi", 10500),
    ("67 साल", "hi", 67), ("sixty seven years", "en", 67), ("कुछ नहीं", "hi", None), ("साठ सत्तर", "hi", 60),
])
def test_parse_finds_the_first_number(text, lang, want):
    assert parse(text, lang) == want


# ---------------------------------------------------------------- speakable text

@pytest.mark.parametrize("text,lang,want", [
    ("₹2 लाख का बीमा, ₹20 साल", "hi", "दो लाख रुपये का बीमा, बीस रुपये साल"),
    ("60 के बाद ₹1,000–₹5,000 हर महीने", "hi", "साठ के बाद एक हज़ार रुपये से पाँच हज़ार रुपये हर महीने"),
    ("1930 पर कॉल करें", "hi", "एक नौ तीन शून्य पर कॉल करें"),
    ("80% या ज़्यादा", "hi", "अस्सी प्रतिशत या ज़्यादा"),
    ("आपका OTP", "hi", "आपका ओ टी पी"),
    ("₹2 lakh cover for ₹20 a year", "en", "two lakh rupees cover for twenty rupees a year"),
    ("Call 1930", "en", "Call one nine three zero"),
])
def test_speakable(text, lang, want):
    assert speakable(text, lang) == want


def test_official_addresses_are_spoken_but_scam_links_are_not():
    assert "साइबर क्राइम डॉट गव डॉट इन" in speakable("cybercrime.gov.in पर शिकायत करें", "hi")
    scam = speakable("अपडेट करें: http://sbi-kyc-update.xyz/login", "hi")
    assert "sbi" not in scam.lower() and "xyz" not in scam and "एक लिंक" in scam


# ---------------------------------------------------------------- answers

def q(qid, kind, options=()):
    return {"id": qid, "kind": kind, "options": [{"id": o} for o in options]}


YN = ("yes", "no", "dont_know")
RATION = ("aay", "bpl_phh", "apl", "none", "dont_know")
WORK = ("farmer_land", "farm_labour", "unorganised", "salaried_pf", "government", "not_working")
MONEY = ("taxpayer", "le15k", "gt15k", "dont_know")
SITUATION = ("widow", "disability80", "earner_died")


@pytest.mark.parametrize("question,text,want", [
    (q("age", "age"), "मेरी उम्र पैंसठ साल है", 65),
    (q("bank", "single", YN), "हाँ, खाता है", "yes"),
    (q("bank", "single", YN), "पता नहीं", "dont_know"),  # longer phrase beats "नहीं"
    (q("bank", "single", YN), "नहीं", "no"),
    (q("ration", "single", RATION), "अंत्योदय वाला कार्ड", "aay"),
    (q("ration", "single", RATION), "बीपीएल कार्ड है", "bpl_phh"),
    (q("work", "single", WORK), "मैं खेत मजदूर हूँ", "farm_labour"),
    (q("work", "single", WORK), "दिहाड़ी करता हूँ", "unorganised"),
    (q("money", "single", MONEY), "महीने में दस हज़ार", "le15k"),
    (q("money", "single", MONEY), "बीस हजार", "gt15k"),
    (q("money", "single", MONEY), "हाँ मैं टैक्स भरता हूँ", "taxpayer"),
    (q("situation", "multi", SITUATION), "मैं विधवा हूँ", ["widow"]),
    (q("situation", "multi", SITUATION), "इनमें से कोई नहीं", []),
    (q("kisan", "single", YN), "no", "no"),
])
def test_answer_matching(question, text, want):
    found = match(question, text, "hi")
    assert found is not None and found["answer"] == want


def test_no_guessing():
    assert match(q("bank", "single", YN), "", "hi") is None
    assert match(q("ration", "single", RATION), "मौसम अच्छा है", "hi") is None
    assert match(q("age", "age"), "बहुत पुरानी बात है", "hi") is None
    # only the options the person was shown can be chosen
    assert match(q("ration", "single", ("apl", "none")), "अंत्योदय", "hi") is None


def test_grammar_holds_the_answer_words():
    g = grammar(q("ration", "single", RATION), "hi")
    assert "अंत्योदय" in g and "पता नहीं" in g
    assert "सड़सठ" in grammar(q("age", "age"), "hi")


# ---------------------------------------------------------------- audio in and out

def wav_of(seconds=0.5, rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))
    return buf.getvalue()


def test_read_wav_checks_and_resamples():
    pcm, seconds = read_wav(wav_of(1.0, 48000))
    assert abs(seconds - 1.0) < 0.01 and len(pcm) == 32000
    with pytest.raises(AudioError):
        read_wav(b"not audio")
    with pytest.raises(AudioError):
        read_wav(wav_of(31))


def test_asr_refuses_bad_input():
    assert client.post("/api/asr", content=b"nope").status_code == 422
    assert client.post("/api/asr", params={"question": "nope"}, content=wav_of()).status_code == 422
    assert client.post("/api/asr", content=b"\x00" * (3 * 1024 * 1024)).status_code == 413


@needs_models
def test_tts_speaks_wav_and_caches_fixed_sentences():
    r = client.post("/api/tts", json={"text": "क्या आपका बैंक या डाकघर में बचत खाता है?", "lang": "hi"})
    assert r.status_code == 200 and r.headers["content-type"] == "audio/wav" and r.content[:4] == b"RIFF"
    again = client.post("/api/tts", json={"text": "क्या आपका बैंक या डाकघर में बचत खाता है?", "lang": "hi"})
    assert again.headers["x-sahayak-cached"] in ("memory", "disk")
    assert client.post("/api/tts", json={"text": "x" * 700}).status_code == 422


@needs_models
@pytest.mark.parametrize("said,question,options,want", [
    ("मेरी उम्र बहत्तर साल है", "age", None, 72),
    ("अंत्योदय कार्ड है", "ration", "aay,bpl_phh,apl,none,dont_know", "aay"),
    ("पता नहीं", "bank", "yes,no,dont_know", "dont_know"),
])
def test_spoken_answer_round_trip(said, question, options, want):
    audio = client.post("/api/tts", json={"text": said, "lang": "hi", "voice": "male"}).content
    params = {"lang": "hi", "question": question}
    if options:
        params["options"] = options
    out = client.post("/api/asr", params=params, content=audio).json()
    assert out["answer"] == want, out
    assert out["seconds"] > 0.3


# ---------------------------------------------------------------- VoiceBench recorder

def test_voicebench_recording_is_off_by_default():
    assert client.get("/api/voicebench/prompts").status_code == 404
    assert client.post("/api/voicebench/session", json={"consent": True, "age_band": "55+"}).status_code == 404


def test_voicebench_consent_record_and_withdraw(monkeypatch):
    from sahayak.config import get_settings
    monkeypatch.setenv("SAHAYAK_VOICEBENCH", "1")
    get_settings.cache_clear()
    try:
        prompts = client.get("/api/voicebench/prompts").json()["prompts"]
        assert len(prompts) >= 40 and {p["lang"] for p in prompts} == {"hi", "en"}
        assert client.post("/api/voicebench/session", json={"consent": False, "age_band": "55+"}).status_code == 422
        session = client.post("/api/voicebench/session",
                              json={"consent": True, "age_band": "55+", "region": "Bihar"}).json()["session"]
        assert client.post(f"/api/voicebench/{session}/a01", content=wav_of(1.0)).json()["saved"] == "a01"
        assert client.post(f"/api/voicebench/{session}/zz99", content=wav_of(1.0)).status_code == 404
        assert client.post(f"/api/voicebench/{session}/a02", content=b"nope").status_code == 422
        assert client.post("/api/voicebench/20260101-deadbeef/a01", content=wav_of(1.0)).status_code == 404
        folder = get_settings().data_dir / "voicebench" / session
        meta = (folder / "session.json").read_text(encoding="utf-8")
        assert (folder / "a01.wav").exists() and '"region": "Bihar"' in meta and "name" not in meta
        assert client.delete(f"/api/voicebench/{session}").json()["deleted"] == session
        assert not folder.exists()
    finally:
        monkeypatch.delenv("SAHAYAK_VOICEBENCH")
        get_settings.cache_clear()
