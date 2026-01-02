from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time
from typing import Optional


@dataclass
class SessionRecord:
    session_id: Optional[int]
    trade_date: date
    start_time: Optional[time]
    end_time: Optional[time]
    instrument: str
    direction: str  # "Long" or "Short"
    contracts: int
    entry_price: float
    stop_points: float
    trim1_points: float
    trim2_points: float
    market_regime: Optional[str]
    notes: Optional[str]
    gross_pnl: float
    net_pnl: float
    max_drawdown: float
    mfe: float
    mae: float
    trades: int
    wins: int
    losses: int
    breakeven_trades: int
    win_rate: float
    avg_risk: float
    avg_reward: float
    rr_ratio: float
    trim1_hit: bool
    trim2_hit: bool
    largest_win: float
    largest_loss: float


@dataclass
class DerivedMetrics:
    session_id: int
    expectancy: float
    profit_factor: float
    sharpe: Optional[float]
    sortino: Optional[float]
    calmar: Optional[float]
    recovery_factor: Optional[float]
    ann_return: Optional[float]
    ann_vol: Optional[float]
    rolling_sharpe: Optional[float] = None
    rolling_win_rate: Optional[float] = None
    rolling_expectancy: Optional[float] = None


@dataclass
class TradeSummary:
    session_id: int
    pnl: float
    mfe: float
    mae: float
    timestamp: Optional[str] = None


@dataclass
class AppSettings:
    starting_equity: float = 100000.0
    risk_free_rate: float = 0.0