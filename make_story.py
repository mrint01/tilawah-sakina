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
STORY_NO = {"lantern", "lamp", "umbrella", "angel", "angels", "god", "jesus", "bible", "adam", "eve", "snake", "serpent", "apple", "devil", "demon",
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
    "idris": (2, "إدريس", "Idris", [
        (19, 56, "mountain sunrise"),
        (19, 57, "starry sky"),
    ]),
}
TOTAL_PROPHETS = 25

# Narrated stories: an Arabic narrator tells the story (English subtitles) (from the Quran, authentic hadith and Ibn Kathir's
# Qasas al-Anbiya, without weak reports), and at the key moments Mishary Alafasy recites the ayah itself.
# Segments: ("n", narration, scene) or ("a", surah, ayah, scene).
VOICE = "ar-SA-HamedNeural"   # Arabic narrator (fusha); he tells the story, he never reads Quran words
# how many parts each narrated story has in total (the later parts are written after part 1 is approved)
PARTS = {"nuh": 3}
SOURCES = "Quran · Sahih al-Bukhari · Ibn Kathir, Qasas al-Anbiya"
# Segments: ("n", Arabic narration, English subtitle, scene) or ("a", surah, ayah, scene).
NARRATED = {
    "nuh": (3, "نوح", "Nuh", [
        [  # Part 1: the call
            ("n", "بعد آدمَ بزمنٍ طويل، كان في الناس رجالٌ صالحون. فلما ماتوا، وسوس الشيطانُ للناس: اصنعوا لهم تماثيلَ لتتذكروهم.",
             "Long after Adam, there were righteous men among the people. When they died, Shaytan whispered to them: "
             "make statues of them, so you remember them.", "misty valley"),
            ("n", "ومضت الأجيال، ونُسِيَ العلم، فعبد الناسُ تلك التماثيلَ من دون الله.",
             "Generations passed, the knowledge was forgotten, and the people worshipped those statues instead of Allah.",
             "dark storm clouds"),
            ("n", "فأرسل اللهُ إليهم رسولَه نوحًا عليه السلام.",
             "So Allah sent them His messenger: Nuh, peace be upon him.", "sun rays clouds"),
            ("a", 71, 1, "sunrise sky"),
            ("n", "دعا نوحٌ قومَه ليلًا ونهارًا، في العَلَن وفي السر، وبقي فيهم تسعَمئةٍ وخمسين سنة.",
             "Nuh called his people night and day, in public and in secret. He stayed among them for nine hundred and "
             "fifty years.", "starry night sky"),
            ("a", 71, 7, "thunderstorm clouds"),
            ("n", "وقال لهم: اطلبوا المغفرةَ من ربكم، فيُنزلَ عليكم المطر، ويرزقَكم المالَ والأولاد.",
             "He told them: ask your Lord for forgiveness, and He will send you rain, and give you wealth and children.",
             "rain drops leaves"),
            ("a", 71, 10, "rain water drops"),
            ("n", "لكنّ كبراءَ قومِه سخِروا منه، وقالوا: ما أنت إلا رجلٌ مثلُنا، ولا يتبعك إلا الضعفاءُ منا.",
             "But the leaders mocked him. You are only a man like us, they said, and only the weakest among us follow you.",
             "dry desert"),
            ("n", "وما آمن معه إلا قليل، ومع ذلك لم يتوقف نوحٌ عن دعوتهم إلى الله.",
             "Only a few believed. And still, Nuh never stopped calling them to Allah.", "lone tree field"),
            ("n", "في الجزء الثاني: يأمرُ اللهُ نوحًا ببناء السفينة.",
             "In part two: Allah commands Nuh to build the Ark.", "ocean horizon"),
        ],
    ]),
}


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


def frame_png(no, ar, en, path, part=None, footer=None):
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
    if part:
        pill = f"PART {part[0]} OF {part[1]}"
        f = mr.font("Lora-var.ttf", 26)
        tw = d.textlength(pill, font=f)
        d.rounded_rectangle((W / 2 - tw / 2 - 22, 388, W / 2 + tw / 2 + 22, 432), 22, outline=gold + (220,), width=2)
        d.text((W / 2, 410), pill, font=f, fill=gold + (255,), anchor="mm")
    if footer:
        d.text((W / 2, 1668), footer, font=mr.font("Lora-var.ttf", 24), fill=(240, 234, 220, 170), anchor="mm")
    d.text((W / 2, 1720), RECITER if not footer else f"Recitation: {RECITER}", font=mr.font("Lora-var.ttf", 34),
           fill=gold + (240,), anchor="mm")
    d.text((W / 2, 1772), mr.HANDLE, font=mr.font("Lora-var.ttf", 28), fill=(240, 234, 220, 190), anchor="mm")
    mr.with_shadow(img, path)
    mr.dim_panel(path)


def narration(text, out):
    """Arabic narration with a neural voice (edge-tts), slightly slow and calm."""
    if not out.exists():
        subprocess.run(["edge-tts", "--voice", VOICE, "--rate=-8%", "--text", text, "--write-media", str(out)],
                       check=True, timeout=120)
    return out


def narr_card(ar, en, path):
    """The narration in Arabic (large) with the English subtitle under it, in the middle panel."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for size in range(74, 44, -2):
        fa = mr.font("Amiri-Regular.ttf", size)
        la = mr.wrap(d, ar, fa, W - 170, rtl=True)
        lha = int(size * 1.75)
        es = max(30, int(size * 0.5))
        fe = mr.font("Lora-var.ttf", es)
        le = mr.wrap(d, en, fe, W - 190)
        lhe = int(es * 1.45)
        block = len(la) * lha + 56 + len(le) * lhe
        if block <= 960:
            break
    y = 975 - block / 2
    for ln in la:
        d.text((W / 2, y + lha / 2), ln, font=fa, fill=(250, 244, 230, 255), anchor="mm", direction="rtl", language="ar")
        y += lha
    y += 56
    for ln in le:
        d.text((W / 2, y + lhe / 2), ln, font=fe, fill=(225, 218, 200, 230), anchor="mm")
        y += lhe
    mr.with_shadow(img, path)


def compose(segs, cards, audio, frame, total, out):
    """Scene clips one after another (soft fades), the frame and cards over them, the audio under them."""
    work = Path(frame).parent
    ins, f = [], []
    for i, (p, d_) in enumerate(segs):
        ins += ["-i", str(p)]
        f.append(f"[{i}:v]trim=duration={d_:.3f},setpts=PTS-STARTPTS,fade=t=in:st=0:d=0.35,"
                 f"fade=t=out:st={max(0, d_ - 0.35):.3f}:d=0.35[s{i}]")
    f.append("".join(f"[s{i}]" for i in range(len(segs))) + f"concat=n={len(segs)}:v=1:a=0,tpad=stop_mode=clone:stop_duration=2[bg]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(f), "-map", "[bg]",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(work / "bg.mp4")],
                   check=True, timeout=1800)
    a_ins, a_f = [], []
    for i, (p, d_, lead) in enumerate(audio):
        a_ins += ["-i", str(p)]
        a_f.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=stereo,loudnorm=I=-16:TP=-1.5,"
                   f"adelay={int(lead * 1000)}:all=1,apad=whole_dur={d_:.3f},atrim=0:{d_:.3f}[a{i}]")
    a_f.append("".join(f"[a{i}]" for i in range(len(audio))) + f"concat=n={len(audio)}:v=0:a=1,apad=whole_dur={total:.2f}[aout]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a_ins, "-filter_complex", ";".join(a_f), "-map", "[aout]",
                    "-t", f"{total:.2f}", "-c:a", "aac", "-b:a", "160k", str(work / "audio.m4a")], check=True, timeout=600)
    with open(work / "cards.txt", "w") as fh:
        for p, d_ in cards:
            fh.write(f"file '{Path(p).resolve()}'\nduration {d_:.3f}\n")
        fh.write(f"file '{Path(cards[-1][0]).resolve()}'\n")
    fc = ("[0:v]format=yuv420p,fps=30[b0];[b0][1:v]overlay=0:0:shortest=1[b1];[2:v]format=rgba,fps=30[c];"
          f"[b1][c]overlay=0:0:eof_action=repeat,fade=t=out:st={total - 0.8:.2f}:d=0.8[v]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(work / "bg.mp4"), "-loop", "1", "-i", str(frame),
                    "-f", "concat", "-safe", "0", "-i", str(work / "cards.txt"), "-i", str(work / "audio.m4a"),
                    "-filter_complex", fc, "-map", "[v]", "-map", "3:a", "-t", f"{total:.2f}", "-c:v", "libx264",
                    "-preset", "medium", "-crf", "21", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "copy",
                    "-movflags", "+faststart", str(out)], check=True, timeout=1800)


def scene(query, seconds, rnd, out):
    """scene_clip, falling back to calm sky footage when the search finds nothing usable."""
    for q in (query, "clouds sky", "sunset sky"):
        try:
            return scene_clip(q, seconds, rnd, out)
        except RuntimeError as e:
            print("scene:", e)
    raise RuntimeError(f"no scene for {query!r}")


def render_narrated(key, part=1, seed=None):
    rnd = random.Random(seed)
    no, ar_name, en_name, parts = NARRATED[key]
    segs_in = parts[part - 1]
    chs = mr.chapters()
    folder = mr.RECITERS[RECITER]
    theme = mr.THEMES[0]
    work = mr.CACHE / "work" / f"story_{key}_{part}"
    work.mkdir(parents=True, exist_ok=True)
    frame_png(no, ar_name, en_name, work / "frame.png", part=(part, PARTS.get(key, len(parts))), footer=f"Sources: {SOURCES}")
    segs, cards, audio, t = [], [], [], 0.0
    for i, sg in enumerate(segs_in):
        lead = 0.6 if i == 0 else 0.25
        if sg[0] == "n":
            _, text, en, query = sg
            mp3 = narration(text, work / f"n{i}.mp3")
            narr_card(text, en, work / f"card{i}.png")
            cards.append((work / f"card{i}.png", 0))
        else:
            _, su, ay, query = sg
            mp3 = mr.audio(folder, su, ay)
            ar, en = mr.verse(su, ay)
            for n in range(1, 6):
                pieces, shares = mr.split_parts(ar, en, n) if n > 1 else ([(ar, en)], [1.0])
                paths = [work / f"card{i}_{k}.png" for k in range(n)]
                if all(mr.card(theme, chs[su], su, ay, pa, pe, RECITER, pp) for (pa, pe), pp in zip(pieces, paths)):
                    break
        dur = mr.duration(mp3) + lead + 0.45
        if sg[0] == "n":
            cards[-1] = (cards[-1][0], dur)
        else:
            cards += [(pp, dur * sh) for pp, sh in zip(paths, shares)]
        segs.append((scene(query, dur, rnd, work / f"bg{i}.mp4"), dur))
        audio.append((mp3, dur, lead))
        t += dur
    total = t + 1.2
    mr.OUT.mkdir(exist_ok=True)
    mp4 = mr.OUT / f"story_{key}_{part}.mp4"
    compose(segs, cards, audio, work / "frame.png", total, mp4)
    print(mp4, round(total, 1), "s")
    return {"kind": "story", "file": str(mp4), "duration": round(total, 1), "prophet": key, "part": part,
            "title": f"Stories of the Prophets {no}/{TOTAL_PROPHETS} · {en_name} · Part {part} of {PARTS.get(key, len(parts))}"}


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
    ap.add_argument("prophet", choices=list(STORIES) + list(NARRATED))
    ap.add_argument("--part", type=int, default=1)
    ap.add_argument("--seed", type=int)
    a = ap.parse_args()
    if a.prophet in NARRATED:
        render_narrated(a.prophet, a.part, a.seed)
    else:
        render(a.prophet, a.seed)
