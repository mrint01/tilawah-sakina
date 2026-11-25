"""Tilawah Sakina pipeline: generate -> check -> review -> post.

  python3 pipeline.py generate --ayah 2 --tasbih 1   # render reels into staging/ as "pending"
  python3 pipeline.py approve <id> [--note "..."]    # mark OK and upload video to the 'queue' release
  python3 pipeline.py reject <id> --note "why"
  python3 pipeline.py status                          # what is pending / approved / posted
  python3 pipeline.py next --slot 06:00               # (CI) id of the reel to post in that slot, or nothing
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


LENGTH_CHECK = {
    "ayah": lambda d: {"length_60_90s": 58 <= d <= 92},
    "ayah_whole": lambda d: {"length_whole_surah": 8 <= d <= 92},
    "tasbih": lambda d: {"length_60s": 57 <= d <= 63},
    "dua": lambda d: {"length_10_60s": 10 <= d <= 62},
    "asma": lambda d: {"length_8_75s": 8 <= d <= 75},
    "quiz": lambda d: {"length_50_150s": 50 <= d <= 150},
}
KINDS = ("ayah", "dua", "asma", "tasbih", "quiz")


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
        # ayah reels 60-90 s (a short surah picked in the panel is shown whole); tasbih exactly one minute;
        # dua 10-60 s; asma (one name + one ayah) 8-75 s; quiz (5 questions) 50-150 s
        **LENGTH_CHECK[("ayah_whole" if kind == "ayah" and whole_surah else kind)](dur),
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
        return [j for j in jobs if j.get("kind") in KINDS]
    starts = [{"kind": "ayah", "start": [int(x) for x in s.split(":")]} for s in (args.start or [])]
    return ((starts or [{"kind": "ayah"}] * args.ayah) + [{"kind": "dua"}] * args.dua + [{"kind": "asma"}] * args.asma
            + [{"kind": "tasbih"}] * args.tasbih + [{"kind": "quiz"}] * args.quiz)


def cmd_generate(args):
    sys.path.insert(0, str(HERE))
    import make_asma
    import make_dua
    import make_quiz
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
        # one post of each kind a day: keep `buffer` days of each kind ready (pending + approved)
        days = config().get("buffer_days", 3)
        stock = {k: sum(1 for it in q["items"] if it["kind"] == k and it["status"] in ("pending", "approved")) for k in KINDS}
        want = {k: max(0, min(2, days - stock[k])) for k in KINDS}
        print("stock", stock, "-> making", want)
        args.ayah, args.dua, args.asma, args.tasbih, args.quiz = (want[k] for k in KINDS)
        args.start = None
        if not any(want.values()):
            print(f"every kind has {days} days ready, not generating")
            return
    # don't repeat a passage that is still waiting or was posted in the last 60 items
    recent = [tuple(it["passage"]) for it in q["items"][-60:] if it.get("passage")]
    jobs = plan_jobs(args)
    ensure_release()
    prog = Progress(len(jobs))
    # one reel failing must not lose the others: note it, go on, and fail the run only if nothing was made
    failed = []
    for i, job in enumerate(jobs):
        try:
            make_one(job, i, q, recent, prog, make_reel, make_tasbih, make_dua, make_asma, make_quiz)
        except (Exception, SystemExit) as e:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            failed.append(f"{job.get('kind')}: {e}")
            print(f"::warning::could not make {job}: {e}")
    if failed and len(failed) == len(jobs):
        prog.close(error="; ".join(failed)[:300])
        sys.exit("no reel could be made: " + "; ".join(failed))
    prog.close()


def make_one(job, i, q, recent, prog, make_reel, make_tasbih, make_dua, make_asma, make_quiz):
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
    elif kind == "dua":
        cat = job.get("category")
        if cat not in make_dua.CATEGORIES:
            cat = next_dua_category(q)
        used = [it.get("dua_id") for it in q["items"] if it.get("kind") == "dua" and it["status"] != "rejected"]
        prog.set(done=i, frac=0, current=make_dua.CATEGORIES[cat]["label"], stage="rendering")
        meta = make_dua.render(category=cat, dua_id=job.get("dua_id"), seed=seed, used=used, progress=step)
    elif kind == "asma":
        number = int(job["number"]) if str(job.get("number", "")).isdigit() and 1 <= int(job["number"]) <= 99 else next_asma_number(q)
        prog.set(done=i, frac=0, current=f"Name {number} of 99", stage="rendering")
        meta = make_asma.render(number, reciter=job.get("reciter"), seed=seed, progress=step)
    elif kind == "quiz":
        level = job.get("level") if job.get("level") in make_quiz.LEVELS else random.Random(seed).choices(
            ["easy", "medium", "hard"], [5, 3, 2])[0]
        prog.set(done=i, frac=0, current=f"Quiz · {level}", stage="rendering")
        meta = make_quiz.render(level, seed=seed, progress=step)
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
    # the grid cover: title centred where Instagram's profile grid always shows it
    import covers
    cover = STAGING / f"{item_id}-cover.jpg"
    try:
        covers.cover_for({"kind": kind, **meta}, mp4, cover)
    except Exception as e:  # noqa: BLE001
        print(f"::warning::no cover for {item_id}: {e}")
        cover = None
    subprocess.run(["gh", "release", "upload", RELEASE_TAG, str(mp4), str(png), str(small), *([str(cover)] if cover else []),
                    "--clobber"], check=True, cwd=HERE)
    if cover:
        meta["cover"] = True
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


# Daily posting slots, Tunisia time (UTC+1, no daylight saving) -> the kind posted. post.yml runs at these times.
SLOTS = {"00:00": "ayah", "06:00": "dua", "12:00": "asma", "18:00": "tasbih", "21:00": "quiz"}
# The 06:00 dua by weekday (Monday = 0): morning adhkar 3x, after salah 2x, a need, salawat on Friday.
DUA_BY_WEEKDAY = ["morning", "need", "morning", "after_salah", "friday", "morning", "after_salah"]


def tunis_now():
    from datetime import timedelta
    return datetime.now(timezone.utc) + timedelta(hours=1)


def next_dua_category(q):
    """The kind of dua the coming days need most, given what is already waiting."""
    from collections import Counter
    need = Counter(DUA_BY_WEEKDAY)          # posts per week of each kind
    have = Counter(it.get("category") for it in q["items"] if it.get("kind") == "dua" and it["status"] in ("pending", "approved"))
    return max(need, key=lambda c: need[c] - have[c] * 2)


def next_asma_number(q):
    """The series goes 1 -> 99 and starts again: one after the highest number made so far (not rejected)."""
    made = [it.get("number", 0) for it in q["items"] if it.get("kind") == "asma" and it["status"] != "rejected"]
    return (max(made) % 99) + 1 if made else 1


def is_arafah(day):
    """9 Dhul Hijjah (Umm al-Qura calendar, from api.aladhan.com); False when the API can't be reached."""
    try:
        url = f"https://api.aladhan.com/v1/gToH/{day.strftime('%d-%m-%Y')}"
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "reel-maker/1.0"}), timeout=20) as r:
            h = json.loads(r.read())["data"]["hijri"]
        return int(h["month"]["number"]) == 12 and int(h["day"]) == 9
    except Exception:  # noqa: BLE001
        return False


def slot_kind(slot=None):
    """The kind for a slot ("06:00"), or for the slot closest to now (manual runs)."""
    if slot in SLOTS:
        return SLOTS[slot]
    now = tunis_now()
    mins = now.hour * 60 + now.minute
    def dist(t):
        h, m = map(int, t.split(":"))
        d = abs(h * 60 + m - mins)
        return min(d, 1440 - d)
    return SLOTS[min(SLOTS, key=dist)]


def next_item(slot=None, kind=None):
    """The approved reel to post now: oldest approved of the slot's kind. For the dua slot: the Arafah dua on the
    Day of Arafah, else the weekday's kind of dua, else any other dua (never the Arafah one on another day)."""
    if not config().get("enabled", True):
        return None
    q = queue()
    kind = kind or slot_kind(slot)
    approved = [it for it in q["items"] if it["status"] == "approved" and it["kind"] == kind]
    if kind == "dua":
        today = tunis_now()
        if is_arafah(today):
            pick = [it for it in approved if it.get("category") == "arafah"]
            if pick:
                return pick[0]
        approved = [it for it in approved if it.get("category") != "arafah"]
        want = DUA_BY_WEEKDAY[today.weekday()]
        pick = [it for it in approved if it.get("category") == want]
        return (pick or approved or [None])[0]
    if kind == "asma":  # keep the series in order
        approved.sort(key=lambda it: it.get("number", 0))
    return approved[0] if approved else None


# Every slot is tracked in queue.json "slots" ("2026-11-25 06:00" -> what happened), so a slot is never posted twice,
# a late or skipped GitHub run is caught up by the next hourly run, and a slot that could not be posted in time is
# kept as "missed" with the reason (shown in the panel).
SLOT_LATE_H = 3           # a slot may still be posted up to 3 hours late (and never after the next slot starts)
SLOT_TRIES = 3            # posting attempts per slot
SLOTS_FROM = "2026-11-25 06:00"   # tracking starts here (older slots are not reported)


def _tunis():
    from datetime import timedelta
    return timezone(timedelta(hours=1))


def slot_windows(at):
    """(key, slot, start, end) for every slot of the last 2 days and today, Tunisia time."""
    from datetime import timedelta
    out = []
    for back in (2, 1, 0):
        day = (at - timedelta(days=back)).date()
        for s in sorted(SLOTS):
            h, m = map(int, s.split(":"))
            out.append((f"{day} {s}", s, datetime(day.year, day.month, day.day, h, m, tzinfo=_tunis())))
    res = []
    for i, (key, s, t) in enumerate(out):
        nxt = out[i + 1][2] if i + 1 < len(out) else t + timedelta(hours=24)
        res.append((key, s, t, min(nxt, t + timedelta(hours=SLOT_LATE_H))))
    return res


def _posted_in(q, kind, t, end):
    """A reel of this kind that went out for this slot (also a "Publish now" shortly before or during it)."""
    from datetime import timedelta
    for it in q["items"]:
        if it["kind"] == kind and it["status"] == "posted" and it.get("posted") and not it.get("made_up"):
            p = datetime.fromisoformat(it["posted"])
            if t - timedelta(minutes=30) <= p < end:
                return it
    return None


def update_slots(q, at=None):
    """Bring the slot log up to date; returns (key, slot, start, entry) of the slot to post now, or None."""
    from datetime import timedelta
    at = at or datetime.now(_tunis())
    log = q.setdefault("slots", {})
    on = config().get("enabled", True)
    due = None
    for key, s, t, end in slot_windows(at):
        if key < SLOTS_FROM or t > at:
            continue
        e = log.get(key)
        if e and e["status"] in ("posted", "missed", "off", "resolved"):
            continue
        kind = SLOTS[s]
        it = _posted_in(q, kind, t, end)
        if it:
            late = int((datetime.fromisoformat(it["posted"]) - t).total_seconds() // 60)
            log[key] = {"kind": kind, "status": "posted", "id": it["id"], "title": it.get("title"), "posted": it["posted"],
                        "late_min": max(0, late), "tries": (e or {}).get("tries", 0)}
            continue
        if at >= end:
            if not on:
                log[key] = {"kind": kind, "status": "off", "reason": "Automation was OFF"}
            elif e:
                log[key] = {**e, "status": "missed", "reason": e.get("reason") or "The posting run stopped before the reel was live"}
            elif not any(i["kind"] == kind and i["status"] == "approved" for i in q["items"]):
                log[key] = {"kind": kind, "status": "missed", "reason": "Nothing approved of this type to post"}
            else:
                log[key] = {"kind": kind, "status": "missed",
                            "reason": f"GitHub never started the posting run (its scheduler skipped it for {SLOT_LATE_H} hours)"}
            log[key]["at"] = t.isoformat()
            continue
        if on and (not e or e.get("tries", 0) < SLOT_TRIES):
            due = (key, s, t, e)
    # keep the log small: last 30 days
    cut = str((at - timedelta(days=30)).date())
    for k in [k for k in log if k < cut]:
        del log[k]
    return due


def cmd_next(args):
    if args.due:
        # scheduled / catch-up runs: post the current slot if it is not posted yet (late is fine, twice never)
        q = queue()
        due = update_slots(q)
        it = None
        if due:
            key, s, t, e = due
            it = next_item(s)
            if it and not args.dry:
                q["slots"][key] = {"kind": SLOTS[s], "status": "posting", "id": it["id"], "title": it.get("title"),
                                   "tries": (e or {}).get("tries", 0) + 1, "started": now(), "at": t.isoformat(),
                                   "reason": (e or {}).get("reason")}
            print(f"slot {key}: {'posting ' + it['id'] if it else 'nothing approved'}", file=sys.stderr)
        else:
            print("no slot to post now", file=sys.stderr)
        save(QUEUE, q)
        if it:
            print(it["id"])
        return
    it = next_item(args.slot, args.kind)
    if it:
        print(it["id"])


def slot_result(q, item_id, ok, reason=None):
    """Record how the slot being posted with this reel ended."""
    for e in q.get("slots", {}).values():
        if e.get("id") == item_id and e["status"] == "posting":
            if ok:
                it = find(q, item_id)
                late = int((datetime.fromisoformat(it["posted"]) - datetime.fromisoformat(e["at"])).total_seconds() // 60)
                e.update(status="posted", posted=it["posted"], late_min=max(0, late), reason=None)
            else:
                e.update(status="failed", reason=reason or "Posting failed")


def cmd_slotfail(args):
    q = queue()
    slot_result(q, args.id, False, args.error)
    save(QUEUE, q)


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


POSTING = STAGING / "posting.json"
POST_STAGES = {"preparing": 10, "video": 25, "hosting": 40, "uploading": 50, "processing": 55, "publishing": 90,
               "live": 100, "failed": 100}


def posting(stage, item_id=None, pct=None, **extra):
    """Live progress of a post for the panel: posting.json in the 'queue' release (no commit)."""
    d = json.loads(POSTING.read_text()) if POSTING.exists() else {}
    run = os.environ.get("GITHUB_RUN_ID", "local")
    if d.get("run_id") != run:
        d = {"run_id": run, "started": now()}
    if item_id:
        d["id"] = item_id
        try:
            d["title"] = find(queue(), item_id).get("title")
        except SystemExit:
            pass
    d.update(stage=stage, pct=pct if pct is not None else POST_STAGES.get(stage, 0), updated=now(),
             finished=stage in ("live", "failed"), **extra)
    STAGING.mkdir(exist_ok=True)
    POSTING.write_text(json.dumps(d, ensure_ascii=False))
    subprocess.run(["gh", "release", "upload", RELEASE_TAG, str(POSTING), "--clobber"], capture_output=True, cwd=HERE)


def cmd_posting(args):
    posting(args.stage, args.id, error=args.error) if args.error else posting(args.stage, args.id)


def cmd_post(args):
    q = queue()
    it = find(q, args.id)
    user = os.environ["IG_USER_ID"]
    posting("uploading", it["id"])
    extra = {"cover_url": args.cover_url} if getattr(args, "cover_url", None) else {}
    c = ig("POST", f"{user}/media", media_type="REELS", video_url=args.url,
           caption=it["caption"], share_to_feed="true", **extra)
    cid = c["id"]
    print("container", cid, "with cover" if extra else "")
    for k in range(60):  # up to ~10 minutes of processing
        st = ig("GET", cid, fields="status_code,status")
        print("status", st.get("status_code"))
        posting("processing", pct=min(85, 55 + k * 4))
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            it.update(status="failed", review=f"instagram: {st.get('status')}")
            save(QUEUE, q)
            posting("failed", error=f"Instagram could not process the video ({st.get('status')})")
            sys.exit(f"Instagram could not process the video: {st}")
        time.sleep(10)
    else:
        posting("failed", error="Instagram took too long to process the video")
        sys.exit("timed out waiting for Instagram to process the video")
    posting("publishing")
    pub = publish(user, cid)
    media = ig("GET", pub["id"], fields="permalink")
    it.update(status="posted", posted=now(), ig_media_id=pub["id"], permalink=media.get("permalink"))
    slot_result(q, it["id"], True)
    e = q.get("slots", {}).get(getattr(args, "slot", None) or "")
    if e and e["status"] in ("missed", "failed"):  # published from the panel's "Not posted" page
        late = int((datetime.fromisoformat(it["posted"]) - datetime.fromisoformat(e["at"])).total_seconds() // 60) if e.get("at") else 0
        it["made_up"] = args.slot  # it stands for that slot, not for a slot that is due now
        e.update(status="posted", recovered=True, id=it["id"], title=it.get("title"), posted=it["posted"], late_min=max(0, late))
    save(QUEUE, q)
    posting("live", permalink=media.get("permalink"))
    print("posted", media.get("permalink"))


def cmd_covers(args):
    """Add grid covers to pending / approved reels that have none (made before covers existed)."""
    import covers
    q = queue()
    todo = [it for it in q["items"] if it["status"] in ("pending", "approved") and not it.get("cover")]
    STAGING.mkdir(exist_ok=True)
    for it in todo:
        mp4 = STAGING / f"{it['id']}.mp4"
        if not mp4.exists():
            subprocess.run(["gh", "release", "download", RELEASE_TAG, "-p", f"{it['id']}.mp4", "-D", str(STAGING)],
                           check=True, cwd=HERE)
        cover = STAGING / f"{it['id']}-cover.jpg"
        covers.cover_for(it, mp4, cover)
        subprocess.run(["gh", "release", "upload", RELEASE_TAG, str(cover), "--clobber"], check=True, cwd=HERE)
        it["cover"] = True
        print("cover", it["id"], it["title"])
    save(QUEUE, q)


def cmd_check(args):
    """(CI) Is this reel approved and ready to publish? Prints its id, or nothing."""
    q = queue()
    it = next((i for i in q["items"] if i["id"] == args.id), None)
    if it and it["status"] == "approved":
        print(it["id"])
    else:
        print(f"{args.id} is not an approved reel ({it['status'] if it else 'not found'})", file=sys.stderr)


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
    g.add_argument("--dua", type=int, default=0); g.add_argument("--asma", type=int, default=0); g.add_argument("--quiz", type=int, default=0)
    g.add_argument("--spec", help='JSON list of jobs from the panel, e.g. [{"kind":"ayah","surah":18,"reciter":"Mishary Alafasy"}]')
    g.add_argument("--start", action="append", help="surah:ayah to start an ayah reel at (repeatable; replaces --ayah)")
    g.add_argument("--auto", action="store_true", help="skip when automation is OFF or the queue already holds `buffer` reels")
    a = sub.add_parser("approve"); a.add_argument("id"); a.add_argument("--note")
    r = sub.add_parser("reject"); r.add_argument("id"); r.add_argument("--note", required=True)
    sub.add_parser("status")
    n = sub.add_parser("next"); n.add_argument("--slot", help="posting slot, e.g. 06:00 (Tunisia)"); n.add_argument("--kind", choices=KINDS)
    n.add_argument("--due", action="store_true", help="the slot due now (late runs catch up, a slot posts once)")
    n.add_argument("--dry", action="store_true", help="with --due: only record missed slots and say what is due")
    sf = sub.add_parser("slotfail"); sf.add_argument("id"); sf.add_argument("--error")
    p = sub.add_parser("post"); p.add_argument("id"); p.add_argument("--url", required=True); p.add_argument("--cover-url"); p.add_argument("--slot", help="a missed slot this post makes up for (\"2026-11-25 06:00\")")
    pp = sub.add_parser("posting"); pp.add_argument("stage", choices=list(POST_STAGES)); pp.add_argument("--id"); pp.add_argument("--error")
    ck = sub.add_parser("check"); ck.add_argument("id")
    sub.add_parser("covers")
    args = ap.parse_args()
    globals()[f"cmd_{args.cmd}"](args)
