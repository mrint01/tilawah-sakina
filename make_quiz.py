"""Quiz Reel: "Guess the surah". 5 questions; each plays an ayah, shows 4 surahs, counts down 5 s, reveals.

Levels: easy (Juz Amma + al-Fatiha), medium (well-known surahs), hard (any surah). The answer surah's name never
appears in the ayah shown (that would give it away). Ends with "comment your score" so people answer in comments.

Usage:
  python3 make_quiz.py [--level easy|medium|hard] [--seed 7]
"""
import argparse
import random
import subprocess
import wave

import numpy as np
from PIL import Image, ImageDraw

import make_reel as mr
import scenes

W, H = mr.W, mr.H
RECITER = "Mishary Alafasy"   # clear, steady recitation: easiest to recognise
QUESTIONS = 5
THINK = 4          # seconds of countdown after the ayahs
REVEAL = 2.2       # seconds the answer stays on screen
INTRO, OUTRO = 2.2, 3.5
MAX_SECONDS = 16.0   # 2-4 ayahs in a row per question: enough to recognise the surah
MIN_SECONDS = 7.5
MAX_CHARS = 330
LEVELS = {
    "easy": [1] + list(range(78, 115)),
    "medium": [18, 19, 12, 36, 55, 56, 67, 2, 3, 24, 31, 32, 48, 49, 50, 59, 62, 71, 73, 76, 14, 17, 25],
    "hard": list(range(2, 115)),
}
LEVEL_LABEL = {"easy": "EASY", "medium": "MEDIUM", "hard": "HARD"}
GREEN = (120, 220, 160)
SKY = [(0, (6, 24, 20)), (0.5, (12, 46, 38)), (1, (4, 16, 14))]


def plain(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c)).replace("ٱ", "ا")


def unique(ar):
    """True when this exact ayah text is found only once in the Quran (else the question has 2 right answers)."""
    import json
    import urllib.parse
    q = plain(ar)
    url = "https://api.quran.com/api/v4/search?" + urllib.parse.urlencode({"q": q, "size": 20})
    try:
        res = json.loads(mr.fetch(url, mr.CACHE / "quiz_search" / f"{abs(hash(q))}.json").read_text())["search"]["results"]
    except Exception:  # noqa: BLE001
        return False
    norm = lambda t: " ".join(plain(t).replace("ۖ", "").replace("ۗ", "").replace("ۚ", "").split())
    return sum(1 for r in res if norm(r["text"]) == norm(ar)) <= 1


def pick_questions(level, rnd):
    """5 questions from 5 different surahs; each is 2-3 consecutive ayahs (a short surah may give its whole text)."""
    chs = mr.chapters()
    pool = LEVELS[level]
    qs, used = [], set()
    folder = mr.RECITERS[RECITER]
    tries = 0
    while len(qs) < QUESTIONS and tries < 400:
        tries += 1
        s = rnd.choice(pool)
        if s in used:
            continue
        n = chs[s]["verses_count"]
        a0 = rnd.randint(1, max(1, n - 1))
        name = plain(chs[s]["name_arabic"])
        ayahs, files, secs, chars = [], [], 0.0, 0
        for a in range(a0, min(n, a0 + 3) + 1):
            if len(ayahs) >= 2 and secs >= MIN_SECONDS:
                break
            ar, en = mr.verse(s, a)
            try:
                mp3 = mr.audio(folder, s, a)
            except Exception:  # noqa: BLE001
                break
            d = mr.duration(mp3)
            if name in plain(ar) or secs + d > MAX_SECONDS or chars + len(ar) > MAX_CHARS:
                break
            ayahs.append((a, ar, en))
            files.append(mp3)
            secs += d
            chars += len(ar)
        if len(ayahs) < 2 or secs < MIN_SECONDS:
            continue
        if not any(unique(ar) for _, ar, _ in ayahs):  # a refrain repeated across surahs would have 2 answers
            continue
        others = rnd.sample([x for x in pool if x != s], 3)
        opts = others + [s]
        rnd.shuffle(opts)
        qs.append({"surah": s, "ayah": ayahs[0][0], "last": ayahs[-1][0], "ar": " ".join(f"{ar} \u06DD" for _, ar, _ in ayahs).rstrip(" \u06DD"),
                   "mp3s": files, "options": opts})
        used.add(s)
    if len(qs) < QUESTIONS:
        raise SystemExit("could not find 5 good questions")
    return qs


# ---------- drawing ----------
def background(path):
    bw, bh = int(W * 1.12), int(H * 1.12)
    img = scenes.gradient(SKY, bw, bh)
    img = scenes.glow(img, (bw * 0.12, bh * 0.2, bw * 0.88, bh * 0.6), (50, 120, 90), 90, 170)
    img = scenes.stars(img, 60, 0, bh, seed=12)
    img.convert("RGB").save(path, quality=95)


def header(d, qi, level):
    for i in range(QUESTIONS):  # progress dots
        x = W / 2 - (QUESTIONS - 1) * 20 + i * 40
        d.ellipse((x - 9, 200 - 9, x + 9, 200 + 9), fill=scenes.GOLD + (255,) if i <= qi else (255, 255, 255, 60))
    lab = LEVEL_LABEL[level]
    f = mr.font("Lora-var.ttf", 26)
    tw = d.textlength(lab, font=f)
    d.rounded_rectangle((W / 2 - tw / 2 - 24, 238, W / 2 + tw / 2 + 24, 286), 24, outline=GREEN + (220,), width=2)
    d.text((W / 2, 262), lab, font=f, fill=GREEN + (255,), anchor="mm")
    d.line((W / 2 - 330, 345, W / 2 - 190, 345), fill=scenes.GOLD + (150,), width=2)
    d.line((W / 2 + 190, 345, W / 2 + 330, 345), fill=scenes.GOLD + (150,), width=2)
    d.text((W / 2, 345), "GUESS THE SURAH", font=mr.font("Lora-var.ttf", 34), fill=scenes.GOLD_L + (255,), anchor="mm")


def question_png(q, qi, level, state, path):
    """state: 'listen' (ayah playing), an int (seconds left), or 'reveal'."""
    chs = mr.chapters()
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    header(d, qi, level)
    for size in range(60, 34, -2):
        far = mr.font("AmiriQuran-Regular.ttf", size)
        la = mr.wrap(d, q["ar"], far, W - 170, rtl=True)
        lh = int(size * 1.85)
        if len(la) * lh <= 760 - 400:
            break
    y = 580 - len(la) * lh / 2 + lh / 2
    for ln in la:
        d.text((W / 2, y), ln, font=far, fill=(250, 244, 230, 255), anchor="mm", direction="rtl", language="ar")
        y += lh
    # timer ring
    cx, cy, r = W / 2, 860, 60
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=(255, 255, 255, 50), width=9)
    if state == "listen":
        frac, mid = 1.0, None
    elif state == "reveal":
        frac, mid = 1.0, None
    else:
        frac, mid = state / THINK, str(state)
    col = GREEN if state == "reveal" else scenes.GOLD
    d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * frac, fill=col + (255,), width=9)
    if mid:
        d.text((cx, cy), mid, font=mr.font("Lora-var.ttf", 56), fill=scenes.CREAM + (255,), anchor="mm")
    elif state == "listen":  # a small speaker: listen first
        d.polygon([(cx - 24, cy - 12), (cx - 8, cy - 12), (cx + 10, cy - 28), (cx + 10, cy + 28), (cx - 8, cy + 12), (cx - 24, cy + 12)],
                  fill=scenes.CREAM + (255,))
        for k in (1, 2):
            d.arc((cx + 2 - 14 * k, cy - 14 * k, cx + 18 + 14 * k, cy + 14 * k), -45, 45, fill=scenes.CREAM + (220,), width=4)
    else:  # check mark
        d.line([(cx - 26, cy), (cx - 6, cy + 22), (cx + 30, cy - 22)], fill=GREEN + (255,), width=10, joint="curve")
    for i, s in enumerate(q["options"]):
        y0 = 990 + i * 150
        right = state == "reveal" and s == q["surah"]
        dim = state == "reveal" and not right
        fill = (40, 120, 76, 235) if right else (255, 255, 255, 10 if dim else 18)
        out = GREEN + (255,) if right else (255, 255, 255, 40 if dim else 70)
        d.rounded_rectangle((160, y0, W - 160, y0 + 126), 22, fill=fill, outline=out, width=3)
        alpha = 120 if dim else 255
        d.text((228, y0 + 63), "ABCD"[i], font=mr.font("Lora-var.ttf", 40), fill=scenes.GOLD_L + (alpha,), anchor="mm")
        d.text((W / 2 + 20, y0 + 46), chs[s]["name_arabic"], font=mr.font("Amiri-Bold.ttf", 46), fill=scenes.CREAM + (alpha,),
               anchor="mm", direction="rtl", language="ar")
        d.text((W / 2 + 20, y0 + 96), chs[s]["name_simple"], font=mr.font("Lora-var.ttf", 27), fill=(214, 210, 194, alpha - 40),
               anchor="mm")
    if state == "reveal":
        d.text((W / 2, 1640), f"Surah {chs[q['surah']]['name_simple']} · {q['surah']}:{q['ayah']}" + (f"-{q['last']}" if q['last'] != q['ayah'] else ""),
               font=mr.font("Lora-var.ttf", 34),
               fill=GREEN + (255,), anchor="mm")
    d.text((W / 2, 1840), mr.HANDLE, font=mr.font("Lora-var.ttf", 28), fill=(235, 228, 212, 160), anchor="mm")
    mr.with_shadow(img, path)


def title_png(level, lines, path, sub=None):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    header(d, -1, level)
    y = 760
    for i, ln in enumerate(lines):
        d.text((W / 2, y), ln, font=mr.font("Lora-var.ttf", 72 if i == 0 else 46), fill=(scenes.GOLD_L if i == 0 else scenes.CREAM) + (255,),
               anchor="mm")
        y += 110 if i == 0 else 70
    if sub:
        d.text((W / 2, y + 40), sub, font=mr.font("Lora-var.ttf", 34), fill=(220, 214, 200, 210), anchor="mm")
    d.text((W / 2, 1840), mr.HANDLE, font=mr.font("Lora-var.ttf", 28), fill=(235, 228, 212, 160), anchor="mm")
    mr.with_shadow(img, path)


# ---------- sound: soft clock tick each second, a chime on the answer ----------
SR = 48000


def tone(freq, dur, vol, decay):
    t = np.arange(int(SR * dur)) / SR
    return vol * np.sin(2 * np.pi * freq * t) * np.exp(-t * decay)


def sound_track(events, total, path):
    """events: [(time, 'tick'|'chime')] -> mono 16-bit wav of `total` seconds."""
    buf = np.zeros(int(SR * total) + SR)
    for t, kind in events:
        s = tone(1400, 0.05, 0.12, 60) if kind == "tick" else (tone(880, 0.9, 0.18, 4) + tone(1320, 0.9, 0.12, 5))
        i = int(t * SR)
        buf[i:i + len(s)] += s
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(buf[:int(SR * total)], -1, 1) * 32767).astype(np.int16).tobytes())


def render(level="easy", seed=None, progress=None):
    report = progress or (lambda f: None)
    rnd = random.Random(seed)
    qs = pick_questions(level, rnd)
    work = mr.CACHE / "work" / f"quiz_{seed}"
    work.mkdir(parents=True, exist_ok=True)
    background(work / "bg.jpg")
    title_png(level, ["Guess the surah", f"{QUESTIONS} questions"], work / "intro.png", "Listen, then pick before the timer ends")
    title_png(level, ["How many did you get?", "Comment your score below"], work / "outro.png", "Follow for a new quiz every night")
    segs, audio_parts, events, t = [(work / "intro.png", INTRO)], [], [], INTRO
    audio_parts.append(("silence", INTRO))
    for qi, q in enumerate(qs):
        dur = sum(mr.duration(m) for m in q["mp3s"])
        listen = dur + 0.4
        question_png(q, qi, level, "listen", work / f"q{qi}_listen.png")
        segs.append((work / f"q{qi}_listen.png", listen))
        audio_parts += [("file", m) for m in q["mp3s"]] + [("silence", listen - dur)]
        t += listen
        for k in range(THINK, 0, -1):
            question_png(q, qi, level, k, work / f"q{qi}_{k}.png")
            segs.append((work / f"q{qi}_{k}.png", 1.0))
            events.append((t, "tick"))
            t += 1
        question_png(q, qi, level, "reveal", work / f"q{qi}_reveal.png")
        segs.append((work / f"q{qi}_reveal.png", REVEAL))
        events.append((t, "chime"))
        audio_parts.append(("silence", THINK + REVEAL))
        t += REVEAL
        report(0.1 + 0.4 * (qi + 1) / QUESTIONS)
    segs.append((work / "outro.png", OUTRO))
    audio_parts.append(("silence", OUTRO))
    total = t + OUTRO

    # recitation track: the ayahs at their times, silence between
    ins, flt = [], []
    for i, (kind, v) in enumerate(audio_parts):
        if kind == "file":
            ins += ["-i", str(v)]
        else:
            ins += ["-f", "lavfi", "-t", f"{v:.3f}", "-i", "anullsrc=r=48000:cl=mono"]
        flt.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=mono[a{i}]")
    n = len(audio_parts)
    flt.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1[rec]")
    sound_track(events, total, work / "fx.wav")
    ins += ["-i", str(work / "fx.wav")]
    flt.append(f"[rec][{n}:a]amix=inputs=2:normalize=0,afade=t=out:st={total - 1:.2f}:d=1[aout]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(flt), "-map", "[aout]",
                    "-t", f"{total:.2f}", "-ac", "2", "-c:a", "aac", "-b:a", "160k", str(work / "audio.m4a")], check=True, timeout=300)
    with open(work / "cards.txt", "w") as f:
        for p, dsec in segs:
            f.write(f"file '{p.resolve()}'\nduration {dsec:.3f}\n")
        f.write(f"file '{segs[-1][0].resolve()}'\n")
    report(0.6)
    bw, bh = int(W * 1.12), int(H * 1.12)
    fc = (f"[0:v]crop={W}:{H}:x='({bw - W})/2+({bw - W})/2*sin(t/{total:.2f}*3.1416)':y='({bh - H})/2',format=yuv420p,fps=30[bg];"
          f"[1:v]format=rgba,fps=30[c];[bg][c]overlay=0:0:eof_action=repeat,fade=t=out:st={total - 0.6:.2f}:d=0.6[v]")
    mr.OUT.mkdir(exist_ok=True)
    mp4 = mr.OUT / f"quiz_{level}_{seed}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(work / "bg.jpg"), "-f", "concat", "-safe", "0",
                    "-i", str(work / "cards.txt"), "-i", str(work / "audio.m4a"), "-filter_complex", fc, "-map", "[v]", "-map", "2:a",
                    "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
                    "-c:a", "copy", "-movflags", "+faststart", str(mp4)], check=True, timeout=900)
    report(1.0)
    chs = mr.chapters()
    answers = " · ".join(f"{i + 1}) {chs[q['surah']]['name_simple']}" for i, q in enumerate(qs))
    caption = (f"Guess the surah 🤍 {QUESTIONS} questions, level: {level}.\n\nListen to the ayah and pick before the timer ends. "
               f"How many did you get? Comment your score!\n\nAnswers: {answers}\n\nFollow for a new quiz every night.\n\n"
               f"#quranquiz #guessthesurah #quran #islamicquiz #islam")
    return {"kind": "quiz", "file": str(mp4), "caption": caption, "duration": round(total, 1), "level": level,
            "questions": [[q["surah"], q["ayah"], q["last"]] for q in qs], "reciter": RECITER,
            "title": f"Guess the surah · {level} · " + ", ".join(chs[q["surah"]]["name_simple"] for q in qs)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--level", choices=list(LEVELS), default="easy")
    ap.add_argument("--seed", type=int, default=random.randrange(10**6))
    a = ap.parse_args()
    m = render(a.level, a.seed)
    print(m["file"], m["duration"], "s", m["title"])
