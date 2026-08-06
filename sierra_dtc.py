"""Price sources for the alert bot.

`SierraDTCPriceSource` speaks Sierra Chart's DTC protocol to stream the live
last-trade price for a symbol. `SimulatedPriceSource` produces a synthetic
random walk so the whole Telegram/alert pipeline can be exercised without
Sierra Chart or a market connection.

DTC protocol reference: https://dtcprotocol.org/
The initial ENCODING_REQUEST/RESPONSE handshake is always binary; every message
after it is JSON (each JSON object is terminated by a single null byte).
"""

from __future__ import annotations

import abc
import asyncio
import json
import random
import struct
import time
from typing import Awaitable, Callable, Optional

from models import PriceTick

# --- DTC message type constants (subset we use) ---
LOGON_REQUEST = 1
LOGON_RESPONSE = 2
HEARTBEAT = 3
LOGOFF = 5
ENCODING_REQUEST = 6
ENCODING_RESPONSE = 7
MARKET_DATA_REQUEST = 101
MARKET_DATA_REJECT = 103
MARKET_DATA_SNAPSHOT = 104
MARKET_DATA_UPDATE_TRADE = 107
MARKET_DATA_UPDATE_TRADE_COMPACT = 112
MARKET_DATA_UPDATE_LAST_TRADE_SNAPSHOT = 134

# Encodings
JSON_ENCODING = 2

# RequestAction for market data
SUBSCRIBE = 1

# LogonResponse result
LOGON_SUCCESS = 1

PROTOCOL_VERSION = 8

OnTick = Callable[[PriceTick], Awaitable[None] | None]


def extract_price(msg: dict) -> Optional[float]:
    """Return the last-trade price from a decoded DTC market-data message.

    Handles trade updates and snapshots across the field-name variants Sierra
    Chart emits. Returns None for messages that don't carry a last-trade price
    (bid/ask updates, heartbeats, etc.) or when the value is missing/zero.
    """
    mtype = msg.get("Type")
    price = None
    if mtype in (MARKET_DATA_UPDATE_TRADE, MARKET_DATA_UPDATE_TRADE_COMPACT):
        price = msg.get("Price")
    elif mtype in (MARKET_DATA_SNAPSHOT, MARKET_DATA_UPDATE_LAST_TRADE_SNAPSHOT):
        price = msg.get("LastTradePrice", msg.get("Price"))
    if price is None:
        return None
    try:
        value = float(price)
    except (TypeError, ValueError):
        return None
    # DTC uses 0 / a max-double sentinel to mean "no value".
    if value == 0.0 or value >= 1e300:
        return None
    return value


class PriceSource(abc.ABC):
    """Abstract streaming price source."""

    name: str = "price-source"

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self._latest: Optional[PriceTick] = None
        self._connected = False
        self._stop = asyncio.Event()

    @property
    def connected(self) -> bool:
        return self._connected

    def latest(self) -> Optional[PriceTick]:
        return self._latest

    async def stop(self) -> None:
        self._stop.set()

    @abc.abstractmethod
    async def run(self, on_tick: OnTick) -> None:
        """Run forever, calling ``on_tick`` for each new price. Reconnects itself."""

    async def _emit(self, tick: PriceTick, on_tick: OnTick) -> None:
        self._latest = tick
        result = on_tick(tick)
        if asyncio.iscoroutine(result):
            await result


class SimulatedPriceSource(PriceSource):
    """A random-walk price generator for local testing (no network)."""

    name = "simulated"

    def __init__(self, symbol: str, start: float = 21500.0, interval: float = 1.0) -> None:
        super().__init__(symbol)
        self._price = start
        self._interval = interval

    async def run(self, on_tick: OnTick) -> None:
        self._connected = True
        try:
            while not self._stop.is_set():
                self._price += random.uniform(-8, 8)
                tick = PriceTick(symbol=self.symbol, price=round(self._price, 2), timestamp=time.time())
                await self._emit(tick, on_tick)
                try:
                    await asyncio.wait_for(self._stop.wait(), timeout=self._interval)
                except asyncio.TimeoutError:
                    pass
        finally:
            self._connected = False


class SierraDTCPriceSource(PriceSource):
    """Streams the last-trade price for ``symbol`` from Sierra Chart via DTC."""

    name = "sierra-dtc"

    def __init__(
        self,
        symbol: str,
        host: str = "127.0.0.1",
        port: int = 11099,
        username: str = "",
        password: str = "",
        heartbeat_interval: int = 10,
        reconnect_max: float = 30.0,
    ) -> None:
        super().__init__(symbol)
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.heartbeat_interval = heartbeat_interval
        self.reconnect_max = reconnect_max
        self.last_error: Optional[str] = None
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

    async def run(self, on_tick: OnTick) -> None:
        backoff = 1.0
        while not self._stop.is_set():
            try:
                await self._connect_and_stream(on_tick)
                backoff = 1.0  # reset after a clean session
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - surface any failure and retry
                self.last_error = f"{type(exc).__name__}: {exc}"
                self._connected = False
            if self._stop.is_set():
                break
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=backoff)
            except asyncio.TimeoutError:
                pass
            backoff = min(backoff * 2, self.reconnect_max)
        await self._close()

    async def _connect_and_stream(self, on_tick: OnTick) -> None:
        self._reader, self._writer = await asyncio.open_connection(self.host, self.port)
        try:
            await self._negotiate_json_encoding()
            await self._logon()
            await self._subscribe()
            self._connected = True
            self.last_error = None
            hb_task = asyncio.create_task(self._heartbeat_loop())
            try:
                await self._read_loop(on_tick)
            finally:
                hb_task.cancel()
        finally:
            self._connected = False
            await self._close()

    # -- handshake --------------------------------------------------------
    async def _negotiate_json_encoding(self) -> None:
        assert self._reader and self._writer
        # Binary ENCODING_REQUEST: Size(u16) Type(u16) ProtocolVersion(i32)
        # Encoding(i32) ProtocolType(char[4]="DTC\0")
        payload = struct.pack("<HHii4s", 16, ENCODING_REQUEST, PROTOCOL_VERSION, JSON_ENCODING, b"DTC\x00")
        self._writer.write(payload)
        await self._writer.drain()
        # Binary ENCODING_RESPONSE is 16 bytes back.
        resp = await asyncio.wait_for(self._reader.readexactly(16), timeout=10)
        _size, mtype, _ver, encoding = struct.unpack("<HHii", resp[:12])
        if mtype != ENCODING_RESPONSE or encoding != JSON_ENCODING:
            raise RuntimeError(f"DTC server did not accept JSON encoding (type={mtype}, encoding={encoding}).")

    async def _logon(self) -> None:
        await self._send_json(
            {
                "Type": LOGON_REQUEST,
                "ProtocolVersion": PROTOCOL_VERSION,
                "Username": self.username,
                "Password": self.password,
                "HeartbeatIntervalInSeconds": self.heartbeat_interval,
                "ClientName": "NQAlertBot",
            }
        )
        while True:
            msg = await asyncio.wait_for(self._read_json(), timeout=15)
            if msg is None:
                raise RuntimeError("Connection closed during logon.")
            if msg.get("Type") == LOGON_RESPONSE:
                if msg.get("Result") != LOGON_SUCCESS:
                    raise RuntimeError(f"DTC logon rejected: {msg.get('ResultText', 'unknown reason')}")
                return

    async def _subscribe(self) -> None:
        await self._send_json(
            {
                "Type": MARKET_DATA_REQUEST,
                "RequestAction": SUBSCRIBE,
                "SymbolID": 1,
                "Symbol": self.symbol,
                "Exchange": "",
            }
        )

    # -- loops ------------------------------------------------------------
    async def _heartbeat_loop(self) -> None:
        while True:
            await asyncio.sleep(self.heartbeat_interval)
            try:
                await self._send_json({"Type": HEARTBEAT})
            except (ConnectionError, RuntimeError):
                return

    async def _read_loop(self, on_tick: OnTick) -> None:
        while not self._stop.is_set():
            msg = await self._read_json()
            if msg is None:
                raise ConnectionError("DTC connection closed by server.")
            mtype = msg.get("Type")
            if mtype == HEARTBEAT:
                continue
            if mtype == MARKET_DATA_REJECT:
                raise RuntimeError(f"Market data request rejected: {msg.get('RejectText', '')}")
            if mtype == LOGOFF:
                raise ConnectionError(f"DTC logoff: {msg.get('Reason', '')}")
            price = extract_price(msg)
            if price is not None:
                await self._emit(
                    PriceTick(symbol=self.symbol, price=price, timestamp=time.time()), on_tick
                )

    # -- framing ----------------------------------------------------------
    async def _send_json(self, obj: dict) -> None:
        if not self._writer:
            raise RuntimeError("Not connected.")
        self._writer.write(json.dumps(obj).encode("utf-8") + b"\x00")
        await self._writer.drain()

    async def _read_json(self) -> Optional[dict]:
        if not self._reader:
            return None
        try:
            raw = await self._reader.readuntil(b"\x00")
        except asyncio.IncompleteReadError:
            return None
        text = raw[:-1].decode("utf-8", errors="replace").strip()
        if not text:
            return {}
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    async def _close(self) -> None:
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:  # noqa: BLE001
                pass
        self._reader = None
        self._writer = None
