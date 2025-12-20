from __future__ import annotations

import numpy as np
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MetricsEngine:
    def __init__(self, risk_free_rate: float = 0.0) -> None:
        """Initialize metrics engine with risk-free rate.
        
        Args:
            risk_free_rate: Annual risk-free rate for Sharpe/Sortino calculations
        """
        self.risk_free = risk_free_rate

    def _ensure_series(self, pnl: pd.Series) -> pd.Series:
        if not isinstance(pnl, pd.Series):
            pnl = pd.Series(pnl)
        return pnl.dropna().astype(float)

    def expectancy(self, pnl: pd.Series) -> float:
        series = self._ensure_series(pnl)
        if len(series) == 0:
            return 0.0
        return series.mean()

    def profit_factor(self, pnl: pd.Series) -> float:
        series = self._ensure_series(pnl)
        gains = series[series > 0].sum()
        losses = -series[series < 0].sum()
        
        if losses == 0:
            result = np.inf if gains > 0 else np.nan
            if np.isinf(result):
                logger.debug("Profit factor is infinite (no losses)")
            return result
        return gains / losses

    def sharpe(self, returns: pd.Series, trading_days: int = None) -> float:
        series = self._ensure_series(returns)
        if len(series) < 2:
            return np.nan
            
        if series.std(ddof=1) == 0:
            return np.nan
        
        excess = series - self.risk_free / 252
        sharpe_ratio = excess.mean() / excess.std(ddof=1)
        
        if trading_days is not None and trading_days > 0:
            annualization_factor = np.sqrt(trading_days)
            return sharpe_ratio * annualization_factor
        
        return sharpe_ratio

    def sortino(self, returns: pd.Series, trading_days: int = None) -> float:
        series = self._ensure_series(returns)
        if len(series) < 2:
            return np.nan
            
        downside = series[series < 0]
        if len(downside) == 0 or downside.std(ddof=1) == 0:
            return np.nan
        
        excess = series - self.risk_free / 252
        sortino_ratio = excess.mean() / downside.std(ddof=1)
        
        if trading_days is not None and trading_days > 0:
            annualization_factor = np.sqrt(trading_days)
            return sortino_ratio * annualization_factor
        
        return sortino_ratio

    def max_drawdown_equity(self, equity: pd.Series) -> float:
        equity = self._ensure_series(equity)
        if len(equity) == 0:
            return 0.0
            
        peaks = equity.cummax()
        drawdowns = (equity - peaks) / peaks
        return drawdowns.min() if len(drawdowns) > 0 else 0.0

    def calmar_ratio(self, equity: pd.Series, trading_days: int) -> float:
        if len(equity) < 2 or trading_days == 0:
            return np.nan
            
        total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
        ann_return = total_return * (252 / trading_days)
        
        max_dd = abs(self.max_drawdown_equity(equity))
        
        if max_dd == 0:
            return np.inf if ann_return > 0 else np.nan
        
        return ann_return / max_dd

    def recovery_factor(self, equity: pd.Series) -> float:
        equity = self._ensure_series(equity)
        if len(equity) < 2:
            return np.nan
            
        total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
        max_dd = abs(self.max_drawdown_equity(equity))
        
        if max_dd == 0:
            return np.inf if total_return > 0 else np.nan
        
        return total_return / max_dd

    def annualized_return_vol(self, returns: pd.Series, trading_days: int) -> tuple[float, float]:
        series = self._ensure_series(returns)
        if len(series) == 0 or trading_days == 0:
            return 0.0, 0.0
        
        total_return = series.sum()
        ann_return = total_return * (252 / trading_days)
        ann_vol = series.std(ddof=1) * np.sqrt(252 / trading_days)
        
        return ann_return, ann_vol

    def rolling_metric(self, series: pd.Series, window: int, fn) -> pd.Series:
        series = self._ensure_series(series)
        return series.rolling(window=window).apply(fn, raw=False)

    def risk_distribution(self, pnl: pd.Series) -> dict:
        series = self._ensure_series(pnl)
        if len(series) < 2:
            return {
                "skew": np.nan,
                "kurtosis": np.nan,
                "var_95": np.nan,
                "cvar_95": np.nan,
            }
        return {
            "skew": series.skew(),
            "kurtosis": series.kurtosis(),
            "var_95": np.percentile(series, 5),
            "cvar_95": series[series <= np.percentile(series, 5)].mean(),
        }

    def win_rate(self, pnl: pd.Series) -> float:
        series = self._ensure_series(pnl)
        if len(series) == 0:
            return 0.0
        return (series > 0).sum() / len(series)

    def avg_win_loss(self, pnl: pd.Series) -> tuple[float, float]:
        series = self._ensure_series(pnl)
        wins = series[series > 0]
        losses = series[series < 0]
        
        avg_win = wins.mean() if len(wins) > 0 else 0.0
        avg_loss = losses.mean() if len(losses) > 0 else 0.0
        
        return avg_win, avg_loss