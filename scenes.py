"""Drawn scenes shared by the reel makers: night sky with the Kaaba (tasbih), pointed arches (dua), helpers.

Everything is drawn with PIL (no photos), so the look is ours and there is nothing to license.
"""
import math
import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 1080, 1920
GOLD = (222, 188, 120)
GOLD_L = (245, 216, 150)
CREAM = (246, 238, 220)


def gradient(stops, w=W, h=H):
    """Vertical gradient from [(pos 0-1, (r, g, b)), ...]."""
    ys = np.linspace(0, 1, h)[:, None]
    out = np.zeros((h, 1, 3))
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        m = (ys >= p0) & (ys <= p1)
        t = np.clip((ys - p0) / max(1e-6, p1 - p0), 0, 1)
        for i in range(3):
            out[..., i] = np.where(m, c0[i] * (1 - t) + c1[i] * t, out[..., i])
    return Image.fromarray(np.repeat(out, w, axis=1).astype(np.uint8)).convert("RGBA")


def glow(img, box, color, alpha, blur):
    g = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(g).ellipse(box, fill=color + (alpha,))
    return Image.alpha_composite(img, g.filter(ImageFilter.GaussianBlur(blur)))


def stars(img, n, top, bottom, seed=3):
    rnd = random.Random(seed)
    s = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(s)
    for _ in range(n):
        x, y, r = rnd.uniform(0, img.width), rnd.uniform(top, bottom), rnd.choice([1, 1, 1.5, 2, 2.5])
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, rnd.randint(60, 200)))
    return Image.alpha_composite(img, s)


def rays(img, origin, color, n=9, spread=70, length=1500, alpha=26):
    r = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(r)
    ox, oy = origin
    for k in range(n):
        a = math.radians(-90 - spread / 2 + spread * k / (n - 1))
        w = math.radians(2.2)
        d.polygon([origin, (ox + length * math.cos(a - w), oy + length * math.sin(a - w)),
                   (ox + length * math.cos(a + w), oy + length * math.sin(a + w))], fill=color + (alpha,))
    return Image.alpha_composite(img, r.filter(ImageFilter.GaussianBlur(14)))


def shadowed(base, layer, blur=8, alpha=0.7):
    sh = layer.filter(ImageFilter.GaussianBlur(blur))
    a = sh.getchannel("A").point(lambda v: int(v * alpha))
    black = Image.new("RGBA", base.size, (0, 0, 0, 0))
    black.putalpha(a)
    return Image.alpha_composite(Image.alpha_composite(base, black), layer)


def divider(d, cx, y, w=150, color=GOLD):
    d.line((cx - w, y, cx - 14, y), fill=color + (170,), width=2)
    d.line((cx + 14, y, cx + w, y), fill=color + (170,), width=2)
    d.polygon([(cx, y - 8), (cx + 8, y), (cx, y + 8), (cx - 8, y)], fill=color + (230,))


# ---------- Kaaba at night (tasbih) ----------
KAABA_BASE = (W / 2 + 30, 1680)


def kaaba_layer(cx, base_y, w=340):
    """The Kaaba seen slightly from the side: front + side face, gold hizam band and door."""
    k = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(k)
    h = w
    side = int(w * 0.42)
    fx0, fx1 = cx - w * 0.62, cx + w * 0.38
    top, depth = base_y - h, 34
    d.polygon([(fx1, top), (fx1 + side, top - depth), (fx1 + side, base_y - depth), (fx1, base_y)], fill=(14, 14, 16, 255))
    d.polygon([(fx0, top), (fx1, top), (fx1, base_y), (fx0, base_y)], fill=(22, 22, 25, 255))
    d.polygon([(fx0, top), (fx1, top), (fx1 + side, top - depth), (fx0 + side, top - depth)], fill=(34, 34, 38, 255))
    by, bh = top + h * 0.2, h * 0.09
    d.rectangle((fx0, by, fx1, by + bh), fill=GOLD + (255,))
    d.polygon([(fx1, by), (fx1 + side, by - depth), (fx1 + side, by + bh - depth), (fx1, by + bh)], fill=(176, 146, 88, 255))
    for x in np.arange(fx0 + 14, fx1 - 10, 22):  # a hint of calligraphy in the band
        d.line((x, by + bh * 0.3, x + 10, by + bh * 0.3), fill=(120, 92, 40, 255), width=3)
        d.line((x + 4, by + bh * 0.65, x + 14, by + bh * 0.65), fill=(120, 92, 40, 255), width=3)
    dx0, dx1 = fx1 - w * 0.32, fx1 - w * 0.12
    d.rectangle((dx0, base_y - h * 0.62, dx1, base_y - h * 0.08), fill=GOLD + (255,))
    d.rectangle((dx0 + 6, base_y - h * 0.6, dx1 - 6, base_y - h * 0.1), outline=(150, 118, 60, 255), width=3)
    d.line((fx0, top, fx0, base_y), fill=(90, 90, 100, 255), width=3)
    return k


def kaaba_night(handle=None):
    """Static parts of the tasbih scene: sky, stars, light rays, glow and the Kaaba (tawaf lights are per frame)."""
    cx, base_y = KAABA_BASE
    img = gradient([(0, (8, 14, 38)), (0.55, (14, 40, 70)), (0.85, (34, 74, 86)), (1, (20, 40, 46))])
    img = stars(img, 170, 0, 1150)
    img = rays(img, (W / 2, base_y - 30), (255, 226, 170), n=11, spread=80, alpha=22)
    img = glow(img, (cx - 420, base_y - 260, cx + 420, base_y + 150), (255, 214, 140), 70, 90)
    return img


def tawaf_points(n=260, seed=7):
    """People of the tawaf as small lights on an ellipse around the Kaaba: (radius x, radius y, angle, size, alpha)."""
    rnd = random.Random(seed)
    return [(rnd.uniform(330, 470), rnd.uniform(70, 110), rnd.uniform(0, 2 * math.pi), rnd.choice([1.5, 2, 2.5]),
             rnd.randint(70, 190)) for _ in range(n)]


def draw_tawaf(d, pts, t, behind):
    """Lights move anticlockwise (as seen from above) ~ one lap a minute; `behind` draws only the far half."""
    cx, base_y = KAABA_BASE
    for rx, ry, a0, r, al in pts:
        a = a0 - t * 2 * math.pi / 60 * (380 / rx)
        y = base_y + 10 + ry * math.sin(a)
        if (math.sin(a) < 0) != behind:
            continue
        x = cx + rx * math.cos(a)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 236, 200, al))


# ---------- pointed arch (dua) ----------
def arch_points(x0, x1, spring, k=0.78, n=48):
    """Pointed Islamic arch from (x0, spring) up to the apex and down to (x1, spring): two circle arcs."""
    w = x1 - x0
    r = k * w
    cl = x0 + r
    a_end = math.degrees(math.acos((x0 + w / 2 - cl) / r))
    left = [(cl + r * math.cos(math.radians(a)), spring - r * math.sin(math.radians(a))) for a in np.linspace(180, a_end, n)]
    right = [(x0 + x1 - x, y) for x, y in reversed(left)]
    return left + right[1:]


def arch_height(w, k=0.78):
    r = k * w
    return r * math.sin(math.acos((w / 2 - r) / r))
