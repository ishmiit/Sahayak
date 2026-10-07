"""Build a narrated draft of the demo video (docs/video/Sahayak_demo_draft.mp4, 1920 x 1080, under 3 min).

Title cards, the five screen clips from scripts/record_demo_clips.py with a caption beside or under
each, an evidence card whose numbers are read from bench/results/*.json, and an English voice-over
spoken by the node's own offline voice (Piper "lessac"). The script is in SEGMENTS below and is also
written to docs/video/narration_script.md, so the team can re-record the voice in their own words
and swap the audio track.

Usage: python scripts/build_demo_video.py   (needs the clips in docs/video and the speech models)
"""
from __future__ import annotations

import io
import json
import sys
import wave
from fractions import Fraction
from pathlib import Path

import av
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
VIDEO = ROOT / "docs" / "video"
OUT = VIDEO / "Sahayak_demo_draft.mp4"
W, H, FPS, RATE = 1920, 1080, 25, 48000
FONTS = Path("C:/Windows/Fonts")
# Rosh 27, light appearance (as web/styles.css): page, label, secondary label, Bay Blue tint, hairline, device bezel
BG, INK, INK2, TINT, SEP, BEZEL = (244, 243, 240), (11, 11, 12), (94, 94, 95), (31, 95, 214), (226, 225, 221), (11, 11, 12)
GEIST, GEIST_MONO = ROOT / "web" / "fonts" / "geist-latin.woff2", ROOT / "web" / "fonts" / "geist-mono-latin.woff2"


# Geist, the app's own typeface (web/fonts); else Segoe UI on Windows, Arial on macOS, DejaVu on Linux; never Pillow's
# tiny bitmap font.
FONT_FILES = {
    False: ("segoeui.ttf", "DejaVuSans.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    True: ("segoeuib.ttf", "DejaVuSans-Bold.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
}


def font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    try:
        f = ImageFont.truetype(str(GEIST_MONO if mono else GEIST), size)
        f.set_variation_by_axes([600 if mono else 700 if bold else 400])
        return f
    except (OSError, ValueError):
        pass
    for name in FONT_FILES[bold]:
        try:
            return ImageFont.truetype(str(FONTS / name) if (FONTS / name).exists() else name, size)
        except OSError:
            continue
    return ImageFont.load_default(size)  # Pillow 10.1+: a scalable font


def wrap(draw: ImageDraw.ImageDraw, text: str, f, width: int) -> list[str]:
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=f) <= width:
            line = trial
        else:
            lines.append(line)
            line = word
    return lines + [line] if line else lines


def text_block(draw, xy, text, f, width, fill=INK, gap=1.3) -> int:
    x, y = xy
    for line in wrap(draw, text, f, width):
        draw.text((x, y), line, font=f, fill=fill)
        y += int(f.size * gap)
    return y


def mark(im: Image.Image, xy: tuple[int, int], size: int) -> None:
    """Sahayak's mark, as in the app's top bar: a silk-gradient squircle with the shield glyph from web/fonts."""
    n = size * 2  # drawn at twice the size, then scaled down for smooth edges
    t = np.clip((np.arange(n)[:, None] + np.arange(n)[None, :]) / (2 * n - 2), 0, 1)
    stops = np.array([[126, 93, 69], [169, 141, 95], [146, 122, 114], [79, 80, 105]], dtype=float)
    pos = np.array([0, .3, .6, 1])
    rgb = np.stack([np.interp(t, pos, stops[:, c]) for c in range(3)], axis=-1).astype(np.uint8)
    tile = Image.fromarray(rgb, "RGB").convert("RGBA")
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, n - 1, n - 1], int(n * .3), fill=255)
    tile.putalpha(mask)
    try:
        glyph = ImageFont.truetype(str(ROOT / "web" / "fonts" / "symbols.woff2"), int(n * .6))
        glyph.set_variation_by_axes([1, 500])  # FILL 1, weight 500
        ImageDraw.Draw(tile).text((n / 2, n / 2), "\ue8e8", font=glyph, fill=(255, 255, 255, 255), anchor="mm")  # verified_user
    except (OSError, ValueError):
        pass
    tile = tile.resize((size, size), Image.LANCZOS)
    im.paste(tile, xy, tile)


def card(title: str, lines: list[str], kicker: str = "", accent=TINT) -> Image.Image:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    mark(im, (160, 120), 88)
    y = 270
    if kicker:
        d.text((160, y), kicker.upper(), font=font(30, mono=True), fill=accent)
        y += 66
    y = text_block(d, (160, y), title, font(84, True), W - 320, gap=1.15) + 40
    for line in lines:
        y = text_block(d, (160, y), line, font(44), W - 320, fill=INK2) + 18
    return im


def evidence_card(rows: list[tuple[str, str]], note: str) -> Image.Image:
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.text((160, 110), "MEASURED, NOT CLAIMED", font=font(30, mono=True), fill=TINT)
    y = 190
    for head, body in rows:
        d.text((160, y), head, font=font(46, True), fill=INK)
        y2 = text_block(d, (620, y + 4), body, font(40), W - 780, fill=INK2, gap=1.25)
        y = max(y + 70, y2) + 26
        d.line([160, y - 14, W - 160, y - 14], fill=SEP, width=2)
    text_block(d, (160, y + 10), note, font(32), W - 320, fill=INK2)
    return im


class ClipFrames:
    """The frames of one screen clip laid out on a 1920 x 1080 canvas with its caption."""

    def __init__(self, path: Path, caption: str, title: str):
        with av.open(str(path)) as c:
            self.frames = [f.to_image() for f in c.decode(video=0)]
        self.base = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(self.base)
        fw, fh = self.frames[0].size
        if fh > fw:  # phone: the screen on the left, the caption on the right
            scale = 1000 / fh
            self.size, self.pos = (int(fw * scale), 1000), (260, 50)
            d.rounded_rectangle([self.pos[0] - 14, 36, self.pos[0] + self.size[0] + 14, 1064], 48, fill=BEZEL)
            d.text((900, 300), title, font=font(64, True), fill=INK)
            text_block(d, (900, 410), caption, font(42), 860, fill=INK2)
        else:  # desktop: the screen above, the caption below
            self.size, self.pos = (1536, 864), (192, 40)
            d.text((192, 930), title, font=font(46, True), fill=INK)
            text_block(d, (192 + int(d.textlength(title, font=font(46, True))) + 30, 936), caption, font(36), 1536 - 480, fill=INK2)

    def frame(self, i: int) -> Image.Image:
        im = self.base.copy()
        im.paste(self.frames[min(i, len(self.frames) - 1)].resize(self.size, Image.LANCZOS), self.pos)
        return im

    @property
    def seconds(self) -> float:
        return len(self.frames) / FPS


def speech(speaker, text: str) -> np.ndarray:
    data, _ = speaker.synth(text, lang="en", speed=1.0, store=False)
    with wave.open(io.BytesIO(data)) as w:
        rate, pcm = w.getframerate(), np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32)
    t = np.arange(int(len(pcm) * RATE / rate)) * rate / RATE  # resample to 48 kHz for AAC
    return np.interp(t, np.arange(len(pcm)), pcm).astype(np.int16)


def load(name: str) -> dict:
    return json.loads((ROOT / "bench" / "results" / name).read_text(encoding="utf-8"))


def segments() -> list[dict]:
    sb = load("scambench_v0_test.json")["systems"]
    sch, fl = load("schemebench_v1.json"), load("voicebench_fleurs_hi.json")
    full, block = sb["full"]["flagged"], sb["blocklist"]["flagged"]
    pct = lambda x: f"{100 * x:.0f} percent"  # noqa: E731
    pub = load("public_v0.json")["first"]["systems"]
    pf, pb = pub["full"]["groups"]["hindi_english_hinglish"], pub["blocklist"]["groups"]["hindi_english_hinglish"]
    bl = load("redteam_v1_blind.json")["first"]["systems"]
    bf, bb = bl["full"]["groups"]["hindi_english_hinglish"], bl["blocklist"]["groups"]["hindi_english_hinglish"]
    pub_n = load("public_v0.json")["first"]["messages"]
    evidence = [
        ("Real messages", f"{pf['caught']} of {pf['scams']} scams caught, {pf['false_alarm']} of {pf['genuine']} genuine "
                          f"flagged (keyword blocklist: {pb['caught']} and {pb['false_alarm']})"),
        ("Blind red team", f"{bf['caught']} of {bf['scams']} scams caught, {bf['false_alarm']} of {bf['genuine']} genuine "
                           f"flagged (blocklist: {bb['caught']} and {bb['false_alarm']})"),
        ("Our test set", f"{100 * full['recall']:.1f}% of scams caught vs {100 * block['recall']:.1f}% for a blocklist; "
                         f"false alarms {100 * full['false_alarm_rate']:.1f}% vs {100 * block['false_alarm_rate']:.1f}%"),
        ("Scheme rules", f"{sch['rules']['agree']:,} / {sch['rules']['decisions']:,} decisions match a re-derivation by "
                         "the same author"),
        ("Hindi speech", f"{100 * fl['wer']:.1f}% word error on Google FLEURS Hindi, offline"),
        ("Offline", "0 connections from Sahayak to the internet, counted live"),
    ]
    return [
        {"card": card("Sahayak", ["An offline scam shield and benefits guide for people new to digital money.",
                                  "Hindi and English. Voice or touch. No internet."], kicker="Ideas for India 2026"),
         "say": "Sahayak. An offline scam shield and benefits guide for people who are new to digital money. "
                "It works in Hindi and English, by voice or by touch, with no internet at all."},
        {"card": card("The problem", ["A message asks for an OTP. A call threatens to block an account.",
                                      "A QR code promises cashback. Many people cannot check, and many are offline."]),
         "say": "Every day, people who have just started using UPI get messages that ask for an OTP, calls that threaten to "
                "block their bank account, and QR codes that promise cashback. Many cannot read English, and many have no "
                "reliable internet to check."},
        {"clip": "1_scam_check_hi.mp4", "title": "Is this a scam?",
         "caption": "Paste, speak or photograph a message. A verdict in milliseconds, the reasons in Hindi and English, what "
                    "to do next, and a ready 1930 complaint.",
         "say": "A person pastes, speaks, or photographs a suspicious message. In milliseconds Sahayak gives a verdict, the "
                "reasons behind it in Hindi and English, what to do next, and a ready-to-file complaint for the 1930 "
                "cyber fraud helpline."},
        {"clip": "2_benefits_interview_hi.mp4", "title": "What am I owed?",
         "caption": "A few spoken questions find which of 12 central schemes a person can claim, with the papers, the office "
                    "and a printed slip.",
         "say": "The benefits guide asks a few questions, one per screen, and finds which of twelve central schemes a person "
                "can claim: pensions, insurance, PM Kisan, Ayushman Bharat for people over seventy, and more. Each comes "
                "with the papers to carry, the office to visit, and a printed slip for the operator."},
        {"clip": "3_upi_qr_check_hi.mp4", "title": "UPI QR codes",
         "caption": "Who the money goes to, and how much. Scanning a QR sends money; it never brings money in.",
         "say": "A photo of a UPI QR code shows who the money goes to, and how much. Sahayak always says it plainly: "
                "scanning a QR code sends money. It never brings money in."},
        {"clip": "4_operator_console.mp4", "title": "At the counter",
         "caption": "Ask-the-agent queue, assisted checks, a consented encrypted case log, impact counters with no personal data.",
         "say": "At a common service centre, the operator sees an ask-the-agent queue, opens the same check to read it "
                "aloud, keeps an encrypted case log only with consent, and sees impact counters that hold no personal data."},
        {"clip": "5_node_zero_egress.mp4", "title": "Zero internet",
         "caption": "One laptop at the counter. Phones join its Wi-Fi. Every connection Sahayak tries to the internet is counted: zero.",
         "say": "Everything runs on one laptop at the counter. Phones join its Wi-Fi, which has no internet. The node counts "
                "every connection Sahayak tries to make to the internet, live. The count is zero."},
        {"card": evidence_card(evidence, f"Real messages: {pub_n} that people in India received, as published by the "
                                         "government, banks and fact-checkers, scored once. Blind red team: written by a "
                                         "separate AI model that never saw the code. Our test set: written by our team. "
                                         "Method and limits: docs/TESTING_REPORT.md."),
         "say": f"Measured, not claimed. On {pub_n} real messages that people in India received, published by the "
                f"government, banks and fact-checkers, Sahayak caught {pf['caught']} of {pf['scams']} scams in Hindi, "
                f"English and Hinglish, and flagged {pf['false_alarm']} of {pf['genuine']} genuine messages; a keyword "
                f"blocklist caught {pb['caught']} and flagged {pb['false_alarm']}. Real messages are harder than our own: "
                f"on the test set our team wrote, it caught {pct(full['recall'])}. On a blind red team written by a separate "
                f"AI model, it caught {bf['caught']} of {bf['scams']}. The scheme rules agree with a re-derivation on all "
                f"{sch['rules']['decisions']:,} decisions, and nothing leaves the node: the count is zero. Next: messages "
                "from people's own phones, collected with consent, and a field test at a service centre."},
        {"card": card("Sahayak", ["Offline. Private. In the language people speak.", "Team: Roshan Raj and Ishmiit Singh"],
                      kicker="Thank you"),
         "say": "Sahayak. Offline, private, and in the language people speak. From Roshan Raj and Ishmiit Singh. Thank you."},
    ]


def main() -> None:
    from sahayak.voice.tts import get_speaker
    speaker = get_speaker()
    segs = segments()
    script = ["# Demo video narration (draft)", "",
              "Spoken by the node's offline English voice in `Sahayak_demo_draft.mp4`. Re-record in your own voice and "
              "replace the audio track; timings follow the sentences.", ""]
    with av.open(str(OUT), "w", options={"movflags": "faststart"}) as out:
        vs = out.add_stream("libx264", rate=FPS, options={"crf": "20", "preset": "medium"})
        vs.width, vs.height, vs.pix_fmt = W, H, "yuv420p"
        aus = out.add_stream("aac", rate=RATE)
        aus.layout = "mono"
        n_video, n_audio, total = 0, 0, 0.0
        for k, seg in enumerate(segs, 1):
            audio = speech(speaker, seg["say"])
            said = len(audio) / RATE
            clip = ClipFrames(VIDEO / seg["clip"], seg["caption"], seg["title"]) if "clip" in seg else None
            seconds = max(said + 0.9, clip.seconds + 0.4 if clip else 0, 4.0)
            frames = int(seconds * FPS)
            lead = int(0.4 * RATE)
            track = np.zeros(int(frames / FPS * RATE), dtype=np.int16)
            track[lead:lead + len(audio)] = audio[: len(track) - lead]
            for i in range(frames):
                img = clip.frame(i) if clip else seg["card"]
                vf = av.VideoFrame.from_image(img)
                vf.pts = n_video
                n_video += 1
                out.mux(vs.encode(vf))
            for start in range(0, len(track), 1024):
                chunk = track[start:start + 1024]
                af = av.AudioFrame.from_ndarray(chunk.reshape(1, -1), format="s16", layout="mono")
                af.sample_rate, af.pts, af.time_base = RATE, n_audio, Fraction(1, RATE)
                n_audio += len(chunk)
                out.mux(aus.encode(af))
            script += [f"**{k}. {seg.get('title') or ('Evidence' if k == len(segs) - 1 else 'Card')}** "
                       f"({total:.0f}–{total + seconds:.0f} s)", "", seg["say"], ""]
            total += seconds
            print(f"segment {k}: {seconds:.1f} s")
        out.mux(vs.encode())
        out.mux(aus.encode())
    (VIDEO / "narration_script.md").write_text("\n".join(script), encoding="utf-8")
    print(f"wrote {OUT} ({total:.0f} s)")


if __name__ == "__main__":
    main()
