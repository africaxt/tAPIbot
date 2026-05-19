# tAPIbot — Binance + Kraken Execution Bot

> Rewritten from BTC-E (2017, defunct) to modern exchanges via [ccxt](https://github.com/ccxt/ccxt).
> Part of the [africaxt](https://github.com/africaxt) trading ecosystem.

## Overview

tAPIbot is the **execution layer** of the africaxt signal pipeline:

```
africaxt/bitcoin-arbitrage   →   TanulyticsHook observer
    → POST /crypto-arb-webhook
    → africaxt/Tanulytics (webhook server + aggregator)
    → arb_signals.jsonl
    → tAPIbot (this repo) executes on Binance or Kraken
```

## Quick start

```bash
pip install -r requirements.txt
cp config/.env.example config/.env
# Fill in BINANCE_API_KEY / BINANCE_API_SECRET (or Kraken equivalents)

# Dry run — no real orders, just verifies the signal pipeline
MODE=dry-run python tapi/Application.py

# Live listen mode (reads Tanulytics signal log, executes on every new signal)
SIGNAL_LOG=/path/to/Tanulytics/data/arb_signals.jsonl python tapi/Application.py
```

## Configuration

All config via `config/.env` (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `EXCHANGE` | `binance` | `binance` or `kraken` |
| `BINANCE_API_KEY` | — | Binance API key |
| `BINANCE_API_SECRET` | — | Binance API secret |
| `KRAKEN_API_KEY` | — | Kraken API key |
| `KRAKEN_API_SECRET` | — | Kraken API secret |
| `TRADE_SYMBOL` | `BTC/USDT` | ccxt symbol to trade |
| `READONLY` | `true` | Set `false` to place real orders |
| `MIN_PROFIT_USD` | `5.0` | Minimum profit to execute a signal |
| `MAX_TRADE_VOLUME_BTC` | `0.005` | Maximum BTC per arb leg |
| `SIGNAL_LOG` | `data/arb_signals.jsonl` | Path to Tanulytics signal log |
| `POLL_INTERVAL_SECONDS` | `10` | File-poll interval in listen mode |

## Architecture

```
Application.py         Entry point — listen | dry-run modes
trader.py              ArbTrader: signal validation + order execution
api.py                 PublicAPI + TradeAPI wrappers over ccxt
config/.env.example    Credentials template
```

## Safety

- `READONLY=true` is the default. tAPIbot logs what it *would* execute without placing orders.
- Set `MIN_PROFIT_USD` conservatively — exchange fees eat into arbitrage margins.
- Start with `MAX_TRADE_VOLUME_BTC=0.001` and increase only after live testing.

## Dependencies

```
pip install ccxt python-dotenv
```

---

*For signal generation, see [africaxt/bitcoin-arbitrage](https://github.com/africaxt/bitcoin-arbitrage).  
For portfolio aggregation + reporting, see [africaxt/Tanulytics](https://github.com/africaxt/Tanulytics).*
