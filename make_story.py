"""Stories of the Prophets: the story as Allah tells it in the Quran, one scene per ayah.

Every ayah is recited (with Arabic + English on screen) over a real nature clip that matches what it says
(Pixabay, film only). The prophets, angels and people are NEVER shown: scenes are places, sky, sea, light.

Usage (needs PIXABAY_API_KEY):
  python3 make_story.py adam
"""
import argparse
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

import make_reel as mr
import nature

W, H = mr.W, mr.H
RECITER = "Mishary Alafasy"
# Extra tags never wanted in a prophet story (on top of nature.NO): no depictions, no myths that are not in the Quran.
STORY_NO = {"angel", "angels", "god", "jesus", "bible", "adam", "eve", "snake", "serpent", "apple", "devil", "demon",
            "religion", "christian", "cross", "heaven art", "painting", "illustration", "cartoon", "sculpture", "nude"}

# prophet -> (number in the series, Arabic name, English name, [(surah, ayah, scene search)])
STORIES = {
    "adam": (1, "آدم", "Adam", [
        (2, 30, "earth from space"),
        (2, 31, "galaxy stars"),
        (2, 32, "starry sky"),
        (2, 33, "nebula space"),
        (2, 34, "sun rays clouds"),
        (2, 35, "garden flowers"),
        (2, 36, "falling leaves"),
        (2, 37, "sunrise"),
    ]),
}
TOTAL_PROPHETS = 25


def scene_clip(query, seconds, rnd, out):
    """A clip (or a few joined) for one ayah, cropped to 9:16, darkened, exactly `seconds` long."""
    old = set(nature.NO)
    nature.NO |= STORY_NO
    try:
        hits = nature.search(query)
    finally:
        nature.NO = old
    rnd.shuffle(hits)
    clips, covered = [], 0.0
    for h in hits:
        try:
            path = nature.clip_file(h)
            real = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                  "-of", "csv=p=0", str(path)]).strip())
        except Exception:  # noqa: BLE001
            continue
        if real < 5:
            continue
        clips.append((path, real * nature.SLOW, h["id"]))
        covered += real * nature.SLOW - (nature.FADE if len(clips) > 1 else 0)
        if covered >= seconds + 0.5:
            break
    if not clips:
        raise RuntimeError(f"no clip for {query!r}")
    nature.render_background(clips, seconds, out)
    return out


def frame_png(no, ar, en, path):
    """Header (series + prophet) and footer (reciter, handle) over the whole story."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    gold = (232, 198, 128)
    d.text((W / 2, 190), f"STORIES OF THE PROPHETS · {no} / {TOTAL_PROPHETS}", font=mr.font("Lora-var.ttf", 28),
           fill=gold + (230,), anchor="mm")
    d.text((W / 2, 268), f"قصة {ar} عليه السلام", font=mr.font("Amiri-Bold.ttf", 66), fill=gold + (255,), anchor="mm",
           direction="rtl", language="ar")
    d.text((W / 2, 350), f"The story of {en} (peace be upon him)", font=mr.font("Lora-var.ttf", 34),
           fill=(240, 234, 220, 230), anchor="mm")
    d.text((W / 2, 1720), RECITER, font=mr.font("Lora-var.ttf", 34), fill=gold + (240,), anchor="mm")
    d.text((W / 2, 1772), mr.HANDLE, font=mr.font("Lora-var.ttf", 28), fill=(240, 234, 220, 190), anchor="mm")
    mr.with_shadow(img, path)
    mr.dim_panel(path)


def render(key, seed=None):
    rnd = random.Random(seed)
    no, ar_name, en_name, scenes = STORIES[key]
    chs = mr.chapters()
    folder = mr.RECITERS[RECITER]
    theme = mr.THEMES[0]
    work = mr.CACHE / "work" / f"story_{key}"
    work.mkdir(parents=True, exist_ok=True)
    frame_png(no, ar_name, en_name, work / "frame.png")

    # timeline: one segment per ayah; the ayah card can be split over a few screens if long
    segs, cards, audio, t = [], [], [], 0.0
    lead = 0.6
    for s, a, query in scenes:
        mp3 = mr.audio(folder, s, a)
        dur = mr.duration(mp3) + (lead if not segs else 0) + 0.35
        ar, en = mr.verse(s, a)
        for n in range(1, 6):
            parts, shares = mr.split_parts(ar, en, n) if n > 1 else ([(ar, en)], [1.0])
            paths = [work / f"card_{s}_{a}_{k}.png" for k in range(n)]
            if all(mr.card(theme, chs[s], s, a, pa, pe, RECITER, pp) for (pa, pe), pp in zip(parts, paths)):
                break
        for pp, sh in zip(paths, shares):
            cards.append((pp, dur * sh))
        bg = scene_clip(query, dur, rnd, work / f"bg_{s}_{a}.mp4")
        segs.append((bg, dur))
        audio.append((mp3, dur))
        t += dur
    total = t + 1.5

    # background: the scene clips one after another, each fading in/out softly
    ins, f = [], []
    for i, (p, d_) in enumerate(segs):
        ins += ["-i", str(p)]
        f.append(f"[{i}:v]trim=duration={d_:.3f},setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.35,"
                 f"fade=t=out:st={max(0, d_ - 0.35):.3f}:d=0.35[s{i}]")
    f.append("".join(f"[s{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=0,tpad=stop_mode=clone:stop_duration=2[bg]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(f), "-map", "[bg]",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(work / "bg.mp4")],
                   check=True, timeout=1800)
    # recitation: each ayah starts with its scene
    a_ins, a_f = [], []
    for i, (p, d_) in enumerate(audio):
        a_ins += ["-i", str(p)]
        pre = f"adelay={int(lead * 1000)}:all=1," if i == 0 else ""
        a_f.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,{pre}apad=whole_dur={d_:.3f},atrim=0:{d_:.3f}[a{i}]")
    a_f.append("".join(f"[a{i}]" for i in range(len(audio))) + f"concat=n={len(audio)}:v=0:a=1,apad=whole_dur={total:.2f}[aout]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a_ins, "-filter_complex", ";".join(a_f), "-map", "[aout]",
                    "-t", f"{total:.2f}", "-c:a", "aac", "-b:a", "160k", str(work / "audio.m4a")], check=True, timeout=600)
    with open(work / "cards.txt", "w") as fh:
        for p, d_ in cards:
            fh.write(f"file '{p.resolve()}'\nduration {d_:.3f}\n")
        fh.write(f"file '{cards[-1][0].resolve()}'\n")
    fc = ("[0:v]format=yuv420p,fps=30[b0];[b0][1:v]overlay=0:0:shortest=1[b1];[2:v]format=rgba,fps=30[c];"
          f"[b1][c]overlay=0:0:eof_action=repeat,fade=t=out:st={total - 0.8:.2f}:d=0.8[v]")
    mr.OUT.mkdir(exist_ok=True)
    mp4 = mr.OUT / f"story_{key}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(work / "bg.mp4"), "-loop", "1", "-i", str(work / "frame.png"),
                    "-f", "concat", "-safe", "0", "-i", str(work / "cards.txt"), "-i", str(work / "audio.m4a"),
                    "-filter_complex", fc, "-map", "[v]", "-map", "3:a", "-t", f"{total:.2f}", "-c:v", "libx264",
                    "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "copy",
                    "-movflags", "+faststart", str(mp4)], check=True, timeout=1800)
    first, last = scenes[0][:2], scenes[-1][:2]
    caption = (f"The story of {en_name} (peace be upon him), as Allah tells it in the Quran 🤍\n\n"
               f"Surah {chs[first[0]]['name_simple']} {first[0]}:{first[1]}-{last[1]} · recited by {RECITER}\n\n"
               f"Stories of the Prophets · {no} of {TOTAL_PROPHETS}. Follow for the next prophet tomorrow.\n\n"
               f"#storiesoftheprophets #quran #prophet{en_name.lower()} #islam #qasasalanbiya")
    print(mp4, round(total, 1), "s")
    return {"kind": "story", "file": str(mp4), "caption": caption, "duration": round(total, 1), "prophet": key,
            "title": f"Stories of the Prophets {no}/{TOTAL_PROPHETS} · {en_name}"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("prophet", choices=list(STORIES))
    ap.add_argument("--seed", type=int)
    a = ap.parse_args()
    render(a.prophet, a.seed)
