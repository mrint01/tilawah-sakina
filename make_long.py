"""One-time long Reels: a whole range of a surah in one video (Surah Al-Kahf in 2 parts for Fridays).

Uses the same look as make_reel.py (background, header, ayah cards) but plays the recording
continuously, with each ayah card shown at its time from the alignment (timings/...).
The regular 60-90 s reels are not affected.

    python3 make_long.py 18 1 50  --part "Part 1 of 2" --out reels/weekly/kahf-part1.mp4
    python3 make_long.py 18 51 110 --part "Part 2 of 2" --out reels/weekly/kahf-part2.mp4
"""
import argparse
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

import make_reel as mr
import nature

FOLDER = "quranicaudio/maher_256"
RECITER = "Maher Al-Muaiqly"


def build(s, first, last, part, out, theme_idx=0):
    chs = mr.chapters()
    ch = chs[s]
    theme = mr.THEMES[theme_idx]
    timing = {t["ayah"]: t for t in mr.aligned_timing(FOLDER, s)}
    whole = mr.CACHE / FOLDER / f"surah_{s:03d}.mp3"
    if not whole.exists():
        mr.fetch(f"{mr.ALIGNED[FOLDER][0]}{s:03d}.mp3", whole)

    # part 1 keeps the isti'adha and basmala before ayah 1
    t0 = 0.0 if first == 1 else timing[first]["start_time"] / 1000
    t1 = timing[last]["end_time"] / 1000 + (0.6 if last == ch["verses_count"] else 0)
    total = t1 - t0

    work = mr.CACHE / "work" / f"long_{s:03d}_{first:03d}-{last:03d}"
    work.mkdir(parents=True, exist_ok=True)
    mr.background(theme, work / "bg.jpg")
    mr.frame_layer(theme, ch, RECITER, work / "frame.png")
    # "Part 1 of 2 · Ayat 1-50" under the surah name
    fr = Image.open(work / "frame.png")
    d = ImageDraw.Draw(fr)
    d.text((mr.W / 2, 425), f"{part}  ·  Ayat {first}–{last}", font=mr.font("Lora-var.ttf", 32),
           fill=theme[2] + (230,), anchor="mm")
    fr.save(work / "frame.png")

    # ayah cards, each shown from its start to the next one's start
    lines = []
    for a in range(first, last + 1):
        st = 0.0 if a == first else timing[a]["start_time"] / 1000 - t0
        en = total if a == last else timing[a + 1]["start_time"] / 1000 - t0
        ar, eng = mr.verse(s, a)
        for n in range(1, 6):
            parts, shares = mr.split_parts(ar, eng, n) if n > 1 else ([(ar, eng)], [1.0])
            paths = [work / f"card_{a:03d}_{k}.png" for k in range(n)]
            if all(mr.card(theme, ch, s, a, pa, pe, RECITER, pp) for (pa, pe), pp in zip(parts, paths)):
                break
        else:
            raise SystemExit(f"Ayah {s}:{a} too long to display")
        for pp, sh in zip(paths, shares):
            lines.append((pp, (en - st) * sh))
    with open(work / "cards.txt", "w") as f:
        for p, dur in lines:
            f.write(f"file '{p.resolve()}'\nduration {dur:.3f}\n")
        f.write(f"file '{lines[-1][0].resolve()}'\n")  # concat needs the last image twice

    audio = work / "audio.m4a"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}", "-i", str(whole),
                    "-vn", "-af", f"afade=t=in:d=0.05,afade=t=out:st={total - 1.2:.2f}:d=1.2",
                    "-c:a", "aac", "-b:a", "160k", str(audio)], check=True)

    # background: nature video (Pixabay) when the key is set, else the drawn one drifting slowly
    scene = None
    if nature.available():
        import random
        try:
            scene, clips = nature.pick(total, random.Random(s * 1000 + first))
            at = 0.0
            for _, secs, cid in clips:  # to find a clip again if a scene has to go
                print(f"  {at / 60:5.1f} min  pixabay {cid}  ({secs:.0f} s)")
                at += secs - nature.FADE
            nature.render_background(clips, total, work / "bg.mp4")
            mr.dim_panel(work / "frame.png")
        except Exception as e:  # noqa: BLE001
            print(f"nature background failed ({e}), using the drawn one")
            scene = None
    bw, bh = int(mr.W * 1.12), int(mr.H * 1.12)
    period = 120.0  # slow drift of the background, repeating every 2 minutes
    bg0 = ("[0:v]format=yuv420p,fps=30[bg0];" if scene else
           f"[0:v]crop={mr.W}:{mr.H}:x='({bw - mr.W})/2+({bw - mr.W})/2*sin(t/{period}*3.1416)':"
           f"y='({bh - mr.H})/2+({bh - mr.H})/2*sin(t/{period * 1.3:.1f}*3.1416)',format=yuv420p,fps=30[bg0];")
    fc = (bg0 + f"[bg0][1:v]overlay=0:0:shortest=1[bg];"
          f"[2:v]format=rgba,fps=30[cards];[bg][cards]overlay=0:0:eof_action=repeat,"
          f"fade=t=out:st={total - 0.8:.2f}:d=0.8[vout]")
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stats",
                    *(["-stream_loop", "-1", "-i", str(work / "bg.mp4")] if scene else ["-loop", "1", "-i", str(work / "bg.jpg")]),
                    "-loop", "1", "-i", str(work / "frame.png"),
                    "-f", "concat", "-safe", "0", "-i", str(work / "cards.txt"), "-i", str(audio),
                    "-filter_complex", fc, "-map", "[vout]", "-map", "3:a", "-t", f"{total:.2f}",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "23", "-pix_fmt", "yuv420p", "-r", "30",
                    "-c:a", "copy", "-movflags", "+faststart", str(out)], check=True)
    print(f"{out}  ({total / 60:.1f} min, {last - first + 1} ayahs, background: {scene or 'drawn'})")
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("surah", type=int)
    ap.add_argument("first", type=int)
    ap.add_argument("last", type=int)
    ap.add_argument("--part", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    build(a.surah, a.first, a.last, a.part, Path(a.out))
