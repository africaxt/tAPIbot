"""
trader.py — Arb signal execution engine
Receives signals from Tanulytics (africaxt/bitcoin-arbitrage TanulyticsHook)
and executes buy/sell pairs on Binance or Kraken via ccxt.
"""
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from api import TradeAPI, PublicAPI, build_exchange

log = logging.getLogger("tAPIbot.trader")

SIGNAL_LOG = Path(os.getenv(
    "SIGNAL_LOG",
    str(Path(__file__).parent.parent / "data" / "arb_signals.jsonl"),
))
SIGNAL_LOG.parent.mkdir(parents=True, exist_ok=True)


def _now():
    return datetime.now(timezone.utc).isoformat()


class ArbTrader:
    """
    Executes arbitrage signals emitted by africaxt/bitcoin-arbitrage.

    In readonly mode (default): logs what would be executed without
    placing real orders — safe for paper-testing the signal flow.

    Set READONLY=false and provide real API keys to go live.
    """

    def __init__(self):
        self.symbol     = os.getenv("TRADE_SYMBOL", "BTC/USDT")
        self.min_profit = float(os.getenv("MIN_PROFIT_USD", "5.0"))
        self.max_volume = float(os.getenv("MAX_TRADE_VOLUME_BTC", "0.01"))
        self.readonly   = os.getenv("READONLY", "true").lower() != "false"
        exchange        = build_exchange()
        self.public     = PublicAPI(exchange)
        self.trade      = TradeAPI(exchange, readonly=self.readonly)
        if self.readonly:
            log.info("ArbTrader running in READONLY mode — no orders will be placed")

    def _log_signal(self, signal: dict, outcome: dict):
        entry = {"ts": _now(), "signal": signal, "outcome": outcome}
        with SIGNAL_LOG.open("a") as f:
            f.write(json.dumps(entry) + "\n")

    def execute(self, signal: dict) -> dict:
        """
        Execute a single arbitrage signal.

        signal keys (from TanulyticsHook / Tanulytics webhook):
            profit, volume, buy_exchange, sell_exchange,
            buy_price, sell_price, weighted_buy_price,
            weighted_sell_price, profit_pct
        """
        profit = float(signal.get("profit", 0))
        volume = min(float(signal.get("volume", 0)), self.max_volume)

        if profit < self.min_profit:
            log.debug(f"Signal skipped: profit {profit:.2f} < min {self.min_profit}")
            return {"skipped": True, "reason": "below_min_profit"}

        if volume <= 0:
            log.warning("Signal has zero volume — skipping")
            return {"skipped": True, "reason": "zero_volume"}

        buy_price  = float(signal.get("weighted_buy_price") or signal.get("buy_price", 0))
        sell_price = float(signal.get("weighted_sell_price") or signal.get("sell_price", 0))

        log.info(
            f"Executing arb: buy {volume:.6f} BTC @ {buy_price} "
            f"on {signal.get('buy_exchange')}, "
            f"sell @ {sell_price} on {signal.get('sell_exchange')} "
            f"| est. profit={profit:.2f} USD"
        )

        buy_result  = self.trade.place_order(self.symbol, "buy",  volume, buy_price)
        sell_result = self.trade.place_order(self.symbol, "sell", volume, sell_price)

        outcome = {
            "executed_at": _now(),
            "symbol":      self.symbol,
            "volume":      volume,
            "buy_result":  buy_result,
            "sell_result": sell_result,
            "estimated_profit": profit,
        }
        self._log_signal(signal, outcome)
        return outcome
