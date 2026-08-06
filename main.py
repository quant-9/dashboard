"""Entry point: wire the price source -> alert engine -> Telegram notifier.

Run live (reads Sierra Chart via DTC):
    python main.py

Run without Sierra Chart (synthetic prices, for testing the bot end-to-end):
    python main.py --simulate
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal

from alerts import AlertEngine, AlertStore
from config import Config, ConfigError
from models import PriceTick
from sierra_dtc import PriceSource, SierraDTCPriceSource, SimulatedPriceSource
from telegram_bot import AlertBot

log = logging.getLogger("nq-alerts")


def build_price_source(config: Config) -> PriceSource:
    if config.simulate:
        return SimulatedPriceSource(symbol=config.dtc_symbol)
    return SierraDTCPriceSource(
        symbol=config.dtc_symbol,
        host=config.dtc_host,
        port=config.dtc_port,
        username=config.dtc_username,
        password=config.dtc_password,
    )


async def run(config: Config) -> None:
    store = AlertStore(config.database_path)
    price_source = build_price_source(config)
    engine = AlertEngine(store, cooldown=config.cooldown_seconds, hysteresis=config.hysteresis)
    bot = AlertBot(config, store, price_source)

    async def on_tick(tick: PriceTick) -> None:
        try:
            for fired in engine.evaluate(tick):
                await bot.notify_fired(fired, tick.price)
        except Exception:  # noqa: BLE001 - never let one tick kill the stream
            log.exception("Error while evaluating tick %s", tick)

    await bot.start()
    log.info("Bot started. Source=%s symbol=%s", price_source.name, config.dtc_symbol)

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop_event.set)
        except NotImplementedError:  # Windows: fall back to KeyboardInterrupt
            pass

    source_task = asyncio.create_task(price_source.run(on_tick))
    try:
        await stop_event.wait()
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        log.info("Shutting down…")
        await price_source.stop()
        source_task.cancel()
        try:
            await source_task
        except (asyncio.CancelledError, Exception):  # noqa: BLE001
            pass
        await bot.stop()
        store.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="NQ price-alert bot (Sierra Chart -> Telegram).")
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Use synthetic prices instead of Sierra Chart (for testing).",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging.")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # Telegram's HTTP library is chatty at INFO; quiet it unless verbose.
    if not args.verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)

    try:
        config = Config.load(simulate=args.simulate)
    except ConfigError as exc:
        raise SystemExit(f"Configuration error: {exc}")

    try:
        asyncio.run(run(config))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
