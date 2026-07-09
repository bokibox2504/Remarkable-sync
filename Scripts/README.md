# remarkable-sync

Automatski sinhronizuje Google Calendar sa reMarkable Paper Pro Move, svakog jutra, bez desktopa.

## Podešavanje (jednom)

1. Dodaj dva GitHub Secret-a u ovaj repo (Settings → Secrets and variables → Actions → New repository secret):
   - `ICS_URL` — Google Calendar "Secret address in iCal format"
   - `RMAPI_CONFIG` — sadržaj `rmapi.conf` fajla dobijen nakon pairing-a (vidi ispod)

2. Da dobiješ `RMAPI_CONFIG`:
   - Na telefonu/računaru instaliraj rmapi lokalno JEDNOM (ili koristi Codespaces/Actions da to uradiš), pokreni `rmapi` i uđi na link koji ti da (my.remarkable.com/device/browser/connect), unesi kod
   - Nakon uspješnog pairing-a, otvori `~/.config/rmapi/rmapi.conf` i kopiraj cijeli sadržaj kao `RMAPI_CONFIG` secret

3. Workflow se pokreće automatski svako jutro u 6:30 (Belgrade). Može se pokrenuti i ručno: Actions tab → "Sync Google Calendar to reMarkable" → Run workflow.

## Fajlovi

- `scripts/generate_schedule.py` — generiše PDF raspored iz ICS feed-a
- `.github/workflows/sync.yml` — cron automatizacija
