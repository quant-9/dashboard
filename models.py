"""Core data types for the NQ price-alert bot."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PriceTick:
    """A single last-trade price observation from the price source."""

    symbol: str
    price: float
    timestamp: float  # epoch seconds


@dataclass
class Alert:
    """A user-defined price alert.

    Fires when the live price comes within ``threshold`` points of ``target``.
    ``triggered`` / ``last_fired`` track anti-spam state so a resting price in
    the band does not send repeated notifications.
    """

    id: int | None
    target: float
    threshold: float
    one_shot: bool = False
    triggered: bool = False
    last_fired: float | None = None  # epoch seconds of the last notification

    def distance(self, price: float) -> float:
        """Absolute distance in points from ``price`` to this alert's target."""
        return abs(price - self.target)

    def in_band(self, price: float) -> bool:
        """True when ``price`` is within ``threshold`` points of the target."""
        return self.distance(price) <= self.threshold
