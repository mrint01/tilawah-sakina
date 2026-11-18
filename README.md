# Tilawah Sakina

Daily Quran recitation and tasbih Reels for Instagram **@tilawah.sakina**: generated, checked, then posted automatically.

## How it works
1. `pipeline.py generate`: renders reels (`make_reel.py` = ayahs + recitation, `make_tasbih.py` = dhikr counter) into `staging/`, runs automatic checks, and writes a contact sheet per reel.
2. Review: a human or Claude looks at the contact sheet, then runs `pipeline.py approve <id>` (uploads the video to the `queue` release) or `pipeline.py reject <id> --note "..."`.
3. `.github/workflows/post.yml` runs at 09:00 and 19:00 Tunisia time: it picks the next approved reel (alternating ayah/tasbih), hosts it on GitHub Pages, and publishes it through the Instagram API.

Turn automation off by setting `"enabled": false` in `state/config.json`.

## Secrets (repo Settings, then Secrets and variables, then Actions)
- `IG_USER_ID`: Instagram professional account id
- `IG_ACCESS_TOKEN`: long-lived Instagram token (Instagram API with Instagram Login)

## Sources
Quran text and translation (Sahih International) from api.quran.com. Recitations from everyayah.com. Fonts: Amiri, Amiri Quran, Lora (SIL OFL).
