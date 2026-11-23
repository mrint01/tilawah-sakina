"""Tilawah Sakina pipeline: generate -> check -> review -> post.

  python3 pipeline.py generate --ayah 2 --tasbih 1   # render reels into staging/ as "pending"
  python3 pipeline.py approve <id> [--note "..."]    # mark OK and upload video to the 'queue' release
  python3 pipeline.py reject <id> --note "why"
  python3 pipeline.py status                          # what is pending / approved / posted
  python3 pipeline.py next                            # (CI) print id of the next reel to post, or nothing
  python3 pipeline.py post <id> --url <public mp4 url> # (CI) publish to Instagram and mark posted

State lives in state/queue.json and state/config.json (both committed).
Videos live in the GitHub release tagged 'queue' (not in git history, so the repo stays small).
"""
import argparse
import json
import os
import random
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).parent
STATE = HERE / "state"
QUEUE = STATE / "queue.json"
CONFIG = STATE / "config.json"
STAGING = HERE / "staging"
RELEASE_TAG = "queue"
# Instagram Login tokens ("IG...") use graph.instagram.com; Facebook / system-user tokens ("EAA...") use graph.facebook.com
GRAPH = ("https://graph.facebook.com/v22.0" if os.environ.get("IG_ACCESS_TOKEN", "").startswith("EAA")
         else "https://graph.instagram.com/v22.0")


# ---------- state ----------
def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def save(path, data):
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def queue():
    return load(QUEUE, {"items": []})


def config():
    return load(CONFIG, {"enabled": True, "alternate": ["ayah", "tasbih"]})


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def find(q, item_id):
    for it in q["items"]:
        if it["id"] == item_id:
            return it
    sys.exit(f"no item {item_id}")


# ---------- automatic checks ----------
def probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "stream=codec_type,codec_name,width,height,r_frame_rate:format=duration,size",
         "-of", "json", str(path)], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def mean_volume(path):
    err = subprocess.run(["ffmpeg", "-i", str(path), "-af", "volumedetect", "-vn", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    for line in err.splitlines():
        if "mean_volume" in line:
            return float(line.split(":")[1].split()[0])
    return -99.0


def run_checks(path, kind="ayah", whole_surah=False):
    info = probe(path)
    v = next((s for s in info["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in info["streams"] if s["codec_type"] == "audio"), {})
    dur = float(info["format"]["duration"])
    size_mb = int(info["format"]["size"]) / 1e6
    vol = mean_volume(path)
    checks = {
        "size_1080x1920": v.get("width") == 1080 and v.get("height") == 1920,
        "video_h264": v.get("codec_name") == "h264",
        "audio_aac": a.get("codec_name") == "aac",
        # ayah reels 60-90 s; tasbih reels are always one minute (33 counts down to 0)
        # (a short surah picked in the panel is shown whole, even when it is under a minute)
        **({"length_whole_surah": 8 <= dur <= 92} if kind == "ayah" and whole_surah
           else {"length_60_90s": 58 <= dur <= 92} if kind == "ayah" else {"length_60s": 57 <= dur <= 63}),
        "audio_not_silent": vol > -45,
        "file_under_100mb": size_mb < 100,
    }
    return checks, {"duration": round(dur, 1), "size_mb": round(size_mb, 1), "mean_volume_db": vol}


def preview_video(path, out):
    """Small copy for the panel's player (phones): 540x960, ~2 MB, so the panel can serve it itself."""
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(path), "-vf", "scale=540:-2",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "30", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "64k", "-movflags", "+faststart", str(out)], check=True)


def contact_sheet(path, out, n=6):
    """n frames side by side so a reviewer (human or Claude) can see the whole reel at a glance."""
    from PIL import Image
    dur = float(probe(path)["format"]["duration"])
    tmp = out.with_suffix("")
    tmp.mkdir(exist_ok=True)
    frames = []
    for i in range(n):
        t = dur * (i + 0.5) / n
        f = tmp / f"{i}.png"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", str(path),
                        "-frames:v", "1", "-vf", "scale=360:-1", str(f)], check=True)
        frames.append(Image.open(f))
    sheet = Image.new("RGB", (sum(f.width for f in frames) + 8 * (n - 1), frames[0].height), "white")
    x = 0
    for f in frames:
        sheet.paste(f, (x, 0))
        x += f.width + 8
    sheet.save(out)
    shutil.rmtree(tmp)


# ---------- commands ----------
class Progress:
    """Live render progress for the panel: progress.json in the release, re-uploaded every few seconds
    from a background thread (no commits, so the queue history stays clean)."""

    def __init__(self, total):
        import threading
        self.path = STAGING / "progress.json"
        self.data = {"run_id": os.environ.get("GITHUB_RUN_ID", "local"), "total": total, "done": 0,
                     "current": "", "stage": "starting", "frac": 0.0, "pct": 0, "finished": False}
        self.dirty, self.stop = True, threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def set(self, **kw):
        self.data.update(kw)
        d = self.data
        d["pct"] = round(100 * (d["done"] + min(1.0, d["frac"])) / max(1, d["total"]))
        d["updated"] = now()
        self.dirty = True

    def _push(self):
        if not self.dirty:
            return
        self.dirty = False
        self.path.write_text(json.dumps(self.data))
        subprocess.run(["gh", "release", "upload", RELEASE_TAG, str(self.path), "--clobber"],
                       capture_output=True, cwd=HERE)

    def _loop(self):
        while not self.stop.wait(6):
            self._push()

    def close(self, error=None):
        if not error:
            self.data.update(done=self.data["total"], frac=0.0)
        self.set(finished=True, stage="failed" if error else "done", error=error)
        self.stop.set()
        self.thread.join(timeout=30)
        self._push()


def plan_jobs(args):
    """What to make: --spec JSON from the panel, else --start / --ayah / --tasbih."""
    if args.spec:
        jobs = json.loads(args.spec)
        if not isinstance(jobs, list) or not 1 <= len(jobs) <= 10:
            sys.exit("--spec must be a JSON list of 1-10 jobs")
        return [j for j in jobs if j.get("kind") in ("ayah", "tasbih")]
    starts = [{"kind": "ayah", "start": [int(x) for x in s.split(":")]} for s in (args.start or [])]
    return (starts or [{"kind": "ayah"}] * args.ayah) + [{"kind": "tasbih"}] * args.tasbih


def cmd_generate(args):
    sys.path.insert(0, str(HERE))
    import make_reel
    import make_tasbih

    from PIL import features
    if not features.check("raqm"):
        sys.exit("Pillow has no libraqm: Arabic would render broken. Install libraqm (apt install libraqm0).")

    q = queue()
    STAGING.mkdir(exist_ok=True)
    if args.auto:
        if not config().get("enabled", True):
            print("automation is OFF, not generating")
            return
        buffer = sum(1 for it in q["items"] if it["status"] in ("pending", "approved"))
        target = config().get("buffer", 14)
        if buffer >= target:
            print(f"buffer full ({buffer}/{target}), not generating")
            return
    # don't repeat a passage that is still waiting or was posted in the last 60 items
    recent = [tuple(it["passage"]) for it in q["items"][-60:] if it.get("passage")]
    jobs = plan_jobs(args)
    ensure_release()
    prog = Progress(len(jobs))
    try:
        for i, job in enumerate(jobs):
            make_one(job, i, q, recent, prog, make_reel, make_tasbih)
    except BaseException as e:
        prog.close(error=str(e) or type(e).__name__)
        raise
    prog.close()


def make_one(job, i, q, recent, prog, make_reel, make_tasbih):
    kind = job["kind"]
    seed = random.randrange(10**9)
    step = lambda frac: prog.set(frac=0.85 * frac)  # rendering is ~85% of the time, checks + upload the rest
    if kind == "ayah":
        start = tuple(job["start"]) if job.get("start") else None
        surah = int(job["surah"]) if job.get("surah") else None
        sn = start[0] if start else surah
        label = f"Surah {make_reel.chapters()[sn]['name_simple']}" if sn else "Ayah reel"
        prog.set(done=i, frac=0, current=label + (f" · {job['reciter']}" if job.get("reciter") else ""), stage="rendering")
        meta = make_reel.build(start=start, surah=None if start else surah, reciter=job.get("reciter"),
                               seed=seed, exclude=recent, progress=step)
        recent.append(tuple(meta["passage"]))
    else:
        key = job.get("set")
        if key not in make_tasbih.SETS:
            # least-used dhikr set first, so the queue doesn't fill up with the same one
            used = [it.get("set") for it in q["items"] if it.get("set") and it["status"] != "rejected"]
            sets = list(make_tasbih.SETS)
            random.Random(seed).shuffle(sets)
            key = min(sets, key=used.count)
        prog.set(done=i, frac=0, current=make_tasbih.SETS[key]["title"], stage="rendering")
        meta = make_tasbih.render(key, seed=seed, progress=step)
    prog.set(current=meta["title"], stage="checking", frac=0.85)
    item_id = datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{kind}"
    mp4 = STAGING / f"{item_id}.mp4"
    shutil.move(meta.pop("file"), mp4)
    checks, stats = run_checks(mp4, kind, meta.get("whole_surah", False))
    png = STAGING / f"{item_id}.png"
    contact_sheet(mp4, png)
    small = STAGING / f"{item_id}-preview.mp4"
    preview_video(mp4, small)
    prog.set(stage="uploading", frac=0.92)
    # video + previews go to the release right away, so the panel (and the poster) can reach them
    subprocess.run(["gh", "release", "upload", RELEASE_TAG, str(mp4), str(png), str(small), "--clobber"], check=True, cwd=HERE)
    item = {"id": item_id, **meta, **stats, "checks": checks,
            "status": "pending" if all(checks.values()) else "rejected",
            "review": None if all(checks.values()) else "failed automatic checks",
            "created": now()}
    q["items"].append(item)
    save(QUEUE, q)
    bad = [k for k, ok in checks.items() if not ok]
    print(f"{item_id}: {item['title']}  checks={'OK' if not bad else 'FAILED ' + ', '.join(bad)}")


def cmd_approve(args):
    q = queue()
    it = find(q, args.id)
    it.update(status="approved", review=args.note or "approved", reviewed=now())
    save(QUEUE, q)
    print(f"approved {it['id']}")


def cmd_reject(args):
    q = queue()
    it = find(q, args.id)
    it.update(status="rejected", review=args.note, reviewed=now())
    save(QUEUE, q)
    print(f"rejected {it['id']}: {args.note}")


def cmd_status(args):
    q = queue()
    for st in ("pending", "approved", "posted", "rejected", "failed"):
        items = [it for it in q["items"] if it["status"] == st]
        print(f"{st:9} {len(items)}")
        for it in items[-5:]:
            print(f"    {it['id']}  {it['title']}")
    print("automation:", "ON" if config()["enabled"] else "OFF")


def next_item():
    cfg = config()
    if not cfg.get("enabled", True):
        return None
    q = queue()
    approved = [it for it in q["items"] if it["status"] == "approved"]
    if not approved:
        return None
    posted = [it for it in q["items"] if it["status"] == "posted"]
    order = cfg.get("alternate", ["ayah", "tasbih"])
    want = order[(order.index(posted[-1]["kind"]) + 1) % len(order)] if posted and posted[-1]["kind"] in order else order[0]
    for it in approved:
        if it["kind"] == want:
            return it
    return approved[0]


def cmd_next(args):
    it = next_item()
    if it:
        print(it["id"])


class IGError(Exception):
    pass


def ig(method, path, fatal=True, **params):
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    data = urllib.parse.urlencode(params).encode()
    url = f"{GRAPH}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        msg = f"Instagram API error {e.code}: {e.read().decode()[:500]}"
        if fatal:
            sys.exit(msg)
        raise IGError(msg)


def publish(user, cid):
    """media_publish, retried: right after FINISHED Instagram sometimes answers with a generic internal
    error (subcode 2207085). Retrying the same container can't post twice: a container publishes once."""
    for wait in (15, 30, 60, 120, 180):
        time.sleep(wait)
        try:
            return ig("POST", f"{user}/media_publish", fatal=False, creation_id=cid)
        except IGError as e:
            print(f"publish failed, retrying: {e}")
    return ig("POST", f"{user}/media_publish", creation_id=cid)


def cmd_post(args):
    q = queue()
    it = find(q, args.id)
    user = os.environ["IG_USER_ID"]
    c = ig("POST", f"{user}/media", media_type="REELS", video_url=args.url,
           caption=it["caption"], share_to_feed="true")
    cid = c["id"]
    print("container", cid)
    for _ in range(60):  # up to ~10 minutes of processing
        st = ig("GET", cid, fields="status_code,status")
        print("status", st.get("status_code"))
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            it.update(status="failed", review=f"instagram: {st.get('status')}")
            save(QUEUE, q)
            sys.exit(f"Instagram could not process the video: {st}")
        time.sleep(10)
    else:
        sys.exit("timed out waiting for Instagram to process the video")
    pub = publish(user, cid)
    media = ig("GET", pub["id"], fields="permalink")
    it.update(status="posted", posted=now(), ig_media_id=pub["id"], permalink=media.get("permalink"))
    save(QUEUE, q)
    print("posted", media.get("permalink"))


def ensure_release():
    r = subprocess.run(["gh", "release", "view", RELEASE_TAG], capture_output=True, cwd=HERE)
    if r.returncode != 0:
        subprocess.run(["gh", "release", "create", RELEASE_TAG, "--title", "Reel queue",
                        "--notes", "Approved reels waiting to be posted. Managed by pipeline.py.", "--prerelease"],
                       check=True, cwd=HERE)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate"); g.add_argument("--ayah", type=int, default=1); g.add_argument("--tasbih", type=int, default=1)
    g.add_argument("--spec", help='JSON list of jobs from the panel, e.g. [{"kind":"ayah","surah":18,"reciter":"Mishary Alafasy"}]')
    g.add_argument("--start", action="append", help="surah:ayah to start an ayah reel at (repeatable; replaces --ayah)")
    g.add_argument("--auto", action="store_true", help="skip when automation is OFF or the queue already holds `buffer` reels")
    a = sub.add_parser("approve"); a.add_argument("id"); a.add_argument("--note")
    r = sub.add_parser("reject"); r.add_argument("id"); r.add_argument("--note", required=True)
    sub.add_parser("status")
    sub.add_parser("next")
    p = sub.add_parser("post"); p.add_argument("id"); p.add_argument("--url", required=True)
    args = ap.parse_args()
    globals()[f"cmd_{args.cmd}"](args)
