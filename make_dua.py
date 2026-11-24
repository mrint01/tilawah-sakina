"""Make a dua Reel: Arabic dua + English meaning on screen, recited audio, in the ayah-reel look.

Text and audio come from Hisn al-Muslim (hisnmuslim.com). dua_catalog.json is the vetted list
(built once with --build-catalog: only duas that fit on screen and last at most a minute).

Usage:
  python3 make_dua.py --list
  python3 make_dua.py --category morning          # least-used morning dua
  python3 make_dua.py --id 79                     # one specific dua
  python3 make_dua.py --build-catalog             # refresh dua_catalog.json from hisnmuslim.com
Output: reels/dua_<id>.mp4 + caption .txt
"""
import argparse
import json
import random
import re
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

import make_reel as mr
import scenes

HERE = Path(__file__).parent
CATALOG = HERE / "dua_catalog.json"
CACHE = mr.CACHE / "dua"
OUT = mr.OUT
W, H = mr.W, mr.H
API = "https://www.hisnmuslim.com/api/en/{}.json"
MAX_SECONDS = 60.0

# What the 06:00 dua posts, by kind. Hisn al-Muslim chapter numbers (+ single extra duas).
CATEGORIES = {
    "morning": {
        "label": "Morning adhkar", "ar": "أذكار الصباح", "en": "Morning Adhkar",
        "chapters": [27], "skip": [75, 76, 91, 93, 96, 98],  # long Quran passages, 100× dhikr, salawat (in friday)
        "hook": "Start your morning with this dhikr 🤍",
        "tags": "#morningadhkar #adhkar #dua #dhikr #islam",
    },
    "after_salah": {
        "label": "Dua after salah", "ar": "أذكار بعد الصلاة", "en": "After Salah",
        "chapters": [24, 25], "skip": [69, 70, 71],  # 33× tasbih (has its own reels), long Quran passages
        "hook": "Say this after your salah 🤍",
        "tags": "#afterSalah #dua #adhkar #salah #islam",
    },
    "need": {
        "label": "Dua for a need", "ar": "دعاء", "en": "Dua for Every Need",
        "chapters": [34, 35, 41, 43, 46, 53, 129], "skip": [253],  # 253 is a hadith, not a dua
        "hook": "A dua for the heart that needs it today 🤍",
        "tags": "#dua #duas #tawakkul #istighfar #islam",
    },
    "friday": {
        "label": "Salawat & Friday", "ar": "الصلاة على النبي ﷺ", "en": "Salawat · Jumu'ah",
        "chapters": [23], "extra": [98], "skip": [],
        "hook": "Send salawat upon the Prophet ﷺ today, it is Jumu'ah 🤍",
        "tags": "#jumuah #salawat #durood #friday #islam",
    },
    "arafah": {
        "label": "Day of Arafah", "ar": "دعاء يوم عرفة", "en": "The Day of Arafah",
        "chapters": [119], "skip": [],
        "hook": "The best dua is the dua of the Day of Arafah 🤍",
        "tags": "#arafah #dhulhijjah #hajj #dua #islam",
    },
}

# Known hadith sources, shown on screen and in the caption (else "Hisn al-Muslim").
SOURCES = {79: "Sahih al-Bukhari", 73: "Ibn Majah", 95: "Ibn Majah", 237: "Jami' at-Tirmidhi", 66: "Sahih Muslim",
           67: "Sahih al-Bukhari", 86: "Abu Dawud & at-Tirmidhi", 97: "Sahih Muslim", 88: "al-Hakim", 84: "Abu Dawud & Ibn Majah"}

REPEAT_WORDS = {2: "twice", 3: "3 times", 4: "4 times"}

# Translations whose source text mixes in notes or the hadith around the dua.
EN_OVERRIDES = {
    66: "I ask Allah for forgiveness. O Allah, You are As-Salam and from You is all peace, blessed are You, "
        "O Possessor of majesty and honour.",
    80: "O Allah, I have reached the morning and call on You, the bearers of Your throne, Your angels and all of "
        "Your creation to witness that You are Allah, none has the right to be worshipped except You, alone, "
        "without partner, and that Muhammad is Your servant and Messenger.",
    82: "O Allah, grant my body health, O Allah, grant my hearing health, O Allah, grant my sight health. None has "
        "the right to be worshipped except You. O Allah, I take refuge with You from disbelief and poverty, and I "
        "take refuge with You from the punishment of the grave. None has the right to be worshipped except You.",
    144: "Allah has decreed, and what He wills, He does.",
    237: "The best dua is the dua of the Day of Arafah, and the best of what I and the Prophets before me have said "
         "is: None has the right to be worshipped except Allah, alone, without partner. To Him belongs all "
         "sovereignty and praise, and He is over all things omnipotent.",
    250: "Whoever says: I seek forgiveness from Allah the Mighty, besides whom none has the right to be worshipped, "
         "the Ever Living, the Self-Subsisting, and I turn to Him in repentance, Allah forgives him, even if he "
         "fled from the battlefield.",
}


# ---------- catalog ----------
def clean_ar(t):
    m = re.search(r"\(\((.*)\)\)", t, re.S)
    t = m.group(1) if m else t
    t = re.sub(r"\([^()]*\)", "", t)                  # notes like (ثلاثاً) inside the dua
    t = t.replace("﴿", "").replace("﴾", "").replace("*", "")
    return re.sub(r"\s+", " ", t).strip(" .،")


def clean_en(t):
    t = t.replace("AA", "'").replace("‘", "'").replace("’", "'").replace("Allaah", "Allah")
    t = re.sub(r"[.)]\s*\)\s*\(.*$", ".", t, flags=re.S)  # ")(note: ...)" after the dua
    t = re.sub(r"\(i\.e\.[^)]*\)|“i\.e\.[^”]*”", "", t)
    t = re.sub(r"\[[^\]]*\]", "", t)                  # [references]
    t = re.sub(r"\((?:[^()]*\b(?:times?|twice|once|morning|evening|prayer|said)\b[^()]*)\)", "", t, flags=re.I)
    t = re.sub(r"\s+", " ", t).strip()
    while t.startswith("(") and t.count("(") > t.count(")") or t.startswith("(") and t.endswith(")"):
        t = t[1:-1].strip() if t.endswith(")") else t[1:].strip()
    t = t.strip(" '‘’\"").replace("(", "").replace(")", "")
    t = re.sub(r"\s+([,.])", r"\1", t)
    t = re.sub(r"\.(?=[A-Z])", ". ", t)
    return re.sub(r"\s+", " ", t).strip().rstrip(".") + "."


def duration(path):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                          "-of", "csv=p=0", str(path)]))


def audio_file(entry):
    p = CACHE / "audio" / f"{entry['id']}.mp3"
    if not p.exists():
        mr.fetch(entry["audio"], p)
    return p


def plays(entry):
    """How many times the recitation plays: the dua's own count (2-4) when it fits in a minute, short ones twice."""
    n = entry["repeat"] if 2 <= entry["repeat"] <= 4 else 1
    while n > 1 and n * entry["seconds"] + (n - 1) * 1.2 + 2.8 > MAX_SECONDS:
        n -= 1
    if n == 1 and entry["seconds"] < 14:
        n = 2
    return n


def build_catalog():
    import tempfile
    entries = []
    probe_dir = Path(tempfile.mkdtemp())
    for cat, spec in CATEGORIES.items():
        want = {}
        for ch in spec["chapters"]:
            p = mr.fetch(API.format(ch), CACHE / f"en{ch}.json")
            for it in list(json.loads(p.read_text(encoding="utf-8-sig")).values())[0]:
                want[it["ID"]] = it
        for extra in spec.get("extra", []):
            for ch in CATEGORIES["morning"]["chapters"]:
                p = mr.fetch(API.format(ch), CACHE / f"en{ch}.json")
                for it in list(json.loads(p.read_text(encoding="utf-8-sig")).values())[0]:
                    if it["ID"] == extra:
                        want[extra] = it
        for i, it in sorted(want.items()):
            if i in spec["skip"] or not it.get("AUDIO"):
                continue
            rep = int(it.get("REPEAT") or 1)
            if rep > 4:
                continue
            e = {"id": i, "category": cat, "ar": clean_ar(it["ARABIC_TEXT"]), "en": EN_OVERRIDES.get(it["ID"]) or clean_en(it["TRANSLATED_TEXT"]),
                 "repeat": rep, "audio": it["AUDIO"].replace("http://", "https://"), "source": SOURCES.get(i, "Hisn al-Muslim")}
            if not e["ar"] or len(e["en"]) < 8:
                continue
            try:
                e["seconds"] = round(duration(audio_file(e)), 2)
            except Exception as ex:  # noqa: BLE001
                print(f"skip {i}: audio {ex}")
                continue
            if e["seconds"] > MAX_SECONDS - 3 or e["seconds"] < 3:
                print(f"skip {i}: {e['seconds']}s")
                continue
            screens = cards(e, probe_dir)
            if not screens:
                print(f"skip {i}: too long to show")
                continue
            e["screens"] = len(screens)
            entries.append(e)
            print(f"{cat:12} {i:4} {e['seconds']:5.1f}s ×{plays(e)} {len(screens)} screen(s)  {e['en'][:60]}")
    CATALOG.write_text(json.dumps({"source": "Hisn al-Muslim, hisnmuslim.com", "duas": entries}, ensure_ascii=False, indent=1) + "\n")
    print(f"{len(entries)} duas -> {CATALOG.name}")


def catalog():
    return json.loads(CATALOG.read_text())["duas"]


# ---------- drawing ----------
# Sky per kind of dua (top -> bottom) and where the light comes from; the dua sits inside a pointed arch (mihrab).
SKIES = {
    "morning": [(0, (22, 18, 44)), (0.45, (58, 34, 66)), (0.75, (150, 82, 70)), (1, (232, 160, 92))],
    "after_salah": [(0, (6, 22, 30)), (0.5, (12, 48, 56)), (0.85, (34, 92, 88)), (1, (60, 120, 104))],
    "need": [(0, (14, 12, 42)), (0.5, (40, 28, 84)), (0.85, (86, 58, 120)), (1, (120, 84, 140))],
    "friday": [(0, (8, 30, 24)), (0.5, (16, 62, 46)), (0.85, (70, 90, 52)), (1, (150, 130, 70))],
    "arafah": [(0, (40, 30, 50)), (0.4, (120, 70, 60)), (0.75, (210, 140, 80)), (1, (246, 196, 120))],
}
SUN = {"morning": (255, 200, 120), "after_salah": (150, 230, 210), "need": (210, 180, 255),
       "friday": (240, 220, 140), "arafah": (255, 214, 140)}
ARCH = (100, W - 100, 470, 1560)   # x0, x1, apex y, bottom y of the arch
TEXT_BOX = (175, W - 175, 830, 1530)  # where the dua may be written (below the narrow top of the arch)


def background(category, path):
    """Sky gradient, a few stars and the light at the horizon; 12% larger so ffmpeg can drift across it."""
    bw, bh = int(W * 1.12), int(H * 1.12)
    img = scenes.gradient(SKIES[category], bw, bh)
    img = scenes.stars(img, 90, 0, bh * 0.35, seed=5)
    img = scenes.glow(img, (bw / 2 - 520, bh * 0.8, bw / 2 + 520, bh * 1.2), SUN[category], 150, 120)
    img.convert("RGB").save(path, quality=95)


def frame(spec, category, source, path):
    """Everything that stays on screen: crescent, title, label, the arch, source and handle."""
    gold, light = scenes.GOLD, scenes.GOLD_L
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # crescent: a disc minus a shifted disc
    moon = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(moon)
    md.ellipse((W / 2 - 34, 120, W / 2 + 34, 188), fill=255)
    md.ellipse((W / 2 - 16, 108, W / 2 + 50, 174), fill=0)
    img.paste(Image.new("RGBA", (W, H), light + (255,)), (0, 0), moon)
    d.text((W / 2, 255), spec["ar"], font=mr.font("Amiri-Bold.ttf", 64), fill=light + (255,), anchor="mm",
           direction="rtl", language="ar")
    label = spec["en"].upper()
    f = mr.font("Lora-var.ttf", 26)
    tw = d.textlength(label, font=f)
    d.rounded_rectangle((W / 2 - tw / 2 - 26, 306, W / 2 + tw / 2 + 26, 358), 26, fill=(255, 255, 255, 26),
                        outline=gold + (140,), width=2)
    d.text((W / 2, 332), label, font=f, fill=scenes.CREAM + (235,), anchor="mm")
    x0, x1, y0, y1 = ARCH
    inner = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    spring = y0 + scenes.arch_height(x1 - x0)
    ImageDraw.Draw(inner).polygon([(x0, y1)] + scenes.arch_points(x0, x1, spring) + [(x1, y1)], fill=(8, 6, 20, 96))
    img = Image.alpha_composite(inner, img)
    d = ImageDraw.Draw(img)
    for off, col, wd in ((-16, gold + (80,), 2), (0, gold + (225,), 4)):
        a0, a1 = x0 + off, x1 - off
        sp = y0 + off + scenes.arch_height(a1 - a0)
        d.line([(a0, y1 - off)] + scenes.arch_points(a0, a1, sp) + [(a1, y1 - off)], fill=col, width=wd, joint="curve")
    d.text((W / 2, 1640), source, font=mr.font("Lora-var.ttf", 32), fill=light + (240,), anchor="mm")
    d.text((W / 2, 1692), mr.HANDLE, font=mr.font("Lora-var.ttf", 28), fill=(250, 240, 224, 190), anchor="mm")
    mr.with_shadow(img, path)


def card(ar, en, path):
    """The dua (Arabic, a small divider, English) centred in the text box; False when it can't fit."""
    bx0, bx1, by0, by1 = TEXT_BOX
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for size in range(76, 46, -4):
        far = mr.font("Amiri-Regular.ttf", size)
        la = mr.wrap(d, ar, far, bx1 - bx0, rtl=True)
        lha = int(size * 1.8)
        fs = max(28, int(size * 0.45))
        fen = mr.font("Lora-var.ttf", fs)
        le = mr.wrap(d, en, fen, bx1 - bx0 + 20)
        lhe = int(fs * 1.42)
        block = len(la) * lha + 64 + len(le) * lhe
        if block <= by1 - by0:
            break
    else:
        return False
    y = (by0 + by1) / 2 - block / 2
    for ln in la:
        d.text((W / 2, y + lha / 2), ln, font=far, fill=(252, 246, 232, 255), anchor="mm", direction="rtl", language="ar")
        y += lha
    scenes.divider(d, W / 2, y + 32, 80)
    y += 64
    for ln in le:
        d.text((W / 2, y + lhe / 2), ln, font=fen, fill=(236, 228, 212, 235), anchor="mm")
        y += lhe
    mr.with_shadow(img, path)
    return True


def cards(e, work):
    """Split the dua over 1-3 screens; returns [(png, share of the time)] or [] when it can't fit."""
    for n in range(1, 4):
        parts, shares = mr.split_parts(e["ar"], e["en"], n) if n > 1 else ([(e["ar"], e["en"])], [1.0])
        paths = [work / f"card{k}.png" for k in range(n)]
        if all(a and en and card(a, en, p) for (a, en), p in zip(parts, paths)):
            return list(zip(paths, shares))
    return []


# ---------- render ----------
def caption(e, spec):
    rep = f"\n\nSay it {REPEAT_WORDS[e['repeat']]}." if e["repeat"] in REPEAT_WORDS else ""
    return (f"{spec['hook']}\n\n{e['en']}{rep}\n\n{e['source']}\n\n"
            f"Save it and send it to someone you love 🤍\n\n{spec['tags']}")


def render(category=None, dua_id=None, seed=None, used=(), progress=None):
    """Render one dua reel. Picks the least-used dua of the category unless dua_id is given."""
    report = progress or (lambda f: None)
    rnd = random.Random(seed)
    duas = catalog()
    if dua_id is not None:
        e = next(d for d in duas if d["id"] == int(dua_id))
    else:
        pool = [d for d in duas if d["category"] == category]
        if not pool:
            raise SystemExit(f"no duas in category {category!r}")
        rnd.shuffle(pool)
        e = min(pool, key=lambda d: list(used).count(d["id"]))
    spec = CATEGORIES[e["category"]]
    work = mr.CACHE / "work" / f"dua_{e['id']}"
    work.mkdir(parents=True, exist_ok=True)
    background(e["category"], work / "bg.jpg")
    frame(spec, e["category"], e["source"], work / "frame.png")
    screens = cards(e, work)
    if not screens:
        raise SystemExit(f"dua {e['id']} too long to display")
    report(0.15)

    src = audio_file(e)
    dur = duration(src)
    n = plays(e)
    lead, gap = 0.8, 1.2
    total = lead + n * dur + (n - 1) * gap + 2.0
    parts = []
    for r in range(n):
        pre = f"adelay={int(lead * 1000)}:all=1," if r == 0 else ""
        pad = f"apad=pad_dur={gap}" if r < n - 1 else "anull"
        parts.append(f"[{r}:a]aresample=48000,aformat=channel_layouts=stereo,{pre}{pad}[x{r}]")
    flt = ";".join(parts) + ";" + "".join(f"[x{r}]" for r in range(n)) + \
        f"concat=n={n}:v=0:a=1,apad=whole_dur={total:.2f},afade=t=out:st={total - 1:.2f}:d=1[aout]"
    ins = [x for _ in range(n) for x in ("-i", str(src))]
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", flt, "-map", "[aout]",
                    "-t", f"{total:.2f}", "-c:a", "aac", "-b:a", "160k", str(work / "audio.m4a")], check=True, timeout=120)

    # the screens follow each recitation, by word share; the first is visible from frame 0 (Instagram's cover)
    seg = []
    for r in range(n):
        st = 0 if r == 0 else lead + r * (dur + gap) - gap / 2
        en = lead + (r + 1) * (dur + gap) - gap / 2 if r < n - 1 else total
        seg += [(p, (en - st) * sh) for p, sh in screens]
    with open(work / "cards.txt", "w") as f:
        for p, s in seg:
            f.write(f"file '{p.resolve()}'\nduration {s:.3f}\n")
        f.write(f"file '{seg[-1][0].resolve()}'\n")

    bw, bh = int(W * 1.12), int(H * 1.12)
    fc = (f"[0:v]crop={W}:{H}:x='({bw - W})/2+({bw - W})/2*sin(t/{total:.2f}*3.1416)':y='({bh - H})*t/{total:.2f}',"
          f"format=yuv420p,fps=30[bg0];[bg0][1:v]overlay=0:0:shortest=1[bg];[2:v]format=rgba,fps=30[c];"
          f"[bg][c]overlay=0:0:eof_action=repeat,fade=t=out:st={total - 0.6:.2f}:d=0.6[v]")
    OUT.mkdir(exist_ok=True)
    mp4 = OUT / f"dua_{e['id']}.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-progress", "pipe:1", "-nostats",
           "-loop", "1", "-i", str(work / "bg.jpg"), "-loop", "1", "-i", str(work / "frame.png"),
           "-f", "concat", "-safe", "0", "-i", str(work / "cards.txt"), "-i", str(work / "audio.m4a"),
           "-filter_complex", fc, "-map", "[v]", "-map", "3:a", "-t", f"{total:.2f}",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
           "-c:a", "copy", "-movflags", "+faststart", str(mp4)]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True)
    for line in proc.stdout:
        if line.startswith("out_time_us="):
            try:
                report(0.15 + 0.85 * min(1.0, int(line.split("=")[1]) / 1e6 / total))
            except ValueError:
                pass
    if proc.wait():
        raise subprocess.CalledProcessError(proc.returncode, cmd)
    report(1.0)
    text = caption(e, spec)
    (OUT / f"dua_{e['id']}.txt").write_text(text)
    short = e["en"] if len(e["en"]) <= 48 else e["en"][:46].rsplit(" ", 1)[0] + "…"
    return {"kind": "dua", "file": str(mp4), "caption": text, "duration": round(total, 1),
            "category": e["category"], "dua_id": e["id"], "source": e["source"],
            "title": f"{spec['label']} · {short}"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", choices=list(CATEGORIES))
    ap.add_argument("--id", type=int)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--build-catalog", action="store_true")
    a = ap.parse_args()
    if a.build_catalog:
        build_catalog()
    elif a.list:
        for d in catalog():
            print(f"{d['category']:12} {d['id']:4} {d['seconds']:5.1f}s  {d['en'][:70]}")
    else:
        m = render(a.category or "morning", a.id, a.seed)
        print(m["file"], m["duration"], "s")
