from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable, List, Optional
import numpy as np

from models import DerivedMetrics, SessionRecord, TradeSummary, AppSettings


class Database:
    def __init__(self, db_path: Path | str = "trading_dashboard.db") -> None:
        """Initialize database connection and create schema if needed.
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        cur = self.conn.cursor()
        
        # Create tables if they don't exist
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                instrument TEXT NOT NULL,
                direction TEXT DEFAULT 'Long',
                contracts INTEGER DEFAULT 2,
                entry_price REAL DEFAULT 0,
                stop_points REAL DEFAULT 10,
                trim1_points REAL DEFAULT 50,
                trim2_points REAL DEFAULT 100,
                trim1_hit BOOLEAN DEFAULT 0,
                trim2_hit BOOLEAN DEFAULT 0,
                market_regime TEXT,
                notes TEXT,
                gross_pnl REAL NOT NULL,
                net_pnl REAL NOT NULL,
                max_drawdown REAL NOT NULL,
                mfe REAL NOT NULL,
                mae REAL NOT NULL,
                trades INTEGER NOT NULL,
                wins INTEGER NOT NULL,
                losses INTEGER NOT NULL,
                breakeven_trades INTEGER DEFAULT 0,
                win_rate REAL NOT NULL,
                avg_risk REAL NOT NULL,
                avg_reward REAL NOT NULL,
                rr_ratio REAL NOT NULL,
                largest_win REAL NOT NULL,
                largest_loss REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS derived_metrics (
                session_id INTEGER PRIMARY KEY,
                expectancy REAL,
                profit_factor REAL,
                sharpe REAL,
                sortino REAL,
                calmar REAL,
                recovery_factor REAL,
                ann_return REAL,
                ann_vol REAL,
                rolling_sharpe REAL,
                rolling_win_rate REAL,
                rolling_expectancy REAL,
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                pnl REAL NOT NULL,
                mfe REAL,
                mae REAL,
                timestamp TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
            );
            
            CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(trade_date);
            CREATE INDEX IF NOT EXISTS idx_trades_session ON trades(session_id);
            
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value REAL NOT NULL
            );
            """
        )
        
        # Migration: Add new columns if they don't exist (for existing databases)
        cur.execute("PRAGMA table_info(sessions)")
        columns = [row['name'] for row in cur.fetchall()]
        
        new_columns = {
            'direction': "TEXT DEFAULT 'Long'",
            'contracts': "INTEGER DEFAULT 2",
            'entry_price': "REAL DEFAULT 0",
            'stop_points': "REAL DEFAULT 10",
            'trim1_points': "REAL DEFAULT 50",
            'trim2_points': "REAL DEFAULT 100",
            'trim1_hit': "BOOLEAN DEFAULT 0",
            'trim2_hit': "BOOLEAN DEFAULT 0",
            'breakeven_trades': "INTEGER DEFAULT 0"
        }

        # Check for 'trims' column removal or rename. We'll simply ignore the old 'trims' column if present
        # but we must add the new ones.
        for col_name, col_def in new_columns.items():
            if col_name not in columns:
                try:
                    cur.execute(f"ALTER TABLE sessions ADD COLUMN {col_name} {col_def}")
                except sqlite3.OperationalError:
                    pass  # Column might have been added by a parallel process or other means

        self.conn.commit()

    def insert_session(self, record: SessionRecord) -> int:
        cur = self.conn.cursor()
        # Calculate trims for backward compatibility (old DB has NOT NULL on trims)
        trims_count = (1 if record.trim1_hit else 0) + (1 if record.trim2_hit else 0)
        cur.execute(
            """
            INSERT INTO sessions (
                trade_date, start_time, end_time, instrument, direction, contracts,
                entry_price, stop_points, trim1_points, trim2_points, trim1_hit, trim2_hit,
                market_regime, notes, gross_pnl, net_pnl, max_drawdown, mfe, mae, 
                trades, wins, losses, breakeven_trades, win_rate, avg_risk, avg_reward, 
                rr_ratio, trims, largest_win, largest_loss
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.trade_date.isoformat(),
                record.start_time.isoformat() if record.start_time else "",
                record.end_time.isoformat() if record.end_time else "",
                record.instrument,
                record.direction,
                record.contracts,
                record.entry_price,
                record.stop_points,
                record.trim1_points,
                record.trim2_points,
                record.trim1_hit,
                record.trim2_hit,
                record.market_regime,
                record.notes,
                record.gross_pnl,
                record.net_pnl,
                record.max_drawdown,
                record.mfe,
                record.mae,
                record.trades,
                record.wins,
                record.losses,
                record.breakeven_trades,
                record.win_rate,
                record.avg_risk,
                record.avg_reward,
                record.rr_ratio,
                trims_count,
                record.largest_win,
                record.largest_loss,
            ),
        )
        self.conn.commit()
        return cur.lastrowid

    def update_session(self, record: SessionRecord) -> None:
        cur = self.conn.cursor()
        # Calculate trims for backward compatibility
        trims_count = (1 if record.trim1_hit else 0) + (1 if record.trim2_hit else 0)
        cur.execute(
            """
            UPDATE sessions SET
                trade_date=?, start_time=?, end_time=?, instrument=?, direction=?, contracts=?,
                entry_price=?, stop_points=?, trim1_points=?, trim2_points=?, trim1_hit=?, trim2_hit=?,
                market_regime=?, notes=?, gross_pnl=?, net_pnl=?, max_drawdown=?, mfe=?, mae=?, 
                trades=?, wins=?, losses=?, breakeven_trades=?, win_rate=?, avg_risk=?, avg_reward=?, 
                rr_ratio=?, trims=?, largest_win=?, largest_loss=?
            WHERE id=?
            """,
            (
                record.trade_date.isoformat(),
                record.start_time.isoformat() if record.start_time else "",
                record.end_time.isoformat() if record.end_time else "",
                record.instrument,
                record.direction,
                record.contracts,
                record.entry_price,
                record.stop_points,
                record.trim1_points,
                record.trim2_points,
                record.trim1_hit,
                record.trim2_hit,
                record.market_regime,
                record.notes,
                record.gross_pnl,
                record.net_pnl,
                record.max_drawdown,
                record.mfe,
                record.mae,
                record.trades,
                record.wins,
                record.losses,
                record.breakeven_trades,
                record.win_rate,
                record.avg_risk,
                record.avg_reward,
                record.rr_ratio,
                trims_count,
                record.largest_win,
                record.largest_loss,
                record.session_id,
            ),
        )
        self.conn.commit()

    def get_session(self, session_id: int) -> Optional[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
        return cur.fetchone()

    def upsert_derived(self, metrics: DerivedMetrics) -> None:
        cur = self.conn.cursor()
        cur.execute(
            """
            INSERT INTO derived_metrics (
                session_id, expectancy, profit_factor, sharpe, sortino, calmar,
                recovery_factor, ann_return, ann_vol, rolling_sharpe, rolling_win_rate,
                rolling_expectancy
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                expectancy=excluded.expectancy,
                profit_factor=excluded.profit_factor,
                sharpe=excluded.sharpe,
                sortino=excluded.sortino,
                calmar=excluded.calmar,
                recovery_factor=excluded.recovery_factor,
                ann_return=excluded.ann_return,
                ann_vol=excluded.ann_vol,
                rolling_sharpe=excluded.rolling_sharpe,
                rolling_win_rate=excluded.rolling_win_rate,
                rolling_expectancy=excluded.rolling_expectancy
            """,
            (
    metrics.session_id,
    metrics.expectancy if metrics.expectancy is not None else None,
    None if metrics.profit_factor is None or np.isinf(metrics.profit_factor) or np.isnan(metrics.profit_factor) else float(metrics.profit_factor),
    None if metrics.sharpe is None or np.isnan(metrics.sharpe) or np.isinf(metrics.sharpe) else float(metrics.sharpe),
    None if metrics.sortino is None or np.isnan(metrics.sortino) or np.isinf(metrics.sortino) else float(metrics.sortino),
    None if metrics.calmar is None or np.isnan(metrics.calmar) or np.isinf(metrics.calmar) else float(metrics.calmar),
    None if metrics.recovery_factor is None or np.isnan(metrics.recovery_factor) or np.isinf(metrics.recovery_factor) else float(metrics.recovery_factor),
    None if metrics.ann_return is None else float(metrics.ann_return),
    None if metrics.ann_vol is None else float(metrics.ann_vol),
    metrics.rolling_sharpe,
    metrics.rolling_win_rate,
    metrics.rolling_expectancy,
        ),
        )
        self.conn.commit()

    def insert_trades(self, trades: Iterable[TradeSummary]) -> None:
        cur = self.conn.cursor()
        cur.executemany(
            """
            INSERT INTO trades (session_id, pnl, mfe, mae, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            [(t.session_id, t.pnl, t.mfe, t.mae, t.timestamp) for t in trades],
        )
        self.conn.commit()

    def fetch_sessions(self) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT s.*, d.expectancy, d.profit_factor, d.sharpe, d.sortino, d.calmar,
                   d.recovery_factor, d.ann_return, d.ann_vol, d.rolling_sharpe,
                   d.rolling_win_rate, d.rolling_expectancy
            FROM sessions s
            LEFT JOIN derived_metrics d ON s.id = d.session_id
            ORDER BY date(s.trade_date) ASC
            """
        )
        return cur.fetchall()

    def delete_session(self, session_id: int) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        self.conn.commit()

    def delete_all_sessions(self) -> None:
        cur = self.conn.cursor()
        cur.execute("DELETE FROM sessions")
        self.conn.commit()

    def fetch_trades(self, session_id: Optional[int] = None) -> List[sqlite3.Row]:
        cur = self.conn.cursor()
        if session_id:
            cur.execute("SELECT * FROM trades WHERE session_id = ?", (session_id,))
        else:
            cur.execute("SELECT * FROM trades")
        return cur.fetchall()

    def get_settings(self) -> AppSettings:
        cur = self.conn.cursor()
        cur.execute("SELECT key, value FROM settings")
        rows = cur.fetchall()
        settings_dict = {row['key']: row['value'] for row in rows}
        return AppSettings(
            starting_equity=settings_dict.get('starting_equity', 100000.0),
            risk_free_rate=settings_dict.get('risk_free_rate', 0.0)
        )

    def save_settings(self, settings: AppSettings) -> None:
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('starting_equity', ?)",
            (settings.starting_equity,)
        )
        cur.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES ('risk_free_rate', ?)",
            (settings.risk_free_rate,)
        )
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensures connection is closed."""
        self.close()
        return False