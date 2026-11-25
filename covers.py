"""Reel covers for the Instagram profile grid.

The grid shows each reel cropped to the middle (3:4 now, 1:1 on older apps), so the title must sit in the centre.
A cover is a frame of the reel, softly blurred and darkened, with one centred title block in the same layout for
every reel of a type. It is uploaded with the reel (cover_url) instead of Instagram's first-frame cover.
"""
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

import make_reel as mr

W, H = 1080, 1920
GOLD, CREAM = (232, 198, 128), (246, 238, 220)
# the part every grid shows: centre square (old 1:1 grid) ⊂ centre 3:4 (current grid)
SAFE_TOP, SAFE_BOTTOM = 420 + 40, 1500 - 40


def frame_at(video, t, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1", str(out)],
                   check=True)
    return Image.open(out).convert("RGB")


def _fit(d, text, name, size, max_w, rtl=False, min_size=34):
    kw = dict(direction="rtl", language="ar") if rtl else {}
    while size > min_size and d.textlength(text, font=mr.font(name, size), **kw) > max_w:
        size -= 4
    return mr.font(name, size), size


def make_cover(background, label, title_ar, title_en, sub, out, light=False):
    """background: a 1080x1920 PIL image (a frame of the reel). light: dark text on a light picture (Asma)."""
    bg = background.resize((W, H)).filter(ImageFilter.GaussianBlur(32))
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shade)
    for y in range(H):  # darker (or lighter) towards the middle band where the title is
        mid = 1 - min(1, abs(y - (SAFE_TOP + SAFE_BOTTOM) / 2) / 900)
        a = int(70 + 110 * mid)
        sd.line([(0, y), (W, y)], fill=((250, 244, 230) if light else (4, 8, 12)) + (a,))
    img = Image.alpha_composite(bg.convert("RGBA"), shade)
    ink = (70, 48, 24) if light else CREAM
    gold = (168, 126, 52) if light else GOLD
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cy = (SAFE_TOP + SAFE_BOTTOM) / 2
    # frame lines around the title block
    d.line((140, cy - 300, W - 140, cy - 300), fill=gold + (200,), width=3)
    d.line((140, cy + 300, W - 140, cy + 300), fill=gold + (200,), width=3)
    for x in (140, W - 140):
        for y in (cy - 300, cy + 300):
            d.polygon([(x, y - 10), (x + 10, y), (x, y + 10), (x - 10, y)], fill=gold + (255,))
    f, _ = _fit(d, label.upper(), "Lora-var.ttf", 34, W - 300)
    d.text((W / 2, cy - 255), label.upper(), font=f, fill=gold + (255,), anchor="mm")
    fa, sa = _fit(d, title_ar, "Amiri-Bold.ttf", 128, W - 260, rtl=True, min_size=76)
    d.text((W / 2, cy - 55), title_ar, font=fa, fill=gold + (255,), anchor="mm", direction="rtl", language="ar")
    fe, _ = _fit(d, title_en, "Lora-var.ttf", 64, W - 240, min_size=40)
    d.text((W / 2, cy + 90), title_en, font=fe, fill=ink + (255,), anchor="mm")
    if sub:
        fs, _ = _fit(d, sub, "Lora-var.ttf", 40, W - 260, min_size=28)
        d.text((W / 2, cy + 175), sub, font=fs, fill=ink + (220,), anchor="mm")
    d.text((W / 2, cy + 250), mr.HANDLE, font=mr.font("Lora-var.ttf", 30), fill=ink + (170,), anchor="mm")
    sh = lay.filter(ImageFilter.GaussianBlur(8))
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    shadow.putalpha(sh.getchannel("A").point(lambda v: int(v * (0.25 if light else 0.6))))
    img = Image.alpha_composite(Image.alpha_composite(img, shadow), lay)
    img.convert("RGB").save(out, quality=92)
    return out


def cover_text(item):
    """(label, Arabic title, English title, sub line, light) for a queue item, by kind."""
    kind = item["kind"]
    if kind == "ayah":
        s, a = item.get("passage") or [None, None]
        ar = "سورة " + mr.chapters()[s]["name_arabic"] if s else ""
        return ("Quran recitation", ar, f"Surah {item.get('surah', '')}", f"{item.get('ref', '')} · {item.get('reciter', '')}", False)
    if kind == "dua":
        import make_dua
        spec = make_dua.CATEGORIES.get(item.get("category"), {})
        first = item.get("title", "").split(" · ", 1)[-1].rstrip("…")
        return (spec.get("label", "Dua"), spec.get("ar", "دعاء"), spec.get("en", "Dua"), first, False)
    if kind == "asma":
        import make_asma
        n = next((x for x in make_asma.catalog() if x["number"] == item.get("number")), None)
        if n:
            return (f"The 99 Names of Allah · {n['number']} / 99", n["ar"], n["translit"].title(), n["meaning"], True)
        return ("The 99 Names of Allah", "أسماء الله الحسنى", "Asma al-Husna", "", True)
    if kind == "tasbih":
        import make_tasbih
        key = make_tasbih.SETS.get(item.get("set"), {}).get("steps", [[item.get("set")]])[0][0]
        ar, tr, en = make_tasbih.PHRASES.get(key, ("سُبْحَانَ ٱللَّهِ", "SubhanAllah", "Glory be to Allah"))
        return ("Tasbih · 33 times", ar, tr, en.replace("ﷺ", "").strip(), False)
    if kind == "quiz":
        return (f"Quran quiz · {str(item.get('level', 'easy')).title()}", "خمّن السورة", "Guess the Surah",
                "5 questions · comment your score", False)
    if kind == "story":
        return (item.get("cover_label", "Stories of the Prophets"), item.get("cover_ar", "قصص الأنبياء"),
                item.get("cover_en", "Stories of the Prophets"), item.get("cover_sub", ""), False)
    return ("", "", item.get("title", ""), "", False)


def cover_for(item, video, out, work=None):
    """Make the grid cover of a reel from a frame of its own video."""
    work = Path(work or out).with_suffix(".frame.png")
    t = 1.0 if item["kind"] == "quiz" else 1.5
    bg = frame_at(video, t, work)
    label, ar, en, sub, light = cover_text(item)
    make_cover(bg, label, ar, en, sub, out, light)
    work.unlink(missing_ok=True)
    return out
