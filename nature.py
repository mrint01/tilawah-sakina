"""Calm nature video backgrounds for the surah reels, from Pixabay (free licence, no credit needed).

Needs PIXABAY_API_KEY in the environment (GitHub secret). Without it, make_reel falls back to its drawn background.
Clips with people are skipped; several clips of one theme are joined with crossfades to cover the whole reel.
"""
import json
import os
import random
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path

CACHE = Path(__file__).parent / "cache" / "pixabay"
W, H = 1080, 1920
THEMES = ["clouds sky", "ocean waves", "forest sunlight", "mountains", "waterfall", "rain leaves", "night sky stars",
          "desert dunes", "river", "sunset sky", "lake reflection", "snow mountains", "misty forest", "flowers meadow"]
NO = {"woman", "man", "people", "girl", "boy", "person", "couple", "child", "children", "model", "party", "bikini",
      "fashion", "dance", "music", "festival", "church", "cross", "christmas", "temple", "buddha", "statue", "alcohol",
      "wine", "beer", "dog", "cat", "car", "city", "building", "traffic", "face", "portrait", "selfie", "hand", "hands",
      "hut", "mountain hut", "house", "cabin", "home", "tent", "camping", "village", "road", "bridge", "boat", "ship",
      "pagoda", "shrine", "torii", "japan", "tower", "castle", "ruins", "monastery", "mosque", "lighthouse", "windmill", "flag"}
SLOW = 1.2   # clips play a little slower: calmer
FADE = 1.0   # crossfade between clips, seconds


def available():
    return bool(os.environ.get("PIXABAY_API_KEY"))


def _get(url, dest):
    if not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (tilawah-sakina reel maker)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            dest.write_bytes(r.read())
    return dest


def search(theme):
    url = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode(
        {"key": os.environ["PIXABAY_API_KEY"], "q": theme, "safesearch": "true", "per_page": 50, "video_type": "film"})
    p = _get(url, CACHE / "search" / f"{theme.replace(' ', '_')}.json")
    hits = json.loads(p.read_text())["hits"]
    return [h for h in hits if h["duration"] >= 10 and not ({t.strip() for t in h["tags"].split(",")} & NO)]


def clip_file(hit):
    v = hit["videos"].get("medium") or hit["videos"]["large"]
    if not v.get("url"):
        v = hit["videos"]["large"]
    return _get(v["url"], CACHE / "clips" / f"{hit['id']}.mp4")


def pick(total, rnd):
    """Clips covering `total` seconds (with crossfades): one random theme, or several in a row for long videos.
    Returns (theme(s), [(path, seconds, pixabay id)])."""
    themes = THEMES[:]
    rnd.shuffle(themes)
    out, covered, used = [], 0.0, []
    for theme in themes:
        hits = search(theme)
        if len(hits) < 3:
            continue
        rnd.shuffle(hits)
        used.append(theme)
        for h in hits:
            try:
                path = clip_file(h)
            except Exception:  # noqa: BLE001
                continue
            secs = h["duration"] * SLOW
            out.append((path, secs, h["id"]))
            covered += secs - (FADE if len(out) > 1 else 0)
            if covered >= total + 1:
                return " + ".join(used), out
    raise RuntimeError("not enough Pixabay clips")


def _xfade(parts, out, prep, grade_total=None):
    """Join [(file, seconds)] with crossfades. prep: filter applied to each input first."""
    ins, f = [], []
    for i, (path, _) in enumerate(parts):
        ins += ["-i", str(path)]
        f.append(f"[{i}:v]{prep}[c{i}]")
    last, offset = "c0", parts[0][1] - FADE
    for i in range(1, len(parts)):
        f.append(f"[{last}][c{i}]xfade=transition=fade:duration={FADE}:offset={offset:.3f}[x{i}]")
        last = f"x{i}"
        offset += parts[i][1] - FADE
    tail = f",trim=duration={grade_total:.3f},setpts=PTS-STARTPTS,eq=brightness=-0.08:saturation=0.9,vignette=PI/4.5" if grade_total else ""
    f.append(f"[{last}]null{tail}[bg]")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *ins, "-filter_complex", ";".join(f), "-map", "[bg]", "-an",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p", str(out)], check=True, timeout=3600)
    return offset + FADE  # length of the joined video


def render_background(clips, total, out):
    """Cover-crop each clip to 9:16, slow it, crossfade them, darken + vignette: a silent 30 fps video of `total` s.
    Long videos are joined in chunks of 8 clips (then the chunks are crossfaded), to keep memory low."""
    prep = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,setpts={SLOW}*(PTS-STARTPTS),fps=30,format=yuv420p"
    parts = [(p, secs) for p, secs, _ in clips]
    if len(parts) <= 8:
        _xfade(parts, out, prep, total)
        return out
    chunks = []
    for k in range(0, len(parts), 8):
        cf = Path(out).with_name(f"{Path(out).stem}_chunk{k // 8}.mp4")
        chunks.append((cf, _xfade(parts[k:k + 8], cf, prep)))
    _xfade(chunks, out, "format=yuv420p,fps=30", total)
    for cf, _ in chunks:
        cf.unlink(missing_ok=True)
    return out


if __name__ == "__main__":
    import sys
    theme, clips = pick(float(sys.argv[1]) if len(sys.argv) > 1 else 30, random.Random())
    print(theme, [(str(p.name), round(s, 1)) for p, s, _ in clips])
