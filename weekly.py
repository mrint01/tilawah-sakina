"""Weekly reels: the same videos posted again every week (Surah Al-Kahf, parts 1 and 2, on Fridays).

The videos live in the GitHub release tagged 'weekly', which nothing ever cleans up.
state/weekly.json holds their captions and every time they went out.

    python3 weekly.py which "<cron string>"     # (CI) the id that this Friday schedule posts
    python3 weekly.py post <id> --url <mp4 url>  # (CI) publish to Instagram and record it
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pipeline

WEEKLY = Path(__file__).parent / "state" / "weekly.json"


def load():
    return json.loads(WEEKLY.read_text())


def cmd_which(args):
    for it in load()["items"]:
        if it["cron"] == args.cron or it["id"] == args.cron:
            print(it["id"])
            return
    sys.exit(f"no weekly reel for {args.cron!r}")


def cmd_post(args):
    import os
    import time
    w = load()
    it = next(i for i in w["items"] if i["id"] == args.id)
    user = os.environ["IG_USER_ID"]
    c = pipeline.ig("POST", f"{user}/media", media_type="REELS", video_url=args.url,
                    caption=it["caption"], share_to_feed="true")
    for _ in range(120):  # long videos take a while to process (up to ~20 min)
        st = pipeline.ig("GET", c["id"], fields="status_code,status")
        print("status", st.get("status_code"))
        if st.get("status_code") == "FINISHED":
            break
        if st.get("status_code") in ("ERROR", "EXPIRED"):
            sys.exit(f"Instagram could not process the video: {st}")
        time.sleep(10)
    else:
        sys.exit("timed out waiting for Instagram to process the video")
    pub = pipeline.publish(user, c["id"])
    link = pipeline.ig("GET", pub["id"], fields="permalink").get("permalink")
    w.setdefault("posted", []).append({"id": it["id"], "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                       "ig_media_id": pub["id"], "permalink": link})
    WEEKLY.write_text(json.dumps(w, indent=2, ensure_ascii=False) + "\n")
    print("posted", link)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("which").add_argument("cron")
    p = sub.add_parser("post"); p.add_argument("id"); p.add_argument("--url", required=True)
    a = ap.parse_args()
    globals()[f"cmd_{a.cmd}"](a)
