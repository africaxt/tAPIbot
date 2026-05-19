"""
Application.py — tAPIbot entry point
Listens for arbitrage signals from Tanulytics and executes them.
"""
import json
import logging
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent / "config" / ".env")
except ImportError:
    pass

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("tAPIbot")

from trader import ArbTrader

MODE = os.getenv("MODE", "listen").lower()   # listen | dry-run


def run_dry():
    """Execute a synthetic signal to verify the pipeline end-to-end."""
    log.info("Dry-run mode: sending test signal to ArbTrader")
    trader = ArbTrader()
    test_signal = {
        "profit":              12.50,
        "volume":              0.005,
        "buy_exchange":        "KrakenUSD",
        "sell_exchange":       "BitstampUSD",
        "buy_price":           67800.00,
        "sell_price":          67925.00,
        "weighted_buy_price":  67812.50,
        "weighted_sell_price": 67918.75,
        "profit_pct":          0.1543,
    }
    result = trader.execute(test_signal)
    log.info(f"Dry-run result: {json.dumps(result, indent=2)}")


def run_listen():
    """
    Poll for new signals written to the Tanulytics signal log by the
    crypto_arb_fetch.py pipeline and execute each one.

    In a production setup, replace the polling loop with a lightweight
    Flask endpoint (similar to tv_webhook_server.py) so signals are
    processed in real time rather than on a file-poll interval.
    """
    from pathlib import Path
    import time

    signal_log = Path(os.getenv(
        "SIGNAL_LOG",
        str(Path(__file__).parent.parent / "data" / "arb_signals.jsonl"),
    ))
    poll_secs  = int(os.getenv("POLL_INTERVAL_SECONDS", "10"))
    trader     = ArbTrader()
    seen_lines = 0

    log.info(f"tAPIbot listening for signals (poll every {poll_secs}s)")
    log.info(f"Signal log: {signal_log}")
    log.info(f"Exchange:   {trader.trade.ex.id}  readonly={trader.readonly}")

    while True:
        if signal_log.exists():
            with signal_log.open() as f:
                lines = f.readlines()
            new_lines = lines[seen_lines:]
            for line in new_lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry  = json.loads(line)
                    signal = entry.get("signal", entry)
                    result = trader.execute(signal)
                    log.info(f"Executed: {result}")
                except (json.JSONDecodeError, Exception) as e:
                    log.error(f"Failed to process signal line: {e}")
            seen_lines = len(lines)
        time.sleep(poll_secs)


if __name__ == "__main__":
    log.info("tAPIbot starting — africaxt/tAPIbot (Binance + Kraken via ccxt)")
    if MODE == "dry-run":
        run_dry()
    else:
        run_listen()
