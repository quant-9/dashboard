"""Telegram bot: the phone-side interface for creating and managing alerts."""

from __future__ import annotations

import time
from typing import Optional

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from alerts import AlertStore
from config import Config
from models import Alert
from sierra_dtc import PriceSource

HELP_TEXT = (
    "<b>NQ price alerts</b>\n"
    "I watch the live NQ price and ping you when it comes near a level you set. "
    "No trading here — just a heads-up so you can decide whether to head to your desk.\n\n"
    "<b>Commands</b>\n"
    "/alert &lt;price&gt; [points] [once] — set an alert (e.g. <code>/alert 21500</code> or "
    "<code>/alert 21500 15</code>). Add <code>once</code> to auto-remove after it fires.\n"
    "/list — show your active alerts\n"
    "/remove &lt;id&gt; — delete one alert\n"
    "/clear — delete all alerts\n"
    "/price — current NQ price\n"
    "/status — connection + health\n"
    "/help — this message"
)


class AlertBot:
    """Wraps a python-telegram-bot Application with alert commands + a notifier."""

    def __init__(self, config: Config, store: AlertStore, price_source: PriceSource) -> None:
        self.config = config
        self.store = store
        self.price_source = price_source
        self.app: Application = Application.builder().token(config.telegram_bot_token).build()
        self._register()

    def _register(self) -> None:
        h = self.app.add_handler
        h(CommandHandler(["start", "help"], self.cmd_help))
        h(CommandHandler("alert", self.cmd_alert))
        h(CommandHandler("list", self.cmd_list))
        h(CommandHandler("remove", self.cmd_remove))
        h(CommandHandler("clear", self.cmd_clear))
        h(CommandHandler("price", self.cmd_price))
        h(CommandHandler("status", self.cmd_status))

    # -- authorization ----------------------------------------------------
    def _authorized(self, update: Update) -> bool:
        chat = update.effective_chat
        return chat is not None and chat.id in self.config.allowed_chat_ids

    async def _reject(self, update: Update) -> None:
        chat = update.effective_chat
        chat_id = chat.id if chat else "unknown"
        await update.effective_message.reply_text(
            f"⛔ Not authorized. Your chat id is {chat_id}. "
            "Add it to TELEGRAM_ALLOWED_CHAT_IDS if this is your bot."
        )

    # -- commands ---------------------------------------------------------
    async def cmd_help(self, update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        await update.effective_message.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML)

    async def cmd_alert(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        args = ctx.args or []
        if not args:
            await update.effective_message.reply_text(
                "Usage: /alert <price> [points] [once]\nExample: /alert 21500 15"
            )
            return
        try:
            target = float(args[0])
        except ValueError:
            await update.effective_message.reply_text(f"'{args[0]}' isn't a number. Try /alert 21500")
            return

        threshold = self.config.default_threshold
        one_shot = False
        for extra in args[1:]:
            if extra.lower() in ("once", "oneshot", "one-shot"):
                one_shot = True
                continue
            try:
                threshold = float(extra)
            except ValueError:
                await update.effective_message.reply_text(
                    f"Didn't understand '{extra}'. Usage: /alert <price> [points] [once]"
                )
                return
        if threshold <= 0:
            await update.effective_message.reply_text("Threshold (points) must be greater than 0.")
            return

        alert = self.store.add(target=target, threshold=threshold, one_shot=one_shot)
        suffix = ", one-shot" if one_shot else ""
        line = (
            f"✅ Alert #{alert.id} set: NQ within {threshold:g} pts of "
            f"{target:g}{suffix}."
        )
        latest = self.price_source.latest()
        if latest is not None:
            line += f"\nCurrent price {latest.price:g} ({alert.distance(latest.price):g} pts away)."
        await update.effective_message.reply_text(line)

    async def cmd_list(self, update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        alerts = self.store.list()
        if not alerts:
            await update.effective_message.reply_text("No active alerts. Set one with /alert <price>.")
            return
        latest = self.price_source.latest()
        lines = ["<b>Active alerts</b>"]
        for a in alerts:
            parts = [f"#{a.id}: {a.target:g} ±{a.threshold:g}"]
            if a.one_shot:
                parts.append("(once)")
            if latest is not None:
                parts.append(f"— {a.distance(latest.price):g} pts away")
            if a.triggered:
                parts.append("\U0001f515 in-band")
            lines.append(" ".join(parts))
        if latest is not None:
            lines.append(f"\nCurrent NQ: {latest.price:g}")
        await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    async def cmd_remove(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        args = ctx.args or []
        if not args:
            await update.effective_message.reply_text("Usage: /remove <id>  (see /list for ids)")
            return
        try:
            alert_id = int(args[0])
        except ValueError:
            await update.effective_message.reply_text(f"'{args[0]}' isn't a valid id.")
            return
        if self.store.remove(alert_id):
            await update.effective_message.reply_text(f"\U0001f5d1 Removed alert #{alert_id}.")
        else:
            await update.effective_message.reply_text(f"No alert #{alert_id}.")

    async def cmd_clear(self, update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        count = self.store.clear()
        await update.effective_message.reply_text(f"Cleared {count} alert(s).")

    async def cmd_price(self, update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        latest = self.price_source.latest()
        if latest is None:
            state = "connected, waiting for first tick" if self.price_source.connected else "not connected"
            await update.effective_message.reply_text(f"No price yet ({state}).")
            return
        age = max(0, int(time.time() - latest.timestamp))
        await update.effective_message.reply_text(
            f"NQ {latest.price:g}  ({age}s ago, {latest.symbol})"
        )

    async def cmd_status(self, update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
        if not self._authorized(update):
            return await self._reject(update)
        latest = self.price_source.latest()
        conn_state = "\U0001f7e2 connected" if self.price_source.connected else "\U0001f534 down"
        lines = [
            "<b>Status</b>",
            f"Source: {self.price_source.name} ({conn_state})",
            f"Symbol: {self.price_source.symbol}",
        ]
        if latest is not None:
            age = max(0, int(time.time() - latest.timestamp))
            lines.append(f"Last price: {latest.price:g} ({age}s ago)")
        else:
            lines.append("Last price: none yet")
        last_error = getattr(self.price_source, "last_error", None)
        if last_error and not self.price_source.connected:
            lines.append(f"Last error: {last_error}")
        lines.append(f"Active alerts: {len(self.store.list())}")
        chat = update.effective_chat
        lines.append(f"Your chat id: {chat.id if chat else 'unknown'}")
        await update.effective_message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)

    # -- notifications ----------------------------------------------------
    async def notify_fired(self, alert: Alert, price: float) -> None:
        distance = alert.distance(price)
        direction = "above" if price >= alert.target else "below"
        text = (
            f"\U0001f514 <b>NQ near {alert.target:g}</b>\n"
            f"Price {price:g} is {distance:g} pts {direction} your level "
            f"(alert #{alert.id}, ±{alert.threshold:g}).\n"
            "Head to your desk if you want this one."
        )
        await self.broadcast(text)

    async def broadcast(self, text: str) -> None:
        for chat_id in self.config.allowed_chat_ids:
            try:
                await self.app.bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
            except Exception:  # noqa: BLE001 - one bad chat shouldn't kill the loop
                continue

    # -- lifecycle --------------------------------------------------------
    async def start(self) -> None:
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)

    async def stop(self) -> None:
        if self.app.updater:
            await self.app.updater.stop()
        await self.app.stop()
        await self.app.shutdown()
