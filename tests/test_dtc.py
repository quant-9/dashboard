"""Tests for DTC market-data price extraction."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sierra_dtc import (  # noqa: E402
    MARKET_DATA_SNAPSHOT,
    MARKET_DATA_UPDATE_LAST_TRADE_SNAPSHOT,
    MARKET_DATA_UPDATE_TRADE,
    MARKET_DATA_UPDATE_TRADE_COMPACT,
    extract_price,
)

# DTC bid/ask update type (not one we treat as a last-trade price).
MARKET_DATA_UPDATE_BID_ASK = 108


def test_extract_from_trade_update():
    msg = {"Type": MARKET_DATA_UPDATE_TRADE, "SymbolID": 1, "Price": 21507.25, "Volume": 2}
    assert extract_price(msg) == 21507.25


def test_extract_from_trade_compact():
    msg = {"Type": MARKET_DATA_UPDATE_TRADE_COMPACT, "SymbolID": 1, "Price": 21503.0}
    assert extract_price(msg) == 21503.0


def test_extract_from_snapshot_last_trade_price():
    msg = {"Type": MARKET_DATA_SNAPSHOT, "SymbolID": 1, "LastTradePrice": 21499.75, "BidPrice": 21499.5}
    assert extract_price(msg) == 21499.75


def test_extract_from_last_trade_snapshot():
    msg = {"Type": MARKET_DATA_UPDATE_LAST_TRADE_SNAPSHOT, "SymbolID": 1, "LastTradePrice": 21510.0}
    assert extract_price(msg) == 21510.0


def test_bid_ask_update_has_no_last_trade():
    msg = {"Type": MARKET_DATA_UPDATE_BID_ASK, "SymbolID": 1, "BidPrice": 21499.5, "AskPrice": 21500.0}
    assert extract_price(msg) is None


def test_heartbeat_returns_none():
    assert extract_price({"Type": 3}) is None


def test_zero_and_sentinel_treated_as_no_value():
    assert extract_price({"Type": MARKET_DATA_UPDATE_TRADE, "Price": 0}) is None
    assert extract_price({"Type": MARKET_DATA_UPDATE_TRADE, "Price": 1e308}) is None


def test_non_numeric_price_returns_none():
    assert extract_price({"Type": MARKET_DATA_UPDATE_TRADE, "Price": "n/a"}) is None
