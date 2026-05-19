"""
api.py — Exchange API wrapper (Binance + Kraken via ccxt)
Rewritten from BTC-E (2017, defunct) to modern exchanges.
"""
import os
import logging

try:
    import ccxt
except ImportError:
    raise ImportError("Run: pip install ccxt")

log = logging.getLogger("tAPIbot.api")

SUPPORTED = {"binance": ccxt.binance, "kraken": ccxt.kraken}


def build_exchange(name=None):
    """Build and return an authenticated ccxt exchange instance."""
    name = (name or os.getenv("EXCHANGE", "binance")).lower()
    if name not in SUPPORTED:
        raise ValueError(f"Unsupported exchange '{name}'. Choose: {list(SUPPORTED)}")
    cls = SUPPORTED[name]
    exchange = cls({
        "apiKey":          os.getenv(f"{name.upper()}_API_KEY", ""),
        "secret":          os.getenv(f"{name.upper()}_API_SECRET", ""),
        "enableRateLimit": True,
    })
    log.info(f"Exchange initialised: {exchange.id}")
    return exchange


class PublicAPI:
    """Read-only market data."""

    def __init__(self, exchange=None):
        self.ex = exchange or build_exchange()

    def ticker(self, symbol):
        t = self.ex.fetch_ticker(symbol)
        return {"symbol": symbol, "bid": t["bid"], "ask": t["ask"],
                "last": t["last"], "high": t["high"], "low": t["low"],
                "volume": t["quoteVolume"], "ts": t["datetime"]}

    def order_book(self, symbol, limit=20):
        ob = self.ex.fetch_order_book(symbol, limit)
        return {"bids": ob["bids"], "asks": ob["asks"]}

    def recent_trades(self, symbol, limit=100):
        return self.ex.fetch_trades(symbol, limit=limit)


class TradeAPI:
    """Authenticated trading + account endpoints. Read-only by default."""

    def __init__(self, exchange=None, readonly=True):
        self.ex       = exchange or build_exchange()
        self.readonly = readonly

    def balance(self):
        raw = self.ex.fetch_balance()
        return {k: v for k, v in raw.get("total", {}).items() if v and v > 0}

    def open_orders(self, symbol=None):
        return self.ex.fetch_open_orders(symbol)

    def order_history(self, symbol, limit=50):
        try:
            return self.ex.fetch_closed_orders(symbol, limit=limit)
        except ccxt.NotSupported:
            return []

    def place_order(self, symbol, side, amount, price=None):
        if self.readonly:
            log.warning("place_order called in readonly mode — skipped")
            return {"skipped": True, "reason": "readonly"}
        order_type = "limit" if price else "market"
        log.info(f"Placing {order_type} {side} {amount} {symbol} @ {price}")
        return self.ex.create_order(symbol, order_type, side, amount, price)

    def cancel_order(self, order_id, symbol):
        if self.readonly:
            return {"skipped": True}
        return self.ex.cancel_order(order_id, symbol)
