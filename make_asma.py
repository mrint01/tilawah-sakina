"""Asma al-Husna series: one Reel per Name of Allah ("Name 12 of 99"), with an ayah that mentions it, recited.

asma_catalog.json is built once (--build-catalog) from api.aladhan.com (names, transliteration, meaning), with a
hand-picked ayah per name (AYAHS, text and translation from api.quran.com). Names that come from the hadith list but
are not used as a name in the Quran get 7:180: "And to Allah belong the best names, so invoke Him by them."

Usage:
  python3 make_asma.py --build-catalog
  python3 make_asma.py --list
  python3 make_asma.py --number 12 [--reciter "Mishary Alafasy"]
"""
import argparse
import json
import random
import re
import subprocess
import unicodedata
import urllib.parse
from pathlib import Path

from PIL import Image, ImageDraw

import make_reel as mr
import scenes

HERE = Path(__file__).parent
CATALOG = HERE / "asma_catalog.json"
CACHE = mr.CACHE / "asma"
W, H = mr.W, mr.H
FALLBACK = (7, 180)
# Ayah for each name (by number in the aladhan list), picked by hand: the classic verse where Allah is called by
# that name or does what the name says. Names that are not used as a name in the Quran get FALLBACK (7:180).
AYAHS = {
    1: (1, 3), 2: (1, 3), 3: (59, 23), 4: (59, 23), 5: (59, 23), 6: (59, 23), 7: (59, 23), 8: (59, 23), 9: (59, 23),
    10: (59, 23), 11: (59, 24), 12: (59, 24), 13: (59, 24), 14: (38, 66), 15: (38, 65), 16: (3, 8), 17: (51, 58),
    18: (34, 26), 19: (2, 32), 20: (2, 245), 21: (2, 245), 24: (3, 26), 25: (3, 26), 26: (2, 127), 27: (42, 11),
    28: (6, 114), 29: (6, 115), 30: (67, 14), 31: (67, 14), 32: (2, 263), 33: (56, 96), 34: (85, 14), 35: (35, 34),
    36: (42, 4), 37: (13, 9), 38: (12, 64), 39: (4, 85), 40: (33, 39), 41: (55, 27), 42: (82, 6), 43: (4, 1),
    44: (11, 61), 45: (2, 115), 46: (39, 1), 47: (85, 14), 48: (11, 73), 49: (22, 7), 50: (4, 79), 51: (22, 62),
    52: (3, 173), 53: (42, 19), 54: (51, 58), 55: (42, 28), 56: (42, 28), 57: (19, 94), 58: (85, 13), 59: (85, 13),
    60: (57, 2), 61: (57, 2), 62: (3, 2), 63: (3, 2), 66: (12, 39), 67: (112, 1), 68: (112, 2), 69: (75, 40),
    70: (54, 55), 73: (57, 3), 74: (57, 3), 75: (57, 3), 76: (57, 3), 78: (13, 9), 79: (52, 28), 80: (2, 37),
    81: (14, 47), 82: (4, 99), 83: (2, 207), 84: (3, 26), 85: (55, 27), 86: (3, 18), 87: (3, 9), 88: (35, 15),
    89: (53, 48), 91: (6, 17), 92: (6, 17), 93: (24, 35), 94: (25, 31), 95: (2, 117), 96: (55, 27), 97: (15, 23),
}


def plain(ar):
    """Arabic without harakat, and with alif wasla / hamza forms folded, for searching and matching."""
    t = "".join(c for c in unicodedata.normalize("NFKD", ar) if not unicodedata.combining(c))
    return t.replace("ٱ", "ا").replace("أ", "أ").strip()


def build_catalog():
    url = "https://api.aladhan.com/v1/asmaAlHusna"
    names = json.loads(mr.fetch(url, CACHE / "names.json").read_text())["data"]
    out = []
    for n in names:
        s, a = AYAHS.get(n["number"], FALLBACK)
        ar, en = mr.verse(s, a)
        out.append({"number": n["number"], "ar": n["name"], "translit": n["transliteration"].replace("  ", " "),
                    "meaning": n["en"]["meaning"], "ayah": [s, a], "ayah_ar": ar, "ayah_en": en})
        print(f"{n['number']:3} {n['transliteration']:22} {s}:{a:<4} {ar[:70]}")
    CATALOG.write_text(json.dumps({"source": "api.aladhan.com + api.quran.com", "names": out}, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(out)} names -> {CATALOG.name}")


def catalog():
    return json.loads(CATALOG.read_text())["names"]


# ---------- drawing: deep green night (like the other reels), gold calligraphy, a ring of 99 dots ----------
# (was warm paper: the only light tile on the dark Instagram grid)
PAPER = [(0, (10, 30, 26)), (0.45, (18, 50, 42)), (1, (5, 14, 12))]
INK = (246, 238, 220)
GOLD_D = (226, 190, 118)


def background(path):
    bw, bh = int(W * 1.12), int(H * 1.12)
    img = scenes.gradient(PAPER, bw, bh)
    img = scenes.glow(img, (bw / 2 - 460, bh * 0.22, bw / 2 + 460, bh * 0.62), (60, 110, 88), 90, 260)
    # faint geometric rosettes like a manuscript border
    pat = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(pat)
    for gy in range(-90, bh + 180, 180):
        for gx in range(-90, bw + 180, 180):
            ox = gx + (90 if (gy // 180) % 2 else 0)
            for k in range(2):
                pts = [(ox + 40 * mr.math.cos(mr.math.radians(45 * k + 90 * i + 45)),
                        gy + 40 * mr.math.sin(mr.math.radians(45 * k + 90 * i + 45))) for i in range(4)]
                d.polygon(pts, outline=GOLD_D + (20,))
    Image.alpha_composite(img, pat).convert("RGB").save(path, quality=95)


def name_layer(n, path):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((W / 2, 200), "THE 99 NAMES OF ALLAH", font=mr.font("Lora-var.ttf", 28), fill=GOLD_D + (230,), anchor="mm")
    d.text((W / 2, 258), f"{n['number']:02d} / 99", font=mr.font("Lora-var.ttf", 40), fill=INK + (230,), anchor="mm")
    # the name, as large as fits
    size = 230
    while size > 120 and d.textlength(n["ar"], font=mr.font("Amiri-Bold.ttf", size), direction="rtl", language="ar") > W - 200:
        size -= 10
    d.text((W / 2, 540), n["ar"], font=mr.font("Amiri-Bold.ttf", size), fill=GOLD_D + (255,), anchor="mm",
           direction="rtl", language="ar")
    d.text((W / 2, 760), n["translit"].upper(), font=mr.font("Lora-var.ttf", 34), fill=INK + (220,), anchor="mm")
    fm = mr.font("Lora-var.ttf", 50)
    y = 840
    for ln in mr.wrap(d, n["meaning"], fm, W - 200):
        d.text((W / 2, y), ln, font=fm, fill=GOLD_D + (255,), anchor="mm")
        y += 62
    scenes.divider(d, W / 2, y + 20, 110, GOLD_D)
    return img, y + 60


def ayah_layer(n, top, path):
    """The ayah under the name; shrinks to fit between `top` and the dots ring."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s, a = n["ayah"]
    for size in range(60, 36, -4):
        far = mr.font("AmiriQuran-Regular.ttf", size)
        la = mr.wrap(d, n["ayah_ar"], far, W - 220, rtl=True)
        fs = max(26, int(size * 0.5))
        fen = mr.font("Lora-var.ttf", fs)
        le = mr.wrap(d, n["ayah_en"], fen, W - 230)
        block = len(la) * int(size * 1.9) + 30 + len(le) * int(fs * 1.4) + 50
        if top + block <= 1560:
            break
    y = top
    for ln in la:
        d.text((W / 2, y + size), ln, font=far, fill=INK + (255,), anchor="mm", direction="rtl", language="ar")
        y += int(size * 1.9)
    y += 30
    for ln in le:
        d.text((W / 2, y + fs * 0.7), ln, font=fen, fill=INK + (200,), anchor="mm")
        y += int(fs * 1.4)
    d.text((W / 2, y + 30), f"{mr.chapters()[s]['name_simple']} {s}:{a}", font=mr.font("Lora-var.ttf", 28),
           fill=GOLD_D + (230,), anchor="mm")
    return img


def dots_layer(number, path):
    """99 small dots in a grid, the ones up to this name filled: the series' progress."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cols, gap, r = 33, 26, 7
    x0 = W / 2 - (cols - 1) * gap / 2
    for i in range(99):
        x, y = x0 + (i % cols) * gap, 1640 + (i // cols) * gap
        if i < number:
            d.ellipse((x - r, y - r, x + r, y + r), fill=GOLD_D + (255 if i == number - 1 else 200,))
        else:
            d.ellipse((x - r, y - r, x + r, y + r), outline=GOLD_D + (110,), width=2)
    d.text((W / 2, 1760), mr.HANDLE, font=mr.font("Lora-var.ttf", 28), fill=INK + (170,), anchor="mm")
    return img


def still(number, out):
    """One frame of the reel (no audio): for covers."""
    n = next(x for x in catalog() if x["number"] == int(number))
    work = mr.CACHE / "work" / f"asma_{n['number']:02d}"
    work.mkdir(parents=True, exist_ok=True)
    background(work / "bg.jpg")
    name, top = name_layer(n, None)
    full = Image.alpha_composite(Image.alpha_composite(name, ayah_layer(n, top, None)), dots_layer(n["number"], None))
    layer = scenes.shadowed(Image.new("RGBA", (W, H), (0, 0, 0, 0)), full, 10, 0.55)
    bg = Image.open(work / "bg.jpg").convert("RGBA")
    bw, bh = bg.size
    bg = bg.crop(((bw - W) // 2, (bh - H) // 2, (bw - W) // 2 + W, (bh - H) // 2 + H))
    Image.alpha_composite(bg, layer).convert("RGB").save(out, quality=95)
    return n


def caption(n):
    s, a = n["ayah"]
    return (f"{n['ar']} · {n['translit']}\n{n['meaning']}\n\nName {n['number']} of 99. "
            f"Follow so you don't miss the next one 🤍\n\n\"{n['ayah_en']}\" ({mr.chapters()[s]['name_simple']} {s}:{a})\n\n"
            f"The Prophet ﷺ said: Allah has ninety-nine names; whoever learns them will enter Paradise (Bukhari & Muslim).\n\n"
            f"#asmaulhusna #99namesofallah #allah #islam #quran")


def render(number, reciter=None, seed=None, progress=None):
    report = progress or (lambda f: None)
    rnd = random.Random(seed)
    n = next(x for x in catalog() if x["number"] == int(number))
    pool = mr.active_reciters()
    known = {**mr.RECITERS, **pool}
    reciter = reciter if reciter in known else rnd.choice(list(pool))
    work = mr.CACHE / "work" / f"asma_{n['number']:02d}"
    work.mkdir(parents=True, exist_ok=True)
    background(work / "bg.jpg")
    name, top = name_layer(n, None)
    full = Image.alpha_composite(Image.alpha_composite(name, ayah_layer(n, top, None)), dots_layer(n["number"], None))
    scenes.shadowed(Image.new("RGBA", (W, H), (0, 0, 0, 0)), full, 10, 0.55).save(work / "layer.png")
    report(0.2)
    s, a = n["ayah"]
    # some whole-surah recordings can't be cut cleanly at every ayah: then use another reciter
    src = None
    for name in [reciter] + [r for r in known if r != reciter]:
        try:
            src = mr.audio(known[name], s, a)
            reciter = name
            break
        except Exception as e:  # noqa: BLE001
            print(f"{name}: no clean audio for {s}:{a} ({e}), trying another reciter")
    if src is None:
        raise SystemExit(f"no recitation found for {s}:{a}")
    dur = mr.duration(src)
    lead, tail = 1.5, 2.0
    total = lead + dur + tail
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af",
                    f"adelay={int(lead * 1000)}:all=1,apad=whole_dur={total:.2f},afade=t=out:st={total - 1:.2f}:d=1",
                    "-t", f"{total:.2f}", "-ar", "48000", "-c:a", "aac", "-b:a", "160k", str(work / "audio.m4a")], check=True)
    bw, bh = int(W * 1.12), int(H * 1.12)
    fc = (f"[0:v]crop={W}:{H}:x='({bw - W})/2+({bw - W})/2*sin(t/{total:.2f}*3.1416)':y='({bh - H})/2',format=yuv420p,fps=30[bg];"
          f"[1:v]format=rgba[l];[bg][l]overlay=0:0,fade=t=out:st={total - 0.6:.2f}:d=0.6[v]")
    mr.OUT.mkdir(exist_ok=True)
    mp4 = mr.OUT / f"asma_{n['number']:02d}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(work / "bg.jpg"), "-loop", "1", "-i",
                    str(work / "layer.png"), "-i", str(work / "audio.m4a"), "-filter_complex", fc, "-map", "[v]", "-map", "2:a",
                    "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-r", "30", "-c:a", "copy", "-movflags", "+faststart", str(mp4)], check=True)
    report(1.0)
    return {"kind": "asma", "file": str(mp4), "caption": caption(n), "duration": round(total, 1), "number": n["number"],
            "reciter": reciter, "title": f"Name {n['number']} of 99 · {n['translit']} · {n['meaning']}"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build-catalog", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--number", type=int)
    ap.add_argument("--reciter")
    a = ap.parse_args()
    if a.build_catalog:
        build_catalog()
    elif a.list:
        for x in catalog():
            print(x["number"], x["translit"], x["meaning"], "{}:{}".format(*x["ayah"]))
    else:
        m = render(a.number or 1, a.reciter)
        print(m["file"], m["duration"], "s")
