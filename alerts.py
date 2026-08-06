"""Alert storage (SQLite) and the evaluation engine (cooldown + hysteresis)."""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass
from typing import Optional

from models import Alert, PriceTick


@dataclass(frozen=True)
class Evaluation:
    """Pure decision for a single alert against a price at a point in time."""

    fire: bool
    new_triggered: bool


def evaluate_alert(
    alert: Alert,
    price: float,
    now: float,
    cooldown: float,
    hysteresis: float,
) -> Evaluation:
    """Decide whether ``alert`` should fire at ``price``/``now`` and its next armed state.

    Rules:
    - Fires when price is within ``threshold`` points of the target AND the alert
      is either freshly armed (not yet triggered) or its ``cooldown`` has elapsed
      since the last notification.
    - Re-arms (``triggered`` -> False) only once price leaves the band by more than
      ``hysteresis`` points, so hovering at the boundary doesn't flap.
    """
    if alert.in_band(price):
        if not alert.triggered:
            return Evaluation(fire=True, new_triggered=True)
        if alert.last_fired is not None and (now - alert.last_fired) >= cooldown:
            return Evaluation(fire=True, new_triggered=True)
        return Evaluation(fire=False, new_triggered=True)

    # Out of band: re-arm only when clearly outside (past the hysteresis margin).
    if alert.distance(price) > alert.threshold + hysteresis:
        return Evaluation(fire=False, new_triggered=False)
    return Evaluation(fire=False, new_triggered=alert.triggered)


class AlertStore:
    """SQLite-backed persistence for alerts. Safe for single-process async use."""

    def __init__(self, path: str = "nq_alerts.db") -> None:
        # check_same_thread=False so the DB can be touched from the event loop
        # thread; a lock serializes access.
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS alerts (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    target     REAL    NOT NULL,
                    threshold  REAL    NOT NULL,
                    one_shot   INTEGER NOT NULL DEFAULT 0,
                    triggered  INTEGER NOT NULL DEFAULT 0,
                    last_fired REAL
                )
                """
            )
            self._conn.commit()

    @staticmethod
    def _row_to_alert(row: sqlite3.Row) -> Alert:
        return Alert(
            id=row["id"],
            target=row["target"],
            threshold=row["threshold"],
            one_shot=bool(row["one_shot"]),
            triggered=bool(row["triggered"]),
            last_fired=row["last_fired"],
        )

    def add(self, target: float, threshold: float, one_shot: bool = False) -> Alert:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO alerts (target, threshold, one_shot) VALUES (?, ?, ?)",
                (target, threshold, int(one_shot)),
            )
            self._conn.commit()
            alert_id = cur.lastrowid
        return Alert(id=alert_id, target=target, threshold=threshold, one_shot=one_shot)

    def list(self) -> list[Alert]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM alerts ORDER BY id").fetchall()
        return [self._row_to_alert(r) for r in rows]

    def get(self, alert_id: int) -> Optional[Alert]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
        return self._row_to_alert(row) if row else None

    def remove(self, alert_id: int) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM alerts WHERE id = ?", (alert_id,))
            self._conn.commit()
            return cur.rowcount > 0

    def clear(self) -> int:
        with self._lock:
            cur = self._conn.execute("DELETE FROM alerts")
            self._conn.commit()
            return cur.rowcount

    def save_state(self, alert: Alert) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE alerts SET triggered = ?, last_fired = ? WHERE id = ?",
                (int(alert.triggered), alert.last_fired, alert.id),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()


class AlertEngine:
    """Evaluates each price tick against stored alerts and reports what fires."""

    def __init__(self, store: AlertStore, cooldown: float = 900.0, hysteresis: float = 5.0) -> None:
        self.store = store
        self.cooldown = cooldown
        self.hysteresis = hysteresis

    def evaluate(self, tick: PriceTick) -> list[Alert]:
        """Return the alerts that should notify for ``tick`` and persist state changes.

        One-shot alerts that fire are removed from the store. Returned Alert objects
        reflect the state at fire time (useful for building the notification text).
        """
        fired: list[Alert] = []
        for alert in self.store.list():
            decision = evaluate_alert(
                alert, tick.price, tick.timestamp, self.cooldown, self.hysteresis
            )
            state_changed = False
            if decision.fire:
                alert.triggered = True
                alert.last_fired = tick.timestamp
                fired.append(alert)
                state_changed = True
                if alert.one_shot:
                    self.store.remove(alert.id)  # type: ignore[arg-type]
                    continue
            elif alert.triggered != decision.new_triggered:
                alert.triggered = decision.new_triggered
                state_changed = True
            if state_changed:
                self.store.save_state(alert)
        return fired
