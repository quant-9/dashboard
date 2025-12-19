from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

plt.style.use("dark_background")
BG_COLOR = "#050608"
GRID_COLOR = "#303540"
EQUITY_COLOR = "#00ff7f"
DD_COLOR = "#ff4b4b"


def _style_axes(ax) -> None:
    ax.set_facecolor(BG_COLOR)
    ax.grid(True, color=GRID_COLOR, alpha=0.4, linestyle="--", linewidth=0.5)
    for spine in ax.spines.values():
        spine.set_color(GRID_COLOR)


def equity_curve(equity: pd.Series) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 4))
    equity.plot(ax=ax, color=EQUITY_COLOR, lw=2)
    ax.set_title("Equity Curve")
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity")
    _style_axes(ax)
    return fig


def drawdown_curve(equity: pd.Series) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8, 3))
    dd = (equity - equity.cummax()) / equity.cummax()
    dd.plot(ax=ax, color=DD_COLOR, lw=1.5)
    ax.set_title("Drawdown (Underwater)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Drawdown")
    _style_axes(ax)
    return fig


def pnl_histogram(pnl: pd.Series) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.histplot(pnl, bins=30, kde=True, ax=ax, color="#00bcd4")
    ax.set_title("PnL Distribution")
    ax.set_xlabel("PnL")
    _style_axes(ax)
    return fig


def mfe_mae_scatter(mfe: pd.Series, mae: pd.Series) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(6, 4))
    sns.scatterplot(x=mae, y=mfe, ax=ax, color="#fcb900")
    ax.set_title("MFE vs MAE")
    ax.set_xlabel("MAE")
    ax.set_ylabel("MFE")
    ax.axhline(0, color=GRID_COLOR, lw=0.8)
    ax.axvline(0, color=GRID_COLOR, lw=0.8)
    _style_axes(ax)
    return fig