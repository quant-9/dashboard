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
class FeeConfig:
    """Fee configuration per instrument (roundtrip cost per contract)"""
    mnq_fee: float = 1.00  # $0.50 entry + $0.50 exit
    mes_fee: float = 1.00
    mgc_fee: float = 1.00
    nq_fee: float = 1.75   # E-mini NQ
    es_fee: float = 2.50   # E-mini S&P
    gc_fee: float = 2.50   # E-mini Gold
    default_fee: float = 1.50  # Fallback for unknown instruments
    
    def get_fee(self, instrument: str) -> float:
        """Get the roundtrip fee per contract for a given instrument."""
        fee_map = {
            "MNQ": self.mnq_fee,
            "MES": self.mes_fee,
            "MGC": self.mgc_fee,
            "NQ": self.nq_fee,
            "ES": self.es_fee,
            "GC": self.gc_fee,
        }
        return fee_map.get(instrument.upper(), self.default_fee)


@dataclass
class AppSettings:
    starting_equity: float = 100000.0
    risk_free_rate: float = 0.0
    fees: FeeConfig = None
    
    def __post_init__(self):
        if self.fees is None:
            self.fees = FeeConfig()