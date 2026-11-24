"""Make a 60-90s vertical Quran Reel: ayah text (Arabic + English) synced to a recitation.

Usage:
  python3 make_reel.py                 # random passage, random reciter
  python3 make_reel.py --start 55:1    # start from a given ayah
  python3 make_reel.py --count 3       # make several
Output goes to reels/<name>.mp4 with a matching caption .txt
"""
import argparse
import json
import math
import random
import re
import subprocess
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

import nature

HERE = Path(__file__).parent
CACHE = HERE / "cache"
OUT = HERE / "reels"
FONTS = HERE / "fonts"
HANDLE = "@tilawah.sakina"
W, H = 1080, 1920
MIN_LEN, MAX_LEN = 60.0, 90.0
TRANSLATION_ID = 20  # Sahih International

RECITERS = {
    "Mishary Alafasy": "Alafasy_128kbps",
    # studio Mujawwad recording (mp3quran.net); everyayah's MaherAlMuaiqly128kbps is a Haram recording with heavy echo
    # studio Murattal (quranicaudio.com, 256 kbps), cut per ayah by align.py; everyayah's own Maher files
    # (MaherAlMuaiqly128kbps, the alignment reference) are Haram recordings with heavy echo
    "Maher Al-Muaiqly": "quranicaudio/maher_256",
    "Yasser Al-Dosari": "Yasser_Ad-Dussary_128kbps",
}

def active_reciters():
    """The reciters picked at random: state/config.json "reciters" (edited in the panel), else the defaults."""
    try:
        r = json.loads((HERE / "state" / "config.json").read_text()).get("reciters")
    except (OSError, ValueError):
        r = None
    return r if isinstance(r, dict) and r else RECITERS


# Passages that work well as short reels: (surah, first ayah)
PASSAGES = [
    (1, 1), (2, 255), (2, 284), (3, 190), (13, 28), (17, 23), (20, 25),
    (23, 1), (25, 63), (31, 12), (36, 77), (39, 53), (55, 1), (55, 26),
    (59, 21), (67, 1), (73, 1), (78, 1), (87, 1), (89, 27), (93, 1),
    (94, 1), (103, 1), (112, 1), (113, 1), (114, 1), (2, 152), (2, 186),
    (3, 26), (24, 35), (40, 60), (65, 2), (21, 87), (14, 7),
]

THEMES = [  # (center color, edge color, accent)
    ((20, 56, 46), (5, 15, 13), (214, 178, 106)),
    ((22, 34, 62), (5, 8, 18), (205, 180, 125)),
    ((48, 30, 22), (12, 7, 5), (222, 186, 120)),
    ((30, 30, 34), (6, 6, 8), (210, 190, 150)),
]


# ---------- data ----------
def fetch(url, dest: Path):
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "reel-maker/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            dest.write_bytes(r.read())
    return dest


def chapters():
    p = fetch("https://api.quran.com/api/v4/chapters", CACHE / "chapters.json")
    return {c["id"]: c for c in json.loads(p.read_text())["chapters"]}


def verse(s, a):
    p = fetch(
        f"https://api.quran.com/api/v4/verses/by_key/{s}:{a}?translations={TRANSLATION_ID}&fields=text_uthmani",
        CACHE / "verses" / f"{s:03d}{a:03d}.json",
    )
    v = json.loads(p.read_text())["verse"]
    en = v["translations"][0]["text"]
    en = re.sub(r"<sup[^>]*>.*?</sup>", "", en)
    en = re.sub(r"<[^>]+>", "", en).strip()
    # waqf (pause) marks are combining characters: after a space they have no base letter and the font
    # draws them on a dotted circle (◌). Attach each one to the word before it.
    ar = re.sub(r"\s+([\u06D6-\u06DC])", r"\1", v["text_uthmani"].strip())
    # the English font has no ﷺ glyph (it renders as an empty box): spell it out
    en = en.replace("(ﷺ)", "(peace be upon him)").replace("ﷺ", "(peace be upon him)")
    return ar, en


MP3QURAN = "https://www.mp3quran.net/api/v3"
# Whole-surah recordings without published timings: (download base, everyayah folder of the same reciter
# used as the reference for align.py). Timings are computed once and kept in timings/<name>/SSS.json.
ALIGNED = {
    "quranicaudio/maher_256": ("https://download.quranicaudio.com/quran/maher_256/", "MaherAlMuaiqly128kbps"),
}
TIMINGS = HERE / "timings"


class UncertainCut(Exception):
    """align.py is not sure where this ayah starts or ends in the recording."""


def aligned_timing(folder, s):
    path = TIMINGS / folder.split("/")[-1] / f"{s:03d}.json"
    if not path.exists():
        import align
        base, ref = ALIGNED[folder]
        whole = fetch(f"{base}{s:03d}.mp3", CACHE / folder / f"surah_{s:03d}.mp3")
        n = chapters()[s]["verses_count"]
        refs = [audio(ref, s, a) for a in range(1, n + 1)]
        timing = align.align(whole, refs)
        for t, r in zip(timing, refs):  # length against the reference: far off means the cut is doubtful
            t["ratio"] = round((t["end_time"] - t["start_time"]) / 1000 / duration(r), 2)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(timing, indent=1) + "\n")
    return json.loads(path.read_text())


def audio(folder, s, a):
    """One ayah as an mp3. folder is an everyayah.com folder, a key of ALIGNED (whole-surah recording cut
    at timings from align.py), or "mp3quran/<read id>" (cut at mp3quran.net's published timings)."""
    out = CACHE / folder / f"{s:03d}{a:03d}.mp3"
    if folder in ALIGNED:
        t = next(x for x in aligned_timing(folder, s) if x["ayah"] == a)
        if not 0.72 <= t.get("ratio", 1) <= 1.4:
            raise UncertainCut(f"{s}:{a}")
        if not out.exists():
            whole = CACHE / folder / f"surah_{s:03d}.mp3"
            if not whole.exists():
                fetch(f"{ALIGNED[folder][0]}{s:03d}.mp3", whole)
            cut(whole, t["start_time"] / 1000, t["end_time"] / 1000, out)
        return out
    if not folder.startswith("mp3quran/"):
        return fetch(f"https://everyayah.com/data/{folder}/{s:03d}{a:03d}.mp3", out)
    if out.exists():
        return out
    read = folder.split("/", 1)[1]
    reads = json.loads(fetch(f"{MP3QURAN}/ayat_timing/reads", CACHE / "mp3quran" / "reads.json").read_text())
    base = next(r["folder_url"] for r in reads if str(r["id"]) == read)
    whole = fetch(f"{base}{s:03d}.mp3", CACHE / folder / f"surah_{s:03d}.mp3")
    timing = json.loads(fetch(f"{MP3QURAN}/ayat_timing?surah={s}&read={read}",
                              CACHE / folder / f"timing_{s:03d}.json").read_text())
    t = next(x for x in timing if x["ayah"] == a)
    cut(whole, t["start_time"] / 1000, t["end_time"] / 1000, out)
    return out


def cut(whole, start, end, out):
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.3f}", "-to", f"{end:.3f}", "-i", str(whole),
                    "-af", f"afade=t=in:d=0.03,afade=t=out:st={max(0, end - start - 0.06):.3f}:d=0.06",
                    "-ac", "2", "-ar", "44100", "-c:a", "libmp3lame", "-b:a", "192k", str(out)], check=True)


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(out.strip())


def pick_ayahs(chs, folder, surah, start):
    """Consecutive ayahs from start until the reel is 60-90s long."""
    picked, total = [], 0.0
    a = start
    while a <= chs[surah]["verses_count"]:
        try:
            d = duration(audio(folder, surah, a))
        except UncertainCut:
            break  # stop before an ayah whose cut is doubtful
        if total + d > MAX_LEN:
            break
        picked.append((a, d))
        total += d
        a += 1
        if total >= MIN_LEN and len(picked) >= 1 and total >= 70:
            break
    return picked, total


# ---------- drawing ----------
def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def wrap(draw, text, fnt, max_w, rtl=False):
    words, lines, cur = text.split(), [], ""
    kw = dict(direction="rtl", language="ar") if rtl else {}
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt, **kw) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def background(theme, path):
    """Large still with radial light + faint geometric star pattern; ffmpeg pans across it slowly."""
    bw, bh = int(W * 1.12), int(H * 1.12)
    small = Image.new("RGB", (bw // 4, bh // 4))
    px = small.load()
    c1, c2, _ = theme
    cx, cy = small.width / 2, small.height * 0.42
    for y in range(small.height):
        for x in range(small.width):
            t = min(1.0, math.hypot(x - cx, (y - cy) * 0.8) / (small.width * 0.85)) ** 1.3
            px[x, y] = tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))
    img = small.resize((bw, bh), Image.BICUBIC)

    pat = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(pat)
    acc = theme[2]
    step = 180
    for gy in range(-step, bh + step, step):
        for gx in range(-step, bw + step, step):
            ox = gx + (step // 2 if (gy // step) % 2 else 0)
            for k in range(2):  # 8-point star from two squares
                pts = [
                    (ox + 46 * math.cos(math.radians(45 * k + 90 * i + 45)),
                     gy + 46 * math.sin(math.radians(45 * k + 90 * i + 45)))
                    for i in range(4)
                ]
                d.polygon(pts, outline=acc + (20,))
    img = Image.alpha_composite(img.convert("RGBA"), pat)

    glow = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((bw * 0.15, bh * 0.25, bw * 0.85, bh * 0.6), fill=acc + (28,))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(160)))
    img.convert("RGB").save(path, quality=95)


def with_shadow(img, path):
    shadow = img.filter(ImageFilter.GaussianBlur(6))
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sh.putalpha(shadow.getchannel("A").point(lambda v: int(v * 0.6)))
    Image.alpha_composite(sh, img).save(path)


def frame_layer(theme, surah_info, reciter, path):
    """Header + footer that stay on screen the whole reel."""
    acc = theme[2]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((W / 2, 250), "سورة " + surah_info["name_arabic"], font=font("Amiri-Bold.ttf", 68),
           fill=acc + (255,), anchor="mm", direction="rtl", language="ar")
    d.text((W / 2, 335), f"Surah {surah_info['name_simple']}", font=font("Lora-var.ttf", 36),
           fill=(235, 228, 212, 200), anchor="mm")
    d.line((W / 2 - 70, 385, W / 2 + 70, 385), fill=acc + (160,), width=2)
    d.text((W / 2, 1600), reciter, font=font("Lora-var.ttf", 34), fill=acc + (230,), anchor="mm")
    d.text((W / 2, 1650), HANDLE, font=font("Lora-var.ttf", 30), fill=(235, 228, 212, 150), anchor="mm")
    with_shadow(img, path)


def dim_panel(frame_path):
    """Darken the area behind the ayah text (for busy video backgrounds), under the header/footer layer."""
    panel = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(panel).rounded_rectangle((50, 430, W - 50, 1520), 48, fill=(4, 8, 12, 118))
    panel = panel.filter(ImageFilter.GaussianBlur(28))
    Image.alpha_composite(panel, Image.open(frame_path).convert("RGBA")).save(frame_path)


def card(theme, surah_info, s, a, ar, en, reciter, path):
    acc = theme[2]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Arabic: shrink until it fits the box; return False if it can't fit at a readable size
    max_w = W - 150
    fits = False
    for size in range(96, 54, -4):
        far = font("AmiriQuran-Regular.ttf", size)
        lines_ar = wrap(d, ar, far, max_w, rtl=True)
        lh_ar = int(size * 2.0)
        fen_size = max(30, int(size * 0.5))
        fen = font("Lora-var.ttf", fen_size)
        lines_en = wrap(d, en, fen, max_w)
        lh_en = int(fen_size * 1.45)
        block = len(lines_ar) * lh_ar + 70 + len(lines_en) * lh_en + 60
        if block <= 1060:
            fits = True
            break
    if not fits:
        return False

    y = 975 - block / 2
    for ln in lines_ar:
        d.text((W / 2, y + lh_ar / 2), ln, font=far, fill=(250, 244, 230, 255), anchor="mm",
               direction="rtl", language="ar")
        y += lh_ar
    y += 70
    for ln in lines_en:
        d.text((W / 2, y + lh_en / 2), ln, font=fen, fill=(225, 218, 200, 235), anchor="mm")
        y += lh_en
    d.text((W / 2, y + 45), f"{s}:{a}", font=font("Lora-var.ttf", 30), fill=acc + (200,), anchor="mm")
    with_shadow(img, path)
    return True


def split_parts(ar, en, n):
    """Split an ayah into n screens: Arabic by words, English by sentences/clauses near the same fractions."""
    aw = []
    for tok in ar.split():  # keep standalone pause marks (e.g. ۚ ۖ) glued to the previous word
        if aw and all(0x06D6 <= ord(ch) <= 0x06ED for ch in tok):
            aw[-1] += " " + tok
        else:
            aw.append(tok)
    cuts = [round(len(aw) * k / n) for k in range(n + 1)]
    ar_parts = [" ".join(aw[cuts[k]:cuts[k + 1]]) for k in range(n)]
    shares = [(cuts[k + 1] - cuts[k]) / len(aw) for k in range(n)]

    pieces = [p for p in re.split(r"(?<=[.;:,?!])\s+", en) if p]
    total = sum(len(p) for p in pieces)
    en_parts, acc_len, k, cur = [], 0, 0, []
    target = shares[0] * total
    for p in pieces:
        cur.append(p)
        acc_len += len(p)
        if acc_len >= target and k < n - 1:
            en_parts.append(" ".join(cur))
            cur, k = [], k + 1
            target += shares[k] * total
    en_parts.append(" ".join(cur))
    while len(en_parts) < n:
        en_parts.append("")
    return list(zip(ar_parts, en_parts)), shares


def clean_hook(english):
    """First sentence of the first ayah as the caption's opening line, without dangling quotes or dashes."""
    text = english.replace('"', "").replace("\u201c", "").replace("\u201d", "").strip()
    first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
    first = first.rstrip(" -\u2013\u2014,;:.")
    return first + "."


# ---------- assembly ----------
def build(start=None, seed=None, exclude=(), reciter=None, surah=None, progress=None):
    """start=(surah, ayah) or surah=N (a random passage of that surah) or neither (a curated passage).
    reciter: a RECITERS name, random when None. progress(fraction) is called while rendering."""
    rnd = random.Random(seed)
    chs = chapters()
    pool = active_reciters()
    known = {**RECITERS, **pool}
    reciter = reciter if reciter in known else rnd.choice(list(pool))
    folder = known[reciter]
    theme = rnd.choice(THEMES)
    report = progress or (lambda frac: None)
    report(0.0)

    if start:
        candidates = [tuple(start)]
    elif surah:
        n = chs[surah]["verses_count"]
        starts = [a for a in rnd.sample(range(1, n + 1), n) if (surah, a) not in set(exclude)][:8]
        candidates = [(surah, a) for a in starts] or [(surah, 1)]
    else:
        candidates = [p for p in rnd.sample(PASSAGES, len(PASSAGES)) if p not in set(exclude)]
    chosen = None
    for s, a0 in candidates:
        ayahs, total = pick_ayahs(chs, folder, s, a0)
        if ayahs and total >= MIN_LEN:
            chosen = (s, a0, ayahs, total)
            break
        if ayahs and total >= 45 and start:  # explicit start: accept a bit shorter
            chosen = (s, a0, ayahs, total)
            break
    if not chosen and (start or surah):
        # a short surah (or the tail of one): the reel is the whole surah from its first ayah
        s = start[0] if start else surah
        ayahs, total = pick_ayahs(chs, folder, s, 1)
        if ayahs:
            chosen = (s, 1, ayahs, total)
    if not chosen:
        raise SystemExit("No passage fit the 60-90s window")
    s, a0, ayahs, total = chosen
    whole = a0 == 1 and ayahs[-1][0] == chs[s]["verses_count"]
    report(0.1)

    tag = re.sub(r"\W", "", folder.split("/")[-1].split("_")[0].split("128")[0]) or "reciter"
    name = f"{s:03d}_{a0:03d}-{ayahs[-1][0]:03d}_{tag}"
    work = CACHE / "work" / name
    work.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(exist_ok=True)

    background(theme, work / "bg.jpg")
    frame_layer(theme, chs[s], reciter, work / "frame.png")
    texts, cards, t = [], [], 0.0
    for a, dur in ayahs:
        ar, en = verse(s, a)
        texts.append((a, ar, en))
        for n in range(1, 6):
            parts, shares = split_parts(ar, en, n) if n > 1 else ([(ar, en)], [1.0])
            paths = [work / f"card_{a:03d}_{k}.png" for k in range(n)]
            if all(card(theme, chs[s], s, a, pa, pe, reciter, pp) for (pa, pe), pp in zip(parts, paths)):
                break
        else:
            raise SystemExit(f"Ayah {s}:{a} too long to display")
        for pp, sh in zip(paths, shares):
            cards.append((pp, t, dur * sh))
            t += dur * sh
    total = t + 0.6

    # audio list
    (work / "audio.txt").write_text("".join(f"file '{audio(folder, s, a).resolve()}'\n" for a, _ in ayahs))

    # background: real nature video (Pixabay) when the key is set, else the drawn one
    scene = None
    if nature.available():
        try:
            scene, clips = nature.pick(total, rnd)
            nature.render_background(clips, total, work / "bg.mp4")
            dim_panel(work / "frame.png")
        except Exception as e:  # noqa: BLE001
            print(f"nature background failed ({e}), using the drawn one")
            scene = None
    inputs = (["-stream_loop", "-1", "-i", str(work / "bg.mp4")] if scene else ["-loop", "1", "-i", str(work / "bg.jpg")]) + [
              "-f", "concat", "-safe", "0", "-i", str(work / "audio.txt"),
              "-loop", "1", "-i", str(work / "frame.png")]
    for p, _, _ in cards:
        inputs += ["-i", str(p)]

    bw, bh = int(W * 1.12), int(H * 1.12)
    f = [f"[0:v]format=yuv420p,fps=30[bg0]" if scene else
         f"[0:v]crop={W}:{H}:x='({bw - W})/2+({bw - W})/2*sin(t/{total:.2f}*3.1416)':"
         f"y='({bh - H})*t/{total:.2f}',format=yuv420p,fps=30[bg0]",
         "[bg0][2:v]overlay=0:0:shortest=1[bg]"]
    last = "bg"
    fd = 0.35
    for i, (p, st, dur) in enumerate(cards):
        idx = i + 3
        f.append(f"[{idx}:v]format=rgba,loop=-1:1:0,trim=duration={dur:.3f},setpts=PTS-STARTPTS,"
                 # the first card is fully visible from frame 0: Instagram uses frame 0 as the default cover
                 + (f"fade=t=in:st=0:d={fd}:alpha=1," if i else "")
                 + f"fade=t=out:st={max(0, dur - fd):.3f}:d={fd}:alpha=1,"
                 f"setpts=PTS+{st:.3f}/TB[c{i}]")
        f.append(f"[{last}][c{i}]overlay=0:0:eof_action=pass[v{i}]")
        last = f"v{i}"
    f.append(f"[{last}]fade=t=out:st={total - 0.6:.2f}:d=0.6[vout]")

    mp4 = OUT / f"{name}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(f),
           "-map", "[vout]", "-map", "1:a", "-t", f"{total:.2f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
           "-c:a", "aac", "-b:a", "160k", "-af", f"apad,afade=t=out:st={total - 0.8:.2f}:d=0.8",
           "-movflags", "+faststart", str(mp4)]
    # -progress prints out_time_us=... lines: turn them into a 10-100% render progress
    cmd[1:1] = ["-progress", "pipe:1", "-nostats"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    for line in proc.stdout:
        if line.startswith("out_time_us="):
            try:
                report(0.1 + 0.9 * min(1.0, int(line.split("=")[1]) / 1e6 / total))
            except ValueError:
                pass
    if proc.wait():
        raise subprocess.CalledProcessError(proc.returncode, cmd)
    report(1.0)

    ch = chs[s]
    ref = f"{s}:{a0}" if len(ayahs) == 1 else f"{s}:{a0}-{ayahs[-1][0]}"
    hook = clean_hook(texts[0][2])
    caption = (
        f"{hook}\n\n"
        f"Surah {ch['name_simple']} ({ch['translated_name']['name']}) · {ref}\n"
        f"Recited by {reciter}\n\n"
        f"Listen till the end and share it with someone who needs it today 🤍\n\n"
        f"#quran #quranrecitation #islam #{re.sub(r'[^a-z]', '', ch['name_simple'].lower())} #{re.sub(r'[^a-z]', '', reciter.split('(')[0].split()[-1].lower())}"
    )
    (OUT / f"{name}.txt").write_text(caption + "\n")
    print(f"{mp4}  ({total:.1f}s, {len(ayahs)} ayahs, {reciter})")
    return {
        "kind": "ayah", "file": str(mp4), "caption": caption, "duration": round(total, 1),
        "passage": [s, a0], "ref": ref, "whole_surah": whole, "surah": ch["name_simple"], "reciter": reciter,
        "title": f"Surah {ch['name_simple']} {ref} · {reciter}", "background": scene or "drawn",
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", help="surah:ayah, e.g. 55:1")
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--seed", type=int)
    args = ap.parse_args()
    start = tuple(int(x) for x in args.start.split(":")) if args.start else None
    for i in range(args.count):
        build(start, None if args.seed is None else args.seed + i)
