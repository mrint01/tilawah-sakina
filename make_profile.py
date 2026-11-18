"""Profile picture for the Quran page: 1080x1080, centered so Instagram's circle crop keeps everything."""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
S = 1080
GOLD = (214, 178, 106)

def radial_bg():
    img = Image.new("RGB", (S, S))
    px = img.load()
    c = S / 2
    for y in range(S):
        for x in range(S):
            d = min(1.0, math.hypot(x - c, y - c) / (S * 0.62))
            t = d ** 1.4
            px[x, y] = (int(18 * (1 - t) + 6 * t), int(52 * (1 - t) + 16 * t), int(44 * (1 - t) + 14 * t))
    return img

img = radial_bg()
d = ImageDraw.Draw(img)

# thin double ring
for r, w in ((430, 4), (408, 2)):
    d.ellipse((S / 2 - r, S / 2 - r, S / 2 + r, S / 2 + r), outline=GOLD, width=w)

# soft glow behind the word
glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
ImageDraw.Draw(glow).ellipse((300, 300, 780, 700), fill=(214, 178, 106, 55))
img.paste(glow.filter(ImageFilter.GaussianBlur(90)), (0, 0), glow.filter(ImageFilter.GaussianBlur(90)))

ar = ImageFont.truetype(str(HERE / "fonts/Amiri-Bold.ttf"), 250)
d.text((S / 2, S / 2 - 40), "سكينة", font=ar, fill=GOLD, anchor="mm", direction="rtl", language="ar")

lat = ImageFont.truetype(str(HERE / "fonts/Lora-var.ttf"), 64)
d.text((S / 2, S / 2 + 165), "S A K I N A H", font=lat, fill=(236, 226, 205), anchor="mm")

out = HERE / "profile_picture.png"
img.save(out)
print(out)
