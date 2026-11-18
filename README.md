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

## Reel Studio: the console (panel/) on Vercel
A password-protected dashboard: review reels, see what posts next, posted reels with views and likes, workflow runs, and the automation ON/OFF switch.

Deploy (once, about 5 minutes):
1. **GitHub token for the panel:** github.com → Settings → Developer settings → Fine-grained tokens → Generate new token
   - Repository access: *Only select repositories* → `tilawah-sakina`
   - Permissions: **Contents: Read and write**, **Actions: Read and write** (Metadata read-only is added automatically)
   - Expiration: up to 1 year. Copy the token.
2. **vercel.com** → Add New → Project → import `mrint01/tilawah-sakina`
   - **Root Directory: `panel`** (Framework is detected as Vite)
   - Environment Variables:
     - `PANEL_PASSWORD`: the password you will sign in with
     - `SESSION_SECRET`: any long random text (changing it signs every device out)
     - `GITHUB_TOKEN`: the token from step 1
     - `IG_ACCESS_TOKEN`: optional, the Instagram token, for views and likes
   - Deploy. Every push to `main` redeploys it.

Run it locally: `cd panel && npm install`, then `GITHUB_TOKEN=... PANEL_PASSWORD=... npm run dev:api` in one terminal and `npm run dev` in another.

## Daily flow
| UTC | Tunisia | What |
|---|---|---|
| 05:00 | 06:00 | `generate.yml` tops the queue up to `buffer` reels (status *pending*) |
| 06:00 | 07:00 | Claude routine "Tilawah Sakina – review reels" looks at each preview, approves or rejects |
| 08:00 | 09:00 | `post.yml` posts the next approved reel |
| 18:00 | 19:00 | `post.yml` posts the next approved reel |
