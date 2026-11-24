"""Make a tasbih (dhikr counter) Reel: phrase on screen, misbaha bead ring, counter, bead-click sound.

Usage:
  python3 make_tasbih.py                    # random dhikr set
  python3 make_tasbih.py --set after_salah  # 33/33/34
  python3 make_tasbih.py --list
Output: reels/tasbih_<set>.mp4 + caption .txt
"""
import argparse
import math
import random
import subprocess
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import scenes

HERE = Path(__file__).parent
FONTS = HERE / "fonts"
OUT = HERE / "reels"
HANDLE = "@tilawah.sakina"
W, H, FPS = 1080, 1920, 30
TOTAL = 60.0         # every tasbih Reel is exactly one minute
INTRO, OUTRO = 1.2, 2.6
SR = 44100

PHRASES = {
    "subhanallah": ("سُبْحَانَ ٱللَّهِ", "SubhanAllah", "Glory be to Allah"),
    "alhamdulillah": ("ٱلْحَمْدُ لِلَّهِ", "Alhamdulillah", "All praise is for Allah"),
    "allahuakbar": ("ٱللَّهُ أَكْبَرُ", "Allahu Akbar", "Allah is the Greatest"),
    "wabihamdihi": ("سُبْحَانَ ٱللَّهِ وَبِحَمْدِهِ", "SubhanAllahi wa bihamdihi", "Glory be to Allah and praise Him"),
    "astaghfirullah": ("أَسْتَغْفِرُ ٱللَّهَ", "Astaghfirullah", "I seek forgiveness from Allah"),
    "tahlil": ("لَا إِلَٰهَ إِلَّا ٱللَّهُ", "La ilaha illallah", "There is no god but Allah"),
    "salawat": ("ٱللَّهُمَّ صَلِّ عَلَىٰ مُحَمَّدٍ ﷺ", "Allahumma salli 'ala Muhammad", "O Allah, send blessings upon Muhammad ﷺ"),
}

# One Reel = one full turn of the misbaha: 33 counts, counting DOWN to 0, always 60 s.
# Each set has one phrase; "100x" hadiths become "repeat 3 times" in the caption.
SETS = {
    "subhanallah": {
        "title": "33× SubhanAllah",
        "steps": [("subhanallah", 33)],
        "hook": "33 SubhanAllah after every salah. Count down with the beads 🤍",
        "tags": "#tasbih #dhikr #subhanallah #aftersalah #islam",
    },
    "alhamdulillah": {
        "title": "33× Alhamdulillah",
        "steps": [("alhamdulillah", 33)],
        "hook": "Alhamdulillah fills the scale (Muslim). 33 times, one minute 🤍",
        "tags": "#alhamdulillah #dhikr #tasbih #gratitude #islam",
    },
    "allahuakbar": {
        "title": "33× Allahu Akbar",
        "steps": [("allahuakbar", 33)],
        "hook": "33 Allahu Akbar after your salah. One minute with your Lord 🤍",
        "tags": "#allahuakbar #dhikr #tasbih #aftersalah #islam",
    },
    "wabihamdihi": {
        "title": "33× SubhanAllahi wa bihamdihi",
        "steps": [("wabihamdihi", 33)],
        "hook": "Say it 100 times and your sins are wiped away, even if they are like the foam of the sea (Bukhari). Repeat this 3 times 🤍",
        "tags": "#dhikr #subhanallah #tasbih #islam #sunnah",
    },
    "astaghfirullah": {
        "title": "33× Astaghfirullah",
        "steps": [("astaghfirullah", 33)],
        "hook": "The Prophet ﷺ sought forgiveness more than 70 times a day. Repeat this 3 times for 100 🤍",
        "tags": "#astaghfirullah #istighfar #dhikr #tasbih #islam",
    },
    "tahlil": {
        "title": "33× La ilaha illallah",
        "steps": [("tahlil", 33)],
        "hook": "The best dhikr is La ilaha illallah (Tirmidhi). Count down with me 🤍",
        "tags": "#dhikr #tawheed #tasbih #islam #reminder",
    },
    "salawat": {
        "title": "33× Salawat upon the Prophet ﷺ",
        "steps": [("salawat", 33)],
        "hook": "Send one salawat and Allah sends ten blessings upon you (Muslim). Here are 33 🤍",
        "tags": "#salawat #durood #dhikr #prophetmuhammad #islam",
    },
}

THEMES = [
    ((20, 56, 46), (5, 15, 13), (214, 178, 106)),
    ((22, 34, 62), (5, 8, 18), (205, 180, 125)),
    ((48, 30, 22), (12, 7, 5), (222, 186, 120)),
]

CREAM = (240, 232, 214)
RING_C = (540, 1130)
RING_R = 300
BEADS = 33
BEAD_R = 24

# "kaaba" (default): night sky, light rays and the Kaaba with moving tawaf lights; the bead ring sits higher.
# "classic": the first design (plain gradient, big ring with tassel).
STYLES = {
    "kaaba": {"ring": (540, 905), "r": 225, "bead": 17, "tassel": False, "num": 140, "handle_y": 1860,
              "theme": ((14, 40, 70), (8, 14, 38), (232, 198, 128))},
    "classic": {"ring": RING_C, "r": RING_R, "bead": BEAD_R, "tassel": True, "num": 150, "handle_y": 1720, "theme": None},
}


def font(name, size):
    return ImageFont.truetype(str(FONTS / name), size)


def ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


# ---------- static layers ----------
def background(theme):
    c1, c2, acc = theme
    small = Image.new("RGB", (W // 4, H // 4))
    px = small.load()
    cx, cy = small.width / 2, RING_C[1] / 4
    for y in range(small.height):
        for x in range(small.width):
            t = min(1.0, math.hypot(x - cx, (y - cy) * 0.75) / (small.width * 0.9)) ** 1.3
            px[x, y] = tuple(int(c1[i] * (1 - t) + c2[i] * t) for i in range(3))
    img = small.resize((W, H), Image.BICUBIC).convert("RGBA")
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gx, gy = RING_C
    ImageDraw.Draw(glow).ellipse((gx - 380, gy - 380, gx + 380, gy + 380), fill=acc + (26,))
    img = Image.alpha_composite(img, glow.filter(ImageFilter.GaussianBlur(140)))
    d = ImageDraw.Draw(img)
    d.text((W / 2, 1720), HANDLE, font=font("Lora-var.ttf", 32), fill=CREAM + (150,), anchor="mm")
    return img


def phrase_layer(key, theme):
    ar, tr, en = PHRASES[key]
    acc = theme[2]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    size = 120
    while size > 60:
        f = font("Amiri-Bold.ttf", size)
        if d.textlength(ar, font=f, direction="rtl", language="ar") <= W - 140:
            break
        size -= 6
    d.text((W / 2, 400), ar, font=f, fill=acc + (255,), anchor="mm", direction="rtl", language="ar")
    d.text((W / 2, 545), tr, font=font("Lora-var.ttf", 44), fill=CREAM + (240,), anchor="mm")
    # Lora has no ﷺ glyph (it would show an empty box): draw that sign in Amiri, right after the text
    fe, fs = font("Lora-var.ttf", 34), font("Amiri-Regular.ttf", 58)
    txt, saw = (en.replace("ﷺ", "").rstrip(), True) if "ﷺ" in en else (en, False)
    wt = d.textlength(txt, font=fe)
    ws = 12 + d.textlength("ﷺ", font=fs) if saw else 0
    x0 = W / 2 - (wt + ws) / 2
    d.text((x0, 605), txt, font=fe, fill=CREAM + (170,), anchor="lm")
    if saw:
        d.text((x0 + wt + 12, 600), "ﷺ", font=fs, fill=CREAM + (170,), anchor="lm")
    sh = img.filter(ImageFilter.GaussianBlur(6))
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    base.putalpha(sh.getchannel("A").point(lambda v: int(v * 0.55)))
    return Image.alpha_composite(base, img)


def end_layer(theme):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((W / 2, 400), "تَقَبَّلَ ٱللَّهُ مِنَّا وَمِنكُم", font=font("Amiri-Bold.ttf", 96), fill=theme[2] + (255,),
           anchor="mm", direction="rtl", language="ar")
    d.text((W / 2, 545), "May Allah accept from us and you", font=font("Lora-var.ttf", 40), fill=CREAM + (235,), anchor="mm")
    d.text((W / 2, 605), "Share it so others earn the reward too 🤍".replace(" 🤍", ""), font=font("Lora-var.ttf", 34),
           fill=CREAM + (170,), anchor="mm")
    return img


# ---------- per-frame drawing ----------
def draw_ring(d, theme, done_in_cycle, rot, pulse, geo=None):
    geo = geo or STYLES["classic"]
    acc = theme[2]
    cx, cy = geo["ring"]
    R, BR = geo["r"], geo["bead"]
    # thread
    d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=acc + (70,), width=2)
    if not geo["tassel"]:  # soft halo ring around the beads
        d.ellipse((cx - R - 42, cy - R - 42, cx + R + 42, cy + R + 42), outline=(255, 255, 255, 28), width=2)
    for i in range(BEADS):
        ang = -math.pi / 2 + (i - rot) * 2 * math.pi / BEADS
        x, y = cx + R * math.cos(ang), cy + R * math.sin(ang)
        counted = i < done_in_cycle
        r = BR
        if i == done_in_cycle - 1:
            r = BR * (1 + 0.35 * pulse)
        if counted:
            fill, line = acc + (255,), (255, 236, 190, 255)
        elif not geo["tassel"]:
            fill, line = (30, 40, 62, 230), (160, 172, 200, 150)
        else:
            fill, line = (60, 70, 66, 200), acc + (90,)
        d.ellipse((x - r, y - r, x + r, y + r), fill=fill, outline=line, width=2)
        # tiny highlight for a glassy bead look
        d.ellipse((x - r * 0.45, y - r * 0.55, x - r * 0.05, y - r * 0.15), fill=(255, 255, 255, 70 if counted else 30))
    if not geo["tassel"]:
        return
    # imam bead + tassel at the bottom
    bx, by = cx, cy + R + 52
    d.ellipse((bx - 30, by - 30, bx + 30, by + 30), fill=acc + (255,), outline=(255, 236, 190, 255), width=2)
    for k in range(-3, 4):
        d.line((bx + k * 4, by + 30, bx + k * 9, by + 110), fill=acc + (200,), width=3)


def render(set_key, theme_idx=None, seed=None, progress=None, style="kaaba"):
    rnd = random.Random(seed)
    spec = SETS[set_key]
    geo = STYLES[style]
    theme = geo["theme"] or (THEMES[theme_idx] if theme_idx is not None else rnd.choice(THEMES))
    if style == "kaaba":
        bg = scenes.kaaba_night()
        ImageDraw.Draw(bg).text((W / 2, geo["handle_y"]), HANDLE, font=font("Lora-var.ttf", 30), fill=CREAM + (160,), anchor="mm")
        kaaba = scenes.shadowed(Image.new("RGBA", (W, H), (0, 0, 0, 0)), scenes.kaaba_layer(*scenes.KAABA_BASE), 18, 0.8)
        tawaf = scenes.tawaf_points()
    else:
        bg = background(theme)
    layers = {k: phrase_layer(k, theme) for k, _ in spec["steps"]}
    end = end_layer(theme)

    # timeline of counts: (time, step_index, count_in_step). The gaps vary a little like a real hand,
    # then get scaled so the Reel is exactly TOTAL seconds.
    n_all = sum(n for _, n in spec["steps"])
    gaps = [1 + rnd.uniform(-0.05, 0.05) for _ in range(n_all)]
    scale = (TOTAL - INTRO - OUTRO) / sum(gaps)
    step = scale  # average seconds per count
    events, t, k = [], INTRO, 0
    for si, (_, n) in enumerate(spec["steps"]):
        for c in range(1, n + 1):
            events.append((t, si, c))
            t += gaps[k] * scale
            k += 1
    total = TOTAL
    nframes = int(total * FPS)

    OUT.mkdir(exist_ok=True)
    wav = OUT / f".tasbih_{set_key}.wav"
    make_audio(events, total, wav)
    mp4 = OUT / f"tasbih_{set_key}.mp4"
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
         "-r", str(FPS), "-i", "-", "-i", str(wav), "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(mp4)],
        stdin=subprocess.PIPE,
    )

    cnt_font_cache = {}
    ei = -1
    for fi in range(nframes):
        tt = fi / FPS
        if progress and fi % 30 == 0:
            progress(fi / nframes)
        while ei + 1 < len(events) and events[ei + 1][0] <= tt:
            ei += 1
        if ei >= 0:
            et, si, c = events[ei]
            since = tt - et
        else:
            si, c, since = 0, 0, 1.0
        key, n = spec["steps"][si]
        finished = ei == len(events) - 1 and since > step

        frame = bg.copy()
        if style == "kaaba":
            scenes.draw_tawaf(ImageDraw.Draw(frame), tawaf, tt, behind=True)
            frame.alpha_composite(kaaba)
            scenes.draw_tawaf(ImageDraw.Draw(frame), tawaf, tt, behind=False)
        # phrase (crossfade when the step changes, end card at the end)
        if finished:
            a = ease((since - step) / 0.6)
            frame = Image.alpha_composite(frame, fade(layers[key], 1 - a))
            frame = Image.alpha_composite(frame, fade(end, a))
        else:
            a = 1.0  # phrase visible from frame 0 (default Instagram cover)
            if c == 1 and si > 0 and since < 0.4:
                prev = spec["steps"][si - 1][0]
                b = ease(since / 0.4)
                frame = Image.alpha_composite(frame, fade(layers[prev], 1 - b))
                frame = Image.alpha_composite(frame, fade(layers[key], b))
            else:
                frame = Image.alpha_composite(frame, fade(layers[key], a))

        d = ImageDraw.Draw(frame)
        pulse = max(0.0, 1 - since / 0.3) if ei >= 0 else 0
        slide = ease(since / 0.25) if ei >= 0 else 1
        done = ((c - 1) % BEADS) + 1 if c else 0
        if finished or (c == n and since > step * 0.5):
            done = BEADS
        # newest bead slides into the top position, like pulling a real misbaha
        rot = (((c - 1) % BEADS)) + (slide - 1) if c else 0
        draw_ring(d, theme, done, rot=rot, pulse=pulse, geo=geo)

        # countdown in the middle of the ring: 33 before the first bead, 0 after the last
        left = n - c
        size = int(geo["num"] * (1 + 0.12 * pulse))
        f = cnt_font_cache.setdefault(size, font("Lora-var.ttf", size))
        rcx, rcy = geo["ring"]
        if finished:
            cx, cy = rcx, rcy - 20
            d.line([(cx - 55, cy), (cx - 15, cy + 42), (cx + 60, cy - 48)], fill=theme[2] + (255,), width=18, joint="curve")
            d.text((rcx, rcy + 95), "done", font=font("Lora-var.ttf", 40), fill=CREAM + (220,), anchor="mm")
        else:
            d.text((rcx, rcy - 25), str(left), font=f, fill=CREAM + (255,), anchor="mm")
            d.text((rcx, rcy + 80), f"left of {n}", font=font("Lora-var.ttf", 34), fill=theme[2] + (220,), anchor="mm")

        ff.stdin.write(frame.convert("RGB").tobytes())
    ff.stdin.close()
    ff.wait()
    wav.unlink()

    (OUT / f"tasbih_{set_key}.txt").write_text(
        f"{spec['hook']}\n\n{spec['title']}. Count along with the beads and send it to someone you love.\n\n"
        f"Comment \"الحمد لله\" when you finish 🤍\n\n{spec['tags']}\n"
    )
    print(f"{mp4}  ({total:.1f}s)")
    return {
        "kind": "tasbih", "file": str(mp4), "caption": (OUT / f"tasbih_{set_key}.txt").read_text().strip(),
        "duration": round(total, 1), "set": set_key, "title": spec["title"],
    }


_fade_cache = {}


def fade(layer, a):
    if a >= 0.999:
        return layer
    if a <= 0.001:
        return Image.new("RGBA", layer.size, (0, 0, 0, 0))
    q = round(a * 20) / 20
    k = (id(layer), q)
    if k not in _fade_cache:
        l2 = layer.copy()
        l2.putalpha(layer.getchannel("A").point(lambda v: int(v * q)))
        _fade_cache[k] = l2
    return _fade_cache[k]


# ---------- audio ----------
def bead_click(rng, strong=False):
    n = int(0.09 * SR)
    t = np.arange(n) / SR
    tone = sum(np.sin(2 * np.pi * f * t + rng.random() * 6) * a for f, a in ((1650, 0.5), (2900, 0.3), (4300, 0.15)))
    noise = rng.normal(0, 0.35, n) * np.exp(-t * 300)
    env = np.exp(-t * (70 if not strong else 40))
    s = (tone * env + noise) * (0.55 if not strong else 0.8)
    if strong:
        s += 0.4 * np.sin(2 * np.pi * 520 * t) * np.exp(-t * 18)
    return s


def make_audio(events, total, path):
    rng = np.random.default_rng(7)
    buf = np.zeros(int(total * SR) + SR)
    buf += rng.normal(0, 0.004, buf.size)  # faint room tone so it never feels "dead"
    for i, (t, si, c) in enumerate(events):
        nxt = events[i + 1] if i + 1 < len(events) else None
        strong = nxt is None or nxt[1] != si or c % 33 == 0
        s = bead_click(rng, strong) * rng.uniform(0.85, 1.0)
        a = int(t * SR)
        buf[a:a + s.size] += s
    buf = np.clip(buf / max(1e-6, np.abs(buf).max()) * 0.7, -1, 1)
    data = (buf * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", choices=list(SETS))
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--seed", type=int)
    args = ap.parse_args()
    if args.list:
        for k, v in SETS.items():
            print(f"{k:16} {v['title']}")
        raise SystemExit
    render(args.set or random.Random(args.seed).choice(list(SETS)), seed=args.seed)
