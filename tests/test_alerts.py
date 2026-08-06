"""Tests for the alert evaluation logic, store, and engine."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alerts import AlertEngine, AlertStore, evaluate_alert  # noqa: E402
from models import Alert, PriceTick  # noqa: E402

COOLDOWN = 900.0
HYST = 5.0


def make_alert(target=21500.0, threshold=20.0, triggered=False, last_fired=None, one_shot=False):
    return Alert(
        id=1,
        target=target,
        threshold=threshold,
        triggered=triggered,
        last_fired=last_fired,
        one_shot=one_shot,
    )


def test_fires_when_entering_band():
    alert = make_alert()
    ev = evaluate_alert(alert, price=21510, now=1000, cooldown=COOLDOWN, hysteresis=HYST)
    assert ev.fire is True
    assert ev.new_triggered is True


def test_does_not_fire_outside_band():
    alert = make_alert()
    ev = evaluate_alert(alert, price=21450, now=1000, cooldown=COOLDOWN, hysteresis=HYST)
    assert ev.fire is False
    assert ev.new_triggered is False


def test_exactly_on_threshold_edge_fires():
    alert = make_alert(threshold=20)
    ev = evaluate_alert(alert, price=21480, now=1000, cooldown=COOLDOWN, hysteresis=HYST)
    assert ev.fire is True


def test_no_refire_while_resting_in_band_before_cooldown():
    alert = make_alert(triggered=True, last_fired=1000)
    ev = evaluate_alert(alert, price=21505, now=1000 + 60, cooldown=COOLDOWN, hysteresis=HYST)
    assert ev.fire is False
    assert ev.new_triggered is True  # stays armed/in-band


def test_refires_after_cooldown_while_still_in_band():
    alert = make_alert(triggered=True, last_fired=1000)
    ev = evaluate_alert(alert, price=21505, now=1000 + COOLDOWN, cooldown=COOLDOWN, hysteresis=HYST)
    assert ev.fire is True


def test_rearms_only_after_leaving_band_past_hysteresis():
    # Within band+hysteresis: stays triggered (no re-arm, no flapping).
    alert = make_alert(threshold=20, triggered=True, last_fired=1000)
    ev = evaluate_alert(alert, price=21500 + 22, now=2000, cooldown=COOLDOWN, hysteresis=HYST)
    assert ev.new_triggered is True
    # Clearly outside band+hysteresis: re-arm.
    ev2 = evaluate_alert(alert, price=21500 + 30, now=2000, cooldown=COOLDOWN, hysteresis=HYST)
    assert ev2.new_triggered is False


def test_full_cycle_fires_once_then_rearms():
    alert = make_alert(threshold=20)
    # Enter band -> fire
    e1 = evaluate_alert(alert, 21510, now=0, cooldown=COOLDOWN, hysteresis=HYST)
    assert e1.fire
    alert.triggered = e1.new_triggered
    alert.last_fired = 0
    # Still in band, soon after -> no fire
    e2 = evaluate_alert(alert, 21512, now=10, cooldown=COOLDOWN, hysteresis=HYST)
    assert not e2.fire
    alert.triggered = e2.new_triggered
    # Leave band far -> re-arm
    e3 = evaluate_alert(alert, 21600, now=20, cooldown=COOLDOWN, hysteresis=HYST)
    assert not e3.fire
    alert.triggered = e3.new_triggered
    assert alert.triggered is False
    # Re-enter band -> fires again
    e4 = evaluate_alert(alert, 21505, now=30, cooldown=COOLDOWN, hysteresis=HYST)
    assert e4.fire


# --- Store + engine integration (in-memory sqlite) ---

def make_store():
    return AlertStore(":memory:")


def test_store_add_list_remove():
    store = make_store()
    a = store.add(target=21500, threshold=20)
    assert a.id is not None
    assert len(store.list()) == 1
    assert store.remove(a.id) is True
    assert store.list() == []
    assert store.remove(999) is False


def test_engine_fires_and_persists_state():
    store = make_store()
    store.add(target=21500, threshold=20)
    engine = AlertEngine(store, cooldown=COOLDOWN, hysteresis=HYST)

    fired = engine.evaluate(PriceTick("NQ", 21510, timestamp=100))
    assert len(fired) == 1
    # State persisted: now triggered, so an immediate re-eval doesn't re-fire.
    fired2 = engine.evaluate(PriceTick("NQ", 21511, timestamp=110))
    assert fired2 == []
    stored = store.list()[0]
    assert stored.triggered is True
    assert stored.last_fired == 100


def test_engine_one_shot_removes_after_fire():
    store = make_store()
    store.add(target=21500, threshold=20, one_shot=True)
    engine = AlertEngine(store, cooldown=COOLDOWN, hysteresis=HYST)
    fired = engine.evaluate(PriceTick("NQ", 21505, timestamp=100))
    assert len(fired) == 1
    assert store.list() == []  # auto-removed


def test_engine_multiple_alerts_independent():
    store = make_store()
    store.add(target=21500, threshold=10)
    store.add(target=22000, threshold=10)
    engine = AlertEngine(store, cooldown=COOLDOWN, hysteresis=HYST)
    fired = engine.evaluate(PriceTick("NQ", 21505, timestamp=100))
    assert len(fired) == 1
    assert fired[0].target == 21500
