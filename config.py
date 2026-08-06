"""Configuration loaded from environment / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dotenv is optional at import time
    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return False


@dataclass
class Config:
    telegram_bot_token: str
    allowed_chat_ids: set[int]
    dtc_host: str
    dtc_port: int
    dtc_username: str
    dtc_password: str
    dtc_symbol: str
    default_threshold: float
    cooldown_seconds: float
    hysteresis: float
    database_path: str
    simulate: bool = False

    @classmethod
    def load(cls, *, simulate: bool = False) -> "Config":
        """Load configuration from the environment (and a .env file if present).

        In ``simulate`` mode the DTC symbol/host are not required, but a Telegram
        token and at least one allowed chat id still are.
        """
        load_dotenv()

        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        if not token:
            raise ConfigError("TELEGRAM_BOT_TOKEN is required (create a bot via @BotFather).")

        chat_ids = _parse_chat_ids(os.getenv("TELEGRAM_ALLOWED_CHAT_IDS", ""))
        if not chat_ids:
            raise ConfigError(
                "TELEGRAM_ALLOWED_CHAT_IDS is required so the bot only answers you. "
                "Message your bot, then use /status (or @userinfobot) to find your id."
            )

        symbol = os.getenv("DTC_SYMBOL", "").strip()
        if not simulate and not symbol:
            raise ConfigError("DTC_SYMBOL is required for live mode (the exact Sierra Chart symbol).")

        return cls(
            telegram_bot_token=token,
            allowed_chat_ids=chat_ids,
            dtc_host=os.getenv("DTC_HOST", "127.0.0.1").strip(),
            dtc_port=_parse_int("DTC_PORT", os.getenv("DTC_PORT", "11099")),
            dtc_username=os.getenv("DTC_USERNAME", "").strip(),
            dtc_password=os.getenv("DTC_PASSWORD", "").strip(),
            dtc_symbol=symbol or "SIMULATED-NQ",
            default_threshold=_parse_float("DEFAULT_THRESHOLD", os.getenv("DEFAULT_THRESHOLD", "20")),
            cooldown_seconds=_parse_float("COOLDOWN_SECONDS", os.getenv("COOLDOWN_SECONDS", "900")),
            hysteresis=_parse_float("HYSTERESIS", os.getenv("HYSTERESIS", "5")),
            database_path=os.getenv("DATABASE_PATH", "nq_alerts.db").strip() or "nq_alerts.db",
            simulate=simulate,
        )


class ConfigError(Exception):
    """Raised when required configuration is missing or invalid."""


def _parse_chat_ids(raw: str) -> set[int]:
    ids: set[int] = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError as exc:
            raise ConfigError(f"Invalid chat id {part!r} in TELEGRAM_ALLOWED_CHAT_IDS.") from exc
    return ids


def _parse_int(name: str, raw: str) -> int:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}.") from exc


def _parse_float(name: str, raw: str) -> float:
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}.") from exc
