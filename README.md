# WorldCupBot

Telegram bot tracking the 2026 World Cup, with extra attention to Switzerland and USA
matches. Built with `python-telegram-bot` (async), `APScheduler`, and `httpx`. Designed
to run as a single long-lived worker process (e.g. on Railway).

## Configuration

All configuration is via environment variables:

| Variable | Required | Default | Description |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | yes | — | Bot token from `@BotFather` |
| `TELEGRAM_CHAT_ID` | yes | — | Chat/channel id to post updates to |
| `WC_API_KEY` | yes | — | API token for football-data.org |
| `DISPLAY_TZ` | no | `Europe/Zurich` | IANA timezone all displayed times and schedules are anchored to |
| `WC_API_BASE_URL` | no | `https://api.football-data.org/v4` | Override for the API base URL |
| `WC_COMPETITION_CODE` | no | `WC` | football-data.org competition code for the World Cup |
| `WC_SEASON` | no | `2026` | Season year passed to football-data.org |
| `WATCHED_TEAMS` | no | `Switzerland,USA` | Comma-separated team names (as returned by API-Football) to track closely |

Copy `.env.example` to `.env` and fill in values for local development.

## Running locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(cat .env | xargs)   # or use a process manager / direnv
python main.py
```

## Deploying on Railway

This repo includes a `Procfile` (`worker: python main.py`). Set the environment
variables above in the Railway project settings; no other setup is required.

## Operating modes

The bot determines its mode once per day (00:05 in the active display timezone)
and whenever `/timezone` changes the active timezone:

- **LIVE** — a Switzerland or USA match is currently in progress. Polls the match
  endpoint every 5 minutes, diffs the score against the last-seen score to post
  goal alerts, and posts a half-time/play-resumed message on status changes.
  Posts a full-time recap and exits live mode when the match finishes.
- **WATCHFUL** — a Switzerland or USA match is scheduled later today. Schedules a
  single pre-match alert 2 minutes before kickoff. No polling.
- **IDLE** — no Switzerland or USA match today. Sends a morning digest at 08:00
  local time and an evening recap 30 minutes after the last match of the day is
  estimated to finish (kickoff + 120 minutes).

## Commands

- `/update` — fetch today's matches in one call and report status/score/scorers
  immediately. No scheduling side effects.
- `/timezone <tz>` — switch the active display timezone (e.g. `America/New_York`).
  Cancels and reschedules all pending jobs against the new timezone; jobs that
  already fired today are not replayed.
- `/timezone` — show the current timezone and local time.

## football-data.org integration notes

The original data source (wc2026api.com) is no longer available. A second
integration attempt used API-Football, but its free tier doesn't include the 2026
season (only 2022–2024) — see git history if reviving that integration is ever
useful. The bot now uses [football-data.org](https://www.football-data.org/) v4,
whose free tier permanently includes the World Cup competition (code `WC`):

- `GET /competitions/WC/matches?dateFrom=...&dateTo=...&season=2026` — matches for
  a given date
- `GET /matches/{id}` — a single match's current status/score
- `GET /competitions/WC/teams?season=2026` — resolve a team name to its numeric id
  (cached in-memory per process)
- `GET /teams/{id}/matches?status=SCHEDULED&competitions=WC&limit=1` — a team's
  next fixture
- Auth via the `X-Auth-Token` header

**Free-tier limitation**: football-data.org's free tier does not expose
goal-scorer or card-level event data (that requires their paid "deep data pack").
As a result, LIVE mode is simplified compared to the original spec:

- Goal alerts are generic ("⚽ GOAL — Switzerland 1–0 USA / 🇨🇭 Switzerland
  scores!"), detected by diffing `home_score`/`away_score` between polls — no
  scorer name or assist.
- Red card alerts are not available and have been removed.
- Half-time/play-resumed messages are inferred from the coarse `status` field
  (`SCHEDULED`, `TIMED`, `IN_PLAY`, `PAUSED`, `FINISHED`, ...) rather than a
  detailed phase code; extra time/penalties aren't distinguished from regular play.

If a paid plan (API-Football Pro, or football-data.org's deep data pack) is added
later to restore scorer/card-level detail, `worldcupbot/api.py` and
`worldcupbot/models.py` are the only places that need to change — the rest of the
bot operates on the `Match`/`Team` dataclasses.
