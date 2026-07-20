# Signal

Telegram bot that tracks crypto symbols and alerts on large price moves.

## Layout

```
src/signal_bot/
  core/       models, symbol rules, ports, threshold monitor
  storage/    json file database and repositories
  feeds/      binance price feed
  bot/        telegram view, handlers, application
```

Two conventions hold the layout together:

- `core` imports nothing outside the standard library; every other package is an
  adapter around it.
- Each domain boundary gets a `Protocol` in `core/protocols.py`, and every adapter
  subclasses its protocol explicitly, so conformance is checked rather than assumed.

## Run

```bash
python -m venv .venv
.venv/Scripts/activate
pip install -e ".[dev]"
cp .env.example .env
signal-bot
```

## Checks

```bash
ruff check src
ruff format --check src
mypy src
```

## Commands

| Command | Description |
| --- | --- |
| `/add BTC` | watch a coin (±15%, or ±10% for BTC and ETH) |
| `/add BTC 5` | watch a coin with a custom ±5% threshold |
| `/list` | show tracked coins, tap ❌ to remove |
| `/remove BTC` | stop watching a coin |
| `/help` | usage |

Thresholds are measured from the price at the last alert, not over a fixed
window: once an alert fires, counting restarts from that price.

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `SIGNAL_BOT_TOKEN` | — | bot token from @BotFather, required |
| `SIGNAL_DATA_FILE` | `data/signal.json` | local state file |
| `SIGNAL_CHECK_INTERVAL_SECONDS` | `900` | how often prices are polled |
| `SIGNAL_BINANCE_BASE_URL` | `https://api.binance.com` | price source |
