# NQ Price Alerts → Telegram

A tiny always-on service that watches the **live NQ price from Sierra Chart** and
sends a **Telegram** message to your phone when price comes within a few points of a
level you care about.

The whole point: **no trading app on your phone.** When you're out running errands or
in the garden, you get a plain heads-up — "NQ is near your level" — and *you* decide
whether it's worth heading back to your desk to take the trade. There's nothing to
click-to-trade here, so there's no temptation to gamble from your pocket.

You manage everything **from your phone**, by texting the bot:

```
/alert 21500        → alert me when NQ is within 20 pts of 21500
/alert 21500 15     → …within 15 pts instead
/alert 21500 10 once→ …fire once, then delete itself
/list               → show my alerts + how far price is from each
/remove 3           → delete alert #3
/clear              → delete all alerts
/price              → what's NQ right now?
/status             → is Sierra Chart connected? bot health
/help               → command list
```

## How it works

```
Sierra Chart (DTC server)  →  price stream  →  alert engine  →  Telegram  →  your phone
        (your desk, 24/7)                     (within N pts?)
```

One Python process runs on the same desk machine as Sierra Chart. It connects to
Sierra Chart's built-in **DTC protocol server**, streams the last NQ trade price, and
compares it against the alerts you've set. When price enters the band it messages you.
An alert won't spam you: after it fires it stays quiet until price leaves the band or a
cooldown passes.

## Setup

### 1. Install

Requires Python 3.11+.

```bash
pip install -r requirements.txt
cp .env.example .env      # then edit .env (see below)
```

### 2. Create your Telegram bot

1. In Telegram, message **@BotFather** → `/newbot` → follow the prompts.
2. Copy the **bot token** it gives you into `.env` as `TELEGRAM_BOT_TOKEN`.
3. Send your new bot any message (e.g. `/status`). It will reply with **your chat id**.
   Put that number into `.env` as `TELEGRAM_ALLOWED_CHAT_IDS`. The bot ignores everyone
   whose chat id isn't in that list, so only you can control it.

### 3. Enable the DTC server in Sierra Chart

1. In Sierra Chart: **Global Settings → Data/Trade Service Settings** (the DTC Protocol
   Server settings).
2. Turn the **DTC Protocol Server on**, set **Encoding = JSON**, and note the
   **listening port** (default `11099`).
3. Put the host/port into `.env` (`DTC_HOST`, `DTC_PORT`). If your server requires a
   username/password, set `DTC_USERNAME` / `DTC_PASSWORD`.
4. Set `DTC_SYMBOL` to the **exact** symbol string your data feed uses for the NQ chart
   (e.g. `NQZ25-CME`). If you're unsure, `/status` and `/price` will tell you whether the
   symbol is streaming; adjust and restart if needed.

> You chart NQ but execute on MNQ — that's fine. These are price alerts on NQ only;
> the bot never places or touches an order.

### 4. Run it

**Test first, without Sierra Chart** (synthetic prices, proves the phone side works):

```bash
python main.py --simulate
```

Then from Telegram: `/alert <somewhere near the simulated 21500>`, and watch the
notification arrive as the random-walk price crosses your band. `/price`, `/list`,
`/status` all work in this mode too.

**Live** (on the desk machine, with Sierra Chart running and DTC enabled):

```bash
python main.py
```

`/status` should show the DTC source **connected** and `/price` should return the real
NQ last price. Set a `/alert` near the current price to confirm end-to-end.

Leave it running 24/7 next to Sierra Chart (e.g. minimized, or as a Windows service /
scheduled task). Your alerts persist in a local SQLite file (`DATABASE_PATH`), so they
survive restarts.

## Configuration reference (`.env`)

| Variable | Meaning | Default |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather | — (required) |
| `TELEGRAM_ALLOWED_CHAT_IDS` | Your chat id(s), comma-separated | — (required) |
| `DTC_HOST` / `DTC_PORT` | Sierra Chart DTC server address | `127.0.0.1` / `11099` |
| `DTC_USERNAME` / `DTC_PASSWORD` | DTC login, if your server needs one | empty |
| `DTC_SYMBOL` | Exact Sierra Chart symbol for NQ | — (required live) |
| `DEFAULT_THRESHOLD` | Default alert proximity, in points | `20` |
| `COOLDOWN_SECONDS` | Quiet period after an alert fires | `900` |
| `HYSTERESIS` | Extra points price must clear to re-arm | `5` |
| `DATABASE_PATH` | SQLite file for stored alerts | `nq_alerts.db` |

## Tests

```bash
python -m pytest
```

Covers the alert firing / cooldown / re-arm logic and the DTC price parsing — all
deterministic, no network or Sierra Chart needed.

## Files

- `main.py` — wires the price source → alert engine → Telegram bot.
- `sierra_dtc.py` — DTC protocol client + the `--simulate` price source.
- `alerts.py` — SQLite store + the fire/cooldown/hysteresis engine.
- `telegram_bot.py` — the bot commands and notifications.
- `config.py`, `models.py` — settings loading and core data types.
- `tests/` — unit tests.
