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

HERE = Path(__file__).parent
FONTS = HERE / "fonts"
OUT = HERE / "reels"
HANDLE = "@tilawah.sakina"
W, H, FPS = 1080, 1920, 30
STEP = 1.2           # seconds per count: a calm, real-hand pace (each bead varies a little)
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

SETS = {
    "after_salah": {
        "title": "Tasbih after Salah",
        "steps": [("subhanallah", 33), ("alhamdulillah", 33), ("allahuakbar", 34)],
        "hook": "33 · 33 · 34. Take two minutes after your salah 🤍",
        "tags": "#tasbih #dhikr #aftersalah #subhanallah #islam",
    },
    "wabihamdihi": {
        "title": "100× SubhanAllahi wa bihamdihi",
        "steps": [("wabihamdihi", 100)],
        "hook": "Say it 100 times and your sins are wiped away, even if they are like the foam of the sea (Bukhari) 🤍",
        "tags": "#dhikr #subhanallah #tasbih #islam #sunnah",
    },
    "astaghfirullah": {
        "title": "100× Astaghfirullah",
        "steps": [("astaghfirullah", 100)],
        "hook": "The Prophet ﷺ sought forgiveness more than 70 times a day. Join him for two minutes 🤍",
        "tags": "#astaghfirullah #istighfar #dhikr #tasbih #islam",
    },
    "tahlil": {
        "title": "100× La ilaha illallah",
        "steps": [("tahlil", 100)],
        "hook": "The best dhikr is La ilaha illallah (Tirmidhi). Count with me 🤍",
        "tags": "#dhikr #tawheed #tasbih #islam #reminder",
    },
    "salawat": {
        "title": "100× Salawat upon the Prophet ﷺ",
        "steps": [("salawat", 100)],
        "hook": "Send one salawat and Allah sends ten blessings upon you (Muslim). What about 100? 🤍",
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
    d.text((W / 2, 605), en, font=font("Lora-var.ttf", 34), fill=CREAM + (170,), anchor="mm")
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
def draw_ring(d, theme, done_in_cycle, rot, pulse):
    acc = theme[2]
    cx, cy = RING_C
    # thread
    d.ellipse((cx - RING_R, cy - RING_R, cx + RING_R, cy + RING_R), outline=acc + (70,), width=2)
    for i in range(BEADS):
        ang = -math.pi / 2 + (i - rot) * 2 * math.pi / BEADS
        x, y = cx + RING_R * math.cos(ang), cy + RING_R * math.sin(ang)
        counted = i < done_in_cycle
        r = BEAD_R
        if i == done_in_cycle - 1:
            r = BEAD_R * (1 + 0.35 * pulse)
        if counted:
            fill, line = acc + (255,), (255, 236, 190, 255)
        else:
            fill, line = (60, 70, 66, 200), acc + (90,)
        d.ellipse((x - r, y - r, x + r, y + r), fill=fill, outline=line, width=2)
        # tiny highlight for a glassy bead look
        d.ellipse((x - r * 0.45, y - r * 0.55, x - r * 0.05, y - r * 0.15), fill=(255, 255, 255, 70 if counted else 30))
    # imam bead + tassel at the bottom
    bx, by = cx, cy + RING_R + 52
    d.ellipse((bx - 30, by - 30, bx + 30, by + 30), fill=acc + (255,), outline=(255, 236, 190, 255), width=2)
    for k in range(-3, 4):
        d.line((bx + k * 4, by + 30, bx + k * 9, by + 110), fill=acc + (200,), width=3)


def render(set_key, theme_idx=None, seed=None):
    rnd = random.Random(seed)
    spec = SETS[set_key]
    theme = THEMES[theme_idx] if theme_idx is not None else rnd.choice(THEMES)
    bg = background(theme)
    layers = {k: phrase_layer(k, theme) for k, _ in spec["steps"]}
    end = end_layer(theme)

    # timeline of counts: (time, step_index, count_in_step)
    events, t = [], INTRO
    for si, (_, n) in enumerate(spec["steps"]):
        for c in range(1, n + 1):
            events.append((t, si, c))
            t += STEP + rnd.uniform(-0.08, 0.08)
        t += 0.5 if si < len(spec["steps"]) - 1 else 0
    total = t + OUTRO
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
        while ei + 1 < len(events) and events[ei + 1][0] <= tt:
            ei += 1
        if ei >= 0:
            et, si, c = events[ei]
            since = tt - et
        else:
            si, c, since = 0, 0, 1.0
        key, n = spec["steps"][si]
        finished = ei == len(events) - 1 and since > STEP

        frame = bg.copy()
        # phrase (crossfade when the step changes, end card at the end)
        if finished:
            a = ease((since - STEP) / 0.6)
            frame = Image.alpha_composite(frame, fade(layers[key], 1 - a))
            frame = Image.alpha_composite(frame, fade(end, a))
        else:
            a = ease(tt / 0.5) if ei < 0 else 1.0
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
        if finished or (c == n and since > STEP * 0.5):
            done = BEADS
        # newest bead slides into the top position, like pulling a real misbaha
        rot = (((c - 1) % BEADS)) + (slide - 1) if c else 0
        draw_ring(d, theme, done, rot=rot, pulse=pulse)

        # counter in the middle of the ring
        size = int(150 * (1 + 0.12 * pulse))
        f = cnt_font_cache.setdefault(size, font("Lora-var.ttf", size))
        d.text((RING_C[0], RING_C[1] - 25), str(c), font=f, fill=CREAM + (255,), anchor="mm")
        d.text((RING_C[0], RING_C[1] + 85), f"/ {n}", font=font("Lora-var.ttf", 40), fill=theme[2] + (220,), anchor="mm")
        if len(spec["steps"]) > 1:
            k = len(spec["steps"])
            for i in range(k):
                x = RING_C[0] + (i - (k - 1) / 2) * 36
                y = RING_C[1] + 140
                on = i <= si
                d.ellipse((x - 8, y - 8, x + 8, y + 8), fill=theme[2] + (230,) if on else None,
                          outline=theme[2] + (200,), width=2)
        elif n > BEADS:
            d.text((RING_C[0], RING_C[1] + 140), f"round {min((c - 1) // BEADS + 1, math.ceil(n / BEADS)) if c else 1}",
                   font=font("Lora-var.ttf", 28), fill=theme[2] + (170,), anchor="mm")

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
