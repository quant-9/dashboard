from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtWidgets import (
    QApplication,
    QDateEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QFileDialog,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QDialog,
    QDialogButtonBox,
    QTextEdit,
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

INSTRUMENTS = ["NQ", "GC", "ES", "YM", "RTY", "CL", "ZB"]
ROLLING_WINDOW_DEFAULT = 20
MIN_SESSIONS_FOR_ROLLING = 10
ROLLING_WINDOW_MIN_DIVISOR = 2
CSV_EXPORT_DEFAULT = "sessions.csv"

from database import Database
from metrics_engine import MetricsEngine
from models import DerivedMetrics, SessionRecord, AppSettings


class Sidebar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.buttons = {}
        
        for label in ["Log Trade", "Equity", "Drawdown", "PnL Distribution", 
                      "Rolling Metrics", "Statistics", "History", "Settings"]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setMinimumHeight(40)
            btn.clicked.connect(lambda _, name=label: self.activate(name))
            layout.addWidget(btn)
            self.buttons[label] = btn
        
        layout.addStretch()
        self.setLayout(layout)
        self.setFixedWidth(170)
        self.activate("Log Trade")

    def activate(self, name: str) -> None:
        for label, btn in self.buttons.items():
            btn.setChecked(label == name)
        self.parent().on_nav(name)


class EditSessionDialog(QDialog):
    def __init__(self, session_row: dict, parent=None):
        super().__init__(parent)
        self.session_row = session_row
        self.setWindowTitle("Edit Session")
        self.setModal(True)
        self._build_ui()
        
    def _build_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()
        
        self.date = QDateEdit()
        self.date.setDate(QDate.fromString(self.session_row['trade_date'], 'yyyy-MM-dd'))
        
        self.instrument = QComboBox()
        self.instrument.addItems(INSTRUMENTS)
        self.instrument.setCurrentText(self.session_row['instrument'])
        
        self.net = QLineEdit(str(self.session_row['net_pnl']))
        self.trades = QLineEdit(str(self.session_row['trades']))
        self.wins = QLineEdit(str(self.session_row['wins']))
        self.losses = QLineEdit(str(self.session_row['losses']))
        self.avg_risk = QLineEdit(str(self.session_row['avg_risk']))
        self.avg_reward = QLineEdit(str(self.session_row['avg_reward']))
        self.trims = QLineEdit(str(self.session_row['trims']))
        self.largest_win = QLineEdit(str(self.session_row['largest_win']))
        self.largest_loss = QLineEdit(str(self.session_row['largest_loss']))
        
        self.notes = QTextEdit()
        self.notes.setPlainText(self.session_row.get('notes', '') or '')
        self.notes.setMaximumHeight(80)
        
        form.addRow("Date", self.date)
        form.addRow("Instrument", self.instrument)
        form.addRow("Net PnL", self.net)
        form.addRow("Trades", self.trades)
        form.addRow("Wins", self.wins)
        form.addRow("Losses", self.losses)
        form.addRow("Avg Risk", self.avg_risk)
        form.addRow("Avg Reward", self.avg_reward)
        form.addRow("Trims", self.trims)
        form.addRow("Largest Win", self.largest_win)
        form.addRow("Largest Loss", self.largest_loss)
        form.addRow("Notes", self.notes)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addLayout(form)
        layout.addWidget(buttons)
        self.setLayout(layout)
    
    def get_data(self):
        return {
            'trade_date': self.date.date().toPyDate(),
            'instrument': self.instrument.currentText(),
            'net_pnl': float(self.net.text()),
            'trades': int(self.trades.text()),
            'wins': int(self.wins.text()),
            'losses': int(self.losses.text()),
            'avg_risk': float(self.avg_risk.text() or 0),
            'avg_reward': float(self.avg_reward.text() or 0),
            'trims': int(self.trims.text() or 0),
            'largest_win': float(self.largest_win.text() or 0),
            'largest_loss': float(self.largest_loss.text() or 0),
            'notes': self.notes.toPlainText(),
        }


class SessionForm(QWidget):
    def __init__(self, db: Database, metrics: MetricsEngine, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.metrics = metrics
        self._build_ui()

    @staticmethod
    def _parse_float(value: str, default: float = 0.0) -> float:
        value = value.strip()
        return float(value) if value else default

    @staticmethod
    def _parse_int(value: str, default: int = 0) -> int:
        value = value.strip()
        return int(value) if value else default

    def _build_ui(self) -> None:
        self.date = QDateEdit(calendarPopup=True)
        self.date.setDate(QDate.currentDate())
        self.date.setButtonSymbols(QDateEdit.ButtonSymbols.UpDownArrows)
        
        self.instrument = QComboBox()
        self.instrument.addItems(INSTRUMENTS)
        
        self.net = QLineEdit()
        self.trades = QLineEdit()
        self.wins = QLineEdit()
        self.losses = QLineEdit()
        self.avg_risk = QLineEdit()
        self.avg_reward = QLineEdit()
        self.trims = QLineEdit()
        self.largest_win = QLineEdit()
        self.largest_loss = QLineEdit()
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(80)
        self.notes.setPlaceholderText("Optional session notes...")

        self.trades.setPlaceholderText("auto = wins + losses")
        self.losses.setPlaceholderText("auto = trades - wins")

        form = QFormLayout()
        form.addRow("Date", self.date)
        form.addRow("Instrument", self.instrument)
        form.addRow("Net PnL ($)", self.net)
        form.addRow("Total Trades", self.trades)
        form.addRow("Wins", self.wins)
        form.addRow("Losses", self.losses)
        form.addRow("Avg Risk ($)", self.avg_risk)
        form.addRow("Avg Reward ($)", self.avg_reward)
        form.addRow("Trims", self.trims)
        form.addRow("Largest Win ($)", self.largest_win)
        form.addRow("Largest Loss ($)", self.largest_loss)
        form.addRow("Notes", self.notes)

        submit = QPushButton("Save Session")
        submit.clicked.connect(self.save_session)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(submit)
        layout.addStretch()
        self.setLayout(layout)

    def save_session(self) -> None:
        if not self.net.text().strip():
            QMessageBox.warning(self, "Missing Input", "Please enter Net PnL.")
            return

        try:
            wins = self._parse_int(self.wins.text())
            losses_input = self.losses.text().strip()
            trades_input = self.trades.text().strip()
            
            if trades_input:
                trades = int(trades_input)
            else:
                losses_temp = self._parse_int(losses_input) if losses_input else 0
                trades = wins + losses_temp
            
            if losses_input:
                losses = int(losses_input)
            else:
                losses = max(trades - wins, 0)
            
            if wins < 0 or losses < 0 or trades < 0:
                QMessageBox.warning(self, "Invalid Data", "Trades, wins, and losses cannot be negative.")
                return
            
            if wins + losses != trades:
                QMessageBox.warning(
                    self, 
                    "Invalid Data", 
                    f"Wins ({wins}) + Losses ({losses}) must equal Trades ({trades})"
                )
                return
            
            win_rate = wins / trades if trades else 0.0
            avg_risk = self._parse_float(self.avg_risk.text())
            avg_reward = self._parse_float(self.avg_reward.text())
            rr_ratio = avg_reward / abs(avg_risk) if avg_risk else 0.0
            mfe = self._parse_float(self.largest_win.text())
            mae = abs(self._parse_float(self.largest_loss.text()))

            record = SessionRecord(
                session_id=None,
                trade_date=self.date.date().toPyDate(),
                start_time=None,
                end_time=None,
                instrument=self.instrument.currentText(),
                market_regime=None,
                notes=self.notes.toPlainText() or None,
                gross_pnl=self._parse_float(self.net.text()),
                net_pnl=self._parse_float(self.net.text()),
                max_drawdown=0.0,
                mfe=mfe,
                mae=mae,
                trades=trades,
                wins=wins,
                losses=losses,
                win_rate=win_rate,
                avg_risk=avg_risk,
                avg_reward=avg_reward,
                rr_ratio=rr_ratio,
                trims=self._parse_int(self.trims.text()),
                largest_win=self._parse_float(self.largest_win.text()),
                largest_loss=self._parse_float(self.largest_loss.text()),
            )
        except ValueError as e:
            QMessageBox.warning(self, "Invalid Data", f"Please enter valid numbers: {e}")
            return

        session_id = self.db.insert_session(record)
        
        returns = pd.Series([record.net_pnl])
        expectancy = self.metrics.expectancy(returns)
        pf = self.metrics.profit_factor(returns)
        
        # Handle inf/nan values
        pf_val = None if (np.isinf(pf) or np.isnan(pf)) else pf
        
        derived = DerivedMetrics(
            session_id=session_id,
            expectancy=expectancy,
            profit_factor=pf_val,
            sharpe=None,
            sortino=None,
            calmar=None,
            recovery_factor=None,
            ann_return=None,
            ann_vol=None,
        )
        self.db.upsert_derived(derived)
        QMessageBox.information(self, "Saved", "Session saved successfully.")
        self.clear_form()
        
        if hasattr(self.parent(), 'recalculate_all_metrics'):
            self.parent().recalculate_all_metrics()

    def clear_form(self) -> None:
        self.instrument.setCurrentIndex(0)
        for widget in [self.net, self.trades, self.wins, self.losses, self.avg_risk,
                       self.avg_reward, self.trims, self.largest_win, self.largest_loss]:
            widget.clear()
        self.notes.clear()
class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.db = Database(Path("trading_dashboard.db"))
        self.settings = self.db.get_settings()
        self.metrics = MetricsEngine(risk_free_rate=self.settings.risk_free_rate)
        self.setWindowTitle("Trading Analytics Dashboard")
        self.setStyleSheet(
            """
            QWidget { background-color: #050608; color: #e5e5e5; font-size: 13px; font-family: 'Menlo', 'Consolas', monospace; }
            QLineEdit, QDateEdit, QComboBox, QTextEdit {
                background-color: #101218;
                border: 1px solid #2b2f3a;
                border-radius: 0;
                padding: 4px 6px;
            }
            QListWidget { background-color: #050608; border: 1px solid #2b2f3a; }
            QPushButton {
                background-color: #1b1f2a;
                color: #e5e5e5;
                padding: 6px 10px;
                border-radius: 0;
                border: 1px solid #2b2f3a;
            }
            QPushButton:hover { background-color: #242938; }
            QPushButton:checked {
                background-color: #003b46;
                border-color: #00ff7f;
                color: #00ff7f;
            }
            QLabel { color: #e5e5e5; }
            """
        )
        self._build_layout()
        if len(self.db.fetch_sessions()) > 0:
            self.recalculate_all_metrics()

    def closeEvent(self, event):
        self.db.close()
        event.accept()

    def _build_layout(self) -> None:
        self.form = SessionForm(self.db, self.metrics, parent=self)
        self.statistics = QScrollArea()
        self.statistics.setWidgetResizable(True)
        self.history_list = QListWidget()
        self.history_delete = QPushButton("Delete Selected")
        self.history_edit = QPushButton("Edit Selected")
        self.history_delete_all = QPushButton("Delete All")
        self.history_delete.clicked.connect(self.delete_selected_history)
        self.history_edit.clicked.connect(self.edit_selected_history)
        self.history_delete_all.clicked.connect(self.delete_all_history)
        self.refresh_history()
        
        history_container = QWidget()
        history_layout = QVBoxLayout()
        history_layout.addWidget(self.history_list)
        history_btn_row = QHBoxLayout()
        history_btn_row.addWidget(self.history_edit)
        history_btn_row.addWidget(self.history_delete)
        history_btn_row.addWidget(self.history_delete_all)
        history_layout.addLayout(history_btn_row)
        history_container.setLayout(history_layout)
        
        self.settings_widget = QWidget()
        self._build_settings()

        self.equity_view = QScrollArea()
        self.equity_view.setWidgetResizable(True)
        self.drawdown_view = QScrollArea()
        self.drawdown_view.setWidgetResizable(True)
        self.pnl_view = QScrollArea()
        self.pnl_view.setWidgetResizable(True)
        self.rolling_view = QScrollArea()
        self.rolling_view.setWidgetResizable(True)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.form)
        self.stack.addWidget(self.equity_view)
        self.stack.addWidget(self.drawdown_view)
        self.stack.addWidget(self.pnl_view)
        self.stack.addWidget(self.rolling_view)
        self.stack.addWidget(self.statistics)
        self.stack.addWidget(history_container)
        self.stack.addWidget(self.settings_widget)

        layout = QHBoxLayout()
        layout.addWidget(Sidebar(self))
        layout.addWidget(self.stack, stretch=1)
        self.setLayout(layout)

    def on_nav(self, name: str) -> None:
        mapping = {
            "Log Trade": 0,
            "Equity": 1,
            "Drawdown": 2,
            "PnL Distribution": 3,
            "Rolling Metrics": 4,
            "Statistics": 5,
            "History": 6,
            "Settings": 7,
        }
        if name == "History":
            self.refresh_history()
        if name == "Equity":
            self.render_equity()
        if name == "Drawdown":
            self.render_drawdown()
        if name == "PnL Distribution":
            self.render_pnl_hist()
        if name == "Rolling Metrics":
            self.render_rolling()
        if name == "Statistics":
            self.render_statistics()
        self.stack.setCurrentIndex(mapping.get(name, 0))

    def refresh_history(self) -> None:
        self.history_list.clear()
        for row in self.db.fetch_sessions():
            label = f"{row['trade_date']}  |  {row['instrument']}  |  ${row['net_pnl']:.2f}  |  {row['trades']} trades"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            self.history_list.addItem(item)
        self.history_list.setStyleSheet(
            "QListWidget { background-color: #111; border: 1px solid #2a2a2a; padding: 6px; }"
        )

    def edit_selected_history(self) -> None:
        item = self.history_list.currentItem()
        if not item:
            QMessageBox.information(self, "Edit", "Select a session to edit.")
            return
        
        session_id = item.data(Qt.ItemDataRole.UserRole)
        session_row = self.db.get_session(session_id)
        if not session_row:
            QMessageBox.warning(self, "Edit", "Could not load session data.")
            return
        
        dialog = EditSessionDialog(dict(session_row), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                data = dialog.get_data()
                
                if data['wins'] + data['losses'] != data['trades']:
                    QMessageBox.warning(self, "Invalid Data", "Wins + Losses must equal Trades")
                    return
                
                win_rate = data['wins'] / data['trades'] if data['trades'] else 0.0
                rr_ratio = data['avg_reward'] / abs(data['avg_risk']) if data['avg_risk'] else 0.0
                
                record = SessionRecord(
                    session_id=session_id,
                    trade_date=data['trade_date'],
                    start_time=None,
                    end_time=None,
                    instrument=data['instrument'],
                    market_regime=None,
                    notes=data['notes'],
                    gross_pnl=data['net_pnl'],
                    net_pnl=data['net_pnl'],
                    max_drawdown=0.0,
                    mfe=data['largest_win'],
                    mae=abs(data['largest_loss']),
                    trades=data['trades'],
                    wins=data['wins'],
                    losses=data['losses'],
                    win_rate=win_rate,
                    avg_risk=data['avg_risk'],
                    avg_reward=data['avg_reward'],
                    rr_ratio=rr_ratio,
                    trims=data['trims'],
                    largest_win=data['largest_win'],
                    largest_loss=data['largest_loss'],
                )
                
                self.db.update_session(record)
                self.recalculate_all_metrics()
                self.refresh_history()
                QMessageBox.information(self, "Success", "Session updated successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to update session: {e}")

    def delete_selected_history(self) -> None:
        item = self.history_list.currentItem()
        if not item:
            QMessageBox.information(self, "Delete", "Select a session to delete.")
            return
        session_id = item.data(Qt.ItemDataRole.UserRole)
        if session_id is None:
            QMessageBox.warning(self, "Delete", "Unable to determine session id.")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            "Delete this session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
            
        self.db.delete_session(session_id)
        self.recalculate_all_metrics()
        self.refresh_history()

    def delete_all_history(self) -> None:
        reply = QMessageBox.question(
            self,
            "Delete All Sessions",
            "This will permanently delete ALL sessions. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.db.delete_all_sessions()
        self.recalculate_all_metrics()
        self.refresh_history()

    def _sessions_df(self) -> pd.DataFrame:
        rows = self.db.fetch_sessions()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([dict(r) for r in rows])
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.sort_values("trade_date")
        return df

    def _get_trading_days(self, df: pd.DataFrame) -> int:
        if df.empty:
            return 0
        return df['trade_date'].nunique()

    def _get_equity_curve(self, df: pd.DataFrame) -> pd.Series:
        if df.empty:
            return pd.Series([self.settings.starting_equity])
        
        df_sorted = df.sort_values("trade_date").copy()
        equity = self.settings.starting_equity + df_sorted["net_pnl"].cumsum()
        equity.index = pd.to_datetime(df_sorted["trade_date"])
        return equity

    def recalculate_all_metrics(self) -> None:
        df = self._sessions_df()
        if df.empty:
            return
        
        trading_days = self._get_trading_days(df)
        equity = self._get_equity_curve(df)
        returns = pd.Series(df["net_pnl"].values)
        
        sharpe = self.metrics.sharpe(returns, trading_days)
        sortino = self.metrics.sortino(returns, trading_days)
        calmar = self.metrics.calmar_ratio(equity, trading_days)
        recovery = self.metrics.recovery_factor(equity)
        ann_ret, ann_vol = self.metrics.annualized_return_vol(returns, trading_days)
        
        # Recalculate metrics for each session
        for idx, row in df.iterrows():
            session_id = row['id']
            session_returns = pd.Series([row['net_pnl']])
            
            expectancy = self.metrics.expectancy(session_returns)
            pf = self.metrics.profit_factor(session_returns)
            
            # Use portfolio-level metrics only for the latest session
            is_latest = (idx == len(df) - 1)
            
            derived = DerivedMetrics(
                session_id=session_id,
                expectancy=expectancy,
                profit_factor=pf if not np.isinf(pf) and not np.isnan(pf) else None,
                sharpe=sharpe if is_latest and not np.isnan(sharpe) and not np.isinf(sharpe) else None,
                sortino=sortino if is_latest and not np.isnan(sortino) and not np.isinf(sortino) else None,
                calmar=calmar if is_latest and not np.isnan(calmar) and not np.isinf(calmar) else None,
                recovery_factor=recovery if is_latest and not np.isnan(recovery) and not np.isinf(recovery) else None,
                ann_return=ann_ret if is_latest else None,
                ann_vol=ann_vol if is_latest else None,
            )
            self.db.upsert_derived(derived)

    def _build_settings(self) -> None:
        layout = QVBoxLayout()
        
        equity_layout = QFormLayout()
        self.starting_equity_input = QLineEdit(str(self.settings.starting_equity))
        self.risk_free_rate_input = QLineEdit(str(self.settings.risk_free_rate * 100))  # Convert to percentage for display
        equity_layout.addRow("Starting Equity ($)", self.starting_equity_input)
        equity_layout.addRow("Risk-Free Rate (%)", self.risk_free_rate_input)
        
        save_settings_btn = QPushButton("Save Settings")
        save_settings_btn.clicked.connect(self.save_settings)
        
        layout.addLayout(equity_layout)
        layout.addWidget(save_settings_btn)
        layout.addSpacing(20)
        
        export_btn = QPushButton("Export sessions to CSV")
        import_btn = QPushButton("Import sessions from CSV")
        export_btn.clicked.connect(self.export_csv)
        import_btn.clicked.connect(self.import_csv)
        layout.addWidget(export_btn)
        layout.addWidget(import_btn)
        layout.addStretch()
        self.settings_widget.setLayout(layout)

    def save_settings(self) -> None:
        try:
            starting_equity = float(self.starting_equity_input.text())
            risk_free_rate = float(self.risk_free_rate_input.text())
            
            if starting_equity <= 0:
                QMessageBox.warning(self, "Invalid", "Starting equity must be positive.")
                return
            
            if risk_free_rate < 0 or risk_free_rate > 100:
                QMessageBox.warning(self, "Invalid", "Risk-free rate must be between 0 and 100.")
                return
            
            self.settings.starting_equity = starting_equity
            self.settings.risk_free_rate = risk_free_rate / 100  # Convert percentage to decimal
            self.db.save_settings(self.settings)
            
            # Update metrics engine with new risk-free rate
            self.metrics = MetricsEngine(risk_free_rate=self.settings.risk_free_rate)
            self.recalculate_all_metrics()
            
            QMessageBox.information(self, "Saved", "Settings saved. Metrics recalculated.")
        except ValueError:
            QMessageBox.warning(self, "Invalid", "Please enter valid numbers for settings.")

    def export_csv(self) -> None:
        df = self._sessions_df()
        if df.empty:
            QMessageBox.information(self, "Export", "No data to export.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", CSV_EXPORT_DEFAULT, "CSV Files (*.csv)")
        if not path:
            return
        df.to_csv(path, index=False)
        QMessageBox.information(self, "Export", f"Exported {len(df)} rows to {path}.")

    def import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        try:
            df = pd.read_csv(path)
        except Exception as exc:
            QMessageBox.warning(self, "Import", f"Failed to read CSV: {exc}")
            return
        
        required = ["trade_date", "instrument", "net_pnl", "trades", "wins", "losses",
                    "avg_risk", "avg_reward", "rr_ratio", "trims", "largest_win", "largest_loss"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            QMessageBox.warning(self, "Import", f"Missing required columns: {missing}")
            return
        
        imported = 0
        failed = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                trades = int(row["trades"])
                wins = int(row["wins"])
                losses = int(row["losses"])
                
                if wins + losses != trades:
                    raise ValueError(f"wins + losses != trades")
                
                win_rate = wins / trades if trades else 0.0
                
                record = SessionRecord(
                    session_id=None,
                    trade_date=pd.to_datetime(row["trade_date"]).date(),
                    start_time=None,
                    end_time=None,
                    instrument=str(row["instrument"]),
                    market_regime=row.get("market_regime"),
                    notes=row.get("notes"),
                    gross_pnl=float(row.get("gross_pnl", row["net_pnl"])),
                    net_pnl=float(row["net_pnl"]),
                    max_drawdown=float(row.get("max_drawdown", 0)),
                    mfe=float(row.get("mfe", row["largest_win"])),
                    mae=abs(float(row.get("mae", row["largest_loss"]))),
                    trades=trades,
                    wins=wins,
                    losses=losses,
                    win_rate=win_rate,
                    avg_risk=float(row["avg_risk"]),
                    avg_reward=float(row["avg_reward"]),
                    rr_ratio=float(row["rr_ratio"]),
                    trims=int(row["trims"]),
                    largest_win=float(row["largest_win"]),
                    largest_loss=float(row["largest_loss"]),
                )
                self.db.insert_session(record)
                imported += 1
            except Exception as e:
                failed += 1
                if len(errors) < 5:
                    errors.append(f"Row {idx}: {str(e)}")
                continue
        
        if imported > 0:
            self.recalculate_all_metrics()
        
        msg = f"Imported {imported} sessions."
        if failed > 0:
            msg += f"\n{failed} rows failed."
            if errors:
                msg += "\n\nFirst errors:\n" + "\n".join(errors)
        
        QMessageBox.information(self, "Import", msg)

    def render_equity(self) -> None:
        df = self._sessions_df()
        equity_container = QWidget()
        layout = QVBoxLayout()
        
        if df.empty:
            layout.addWidget(QLabel("No data yet."))
        else:
            try:
                equity = self._get_equity_curve(df)
                full_range = pd.date_range(equity.index.min(), equity.index.max(), freq='D')
                equity = equity.reindex(full_range, method='ffill')
                
                fig = Figure(figsize=(10, 5))
                ax = fig.add_subplot(111)
                ax.plot(equity.index, equity.values, color="#4c9aff", linewidth=2)
                ax.set_title("Equity Curve", fontsize=14, fontweight='bold')
                ax.set_xlabel("Date")
                ax.set_ylabel("Equity ($)")
                ax.grid(True, alpha=0.3)
                ax.ticklabel_format(style="plain", axis="y")
                ax.axhline(y=self.settings.starting_equity, color='gray', linestyle='--', alpha=0.5, label='Starting Equity')
                ax.legend()
                
                layout.addWidget(FigureCanvas(fig))
            except Exception as e:
                logger.error(f"Error rendering equity curve: {e}")
                layout.addWidget(QLabel(f"Error rendering chart: {str(e)}"))
        
        equity_container.setLayout(layout)
        self.equity_view.setWidget(equity_container)

    def render_drawdown(self) -> None:
        df = self._sessions_df()
        drawdown_container = QWidget()
        layout = QVBoxLayout()
        
        if df.empty:
            layout.addWidget(QLabel("No data yet."))
        else:
            equity = self._get_equity_curve(df)
            
            fig = Figure(figsize=(10, 4))
            ax = fig.add_subplot(111)
            
            peaks = equity.cummax()
            drawdown = (equity - peaks) / peaks * 100
            
            ax.fill_between(drawdown.index, drawdown.values, 0, color='#ff4b4b', alpha=0.6)
            ax.plot(drawdown.index, drawdown.values, color='#ff4b4b', linewidth=1.5)
            ax.set_title("Drawdown (Underwater Chart)", fontsize=14, fontweight='bold')
            ax.set_xlabel("Date")
            ax.set_ylabel("Drawdown (%)")
            ax.grid(True, alpha=0.3)
            
            max_dd = drawdown.min()
            ax.axhline(y=max_dd, color='darkred', linestyle='--', alpha=0.7, linewidth=1)
            ax.text(0.02, 0.02, f'Max DD: {max_dd:.2f}%', transform=ax.transAxes, 
                   fontsize=10, verticalalignment='bottom',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
            
            layout.addWidget(FigureCanvas(fig))
        
        drawdown_container.setLayout(layout)
        self.drawdown_view.setWidget(drawdown_container)

    def render_pnl_hist(self) -> None:
        df = self._sessions_df()
        pnl_container = QWidget()
        layout = QVBoxLayout()
        
        if df.empty:
            layout.addWidget(QLabel("No data yet."))
        else:
            fig = Figure(figsize=(8, 5))
            ax = fig.add_subplot(111)
            
            pnl = df["net_pnl"]
            ax.hist(pnl, bins=30, color='#00bcd4', alpha=0.7, edgecolor='black')
            ax.axvline(x=0, color='white', linestyle='--', linewidth=2, alpha=0.8)
            ax.axvline(x=pnl.mean(), color='yellow', linestyle='--', linewidth=1.5, 
                      alpha=0.8, label=f'Mean: ${pnl.mean():.2f}')
            
            ax.set_title("P&L Distribution", fontsize=14, fontweight='bold')
            ax.set_xlabel("P&L ($)")
            ax.set_ylabel("Frequency")
            ax.grid(True, alpha=0.3, axis='y')
            ax.legend()
            
            layout.addWidget(FigureCanvas(fig))
        
        pnl_container.setLayout(layout)
        self.pnl_view.setWidget(pnl_container)

    def render_rolling(self) -> None:
        df = self._sessions_df()
        rolling_container = QWidget()
        layout = QVBoxLayout()
        
        if df.empty:
            layout.addWidget(QLabel("No data yet."))
        elif len(df) < MIN_SESSIONS_FOR_ROLLING:
            layout.addWidget(QLabel(f"Need at least {MIN_SESSIONS_FOR_ROLLING} sessions for rolling metrics."))
        else:
            returns = pd.Series(df["net_pnl"].values)
            window = min(ROLLING_WINDOW_DEFAULT, len(returns) // ROLLING_WINDOW_MIN_DIVISOR)
            rolling_wr = returns.rolling(window=window).apply(
                lambda x: self.metrics.win_rate(pd.Series(x)), raw=False
            )
            
            rolling_exp = returns.rolling(window=window).apply(
                lambda x: self.metrics.expectancy(pd.Series(x)), raw=False
            )
            
            fig = Figure(figsize=(10, 8))
            
            ax1 = fig.add_subplot(211)
            ax1.plot(rolling_wr.index, rolling_wr.values * 100, color='#9ecbff', linewidth=2)
            ax1.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
            ax1.set_title(f"Rolling Win Rate (window={window})", fontsize=12, fontweight='bold')
            ax1.set_ylabel("Win Rate (%)")
            ax1.grid(True, alpha=0.3)
            ax1.set_ylim(0, 100)
            
            ax2 = fig.add_subplot(212)
            ax2.plot(rolling_exp.index, rolling_exp.values, color='#fcb900', linewidth=2)
            ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
            ax2.set_title(f"Rolling Expectancy (window={window})", fontsize=12, fontweight='bold')
            ax2.set_ylabel("Expectancy ($)")
            ax2.set_xlabel("Session Number")
            ax2.grid(True, alpha=0.3)
            
            fig.tight_layout()
            layout.addWidget(FigureCanvas(fig))
        
        rolling_container.setLayout(layout)
        self.rolling_view.setWidget(rolling_container)

    def render_statistics(self) -> None:
        df = self._sessions_df()
        stats_container = QWidget()
        layout = QVBoxLayout()
        
        if df.empty:
            layout.addWidget(QLabel("No data yet."))
        else:
            returns = pd.Series(df["net_pnl"].values)
            equity = self._get_equity_curve(df)
            trading_days = self._get_trading_days(df)
            
            total_pnl = returns.sum()
            total_return_pct = (equity.iloc[-1] / self.settings.starting_equity - 1) * 100
            avg_win, avg_loss = self.metrics.avg_win_loss(returns)
            win_rate = self.metrics.win_rate(returns) * 100
            expectancy = self.metrics.expectancy(returns)
            profit_factor = self.metrics.profit_factor(returns)
            max_dd = self.metrics.max_drawdown_equity(equity) * 100
            sharpe = self.metrics.sharpe(returns, trading_days)
            sortino = self.metrics.sortino(returns, trading_days)
            calmar = self.metrics.calmar_ratio(equity, trading_days)
            recovery = self.metrics.recovery_factor(equity)
            ann_ret, ann_vol = self.metrics.annualized_return_vol(returns, trading_days)
            
            # Format metrics with proper handling of NaN and inf
            sharpe_str = f"{sharpe:.3f}" if not np.isnan(sharpe) else "N/A"
            sortino_str = f"{sortino:.3f}" if not np.isnan(sortino) else "N/A"
            calmar_str = f"{calmar:.3f}" if not (np.isnan(calmar) or np.isinf(calmar)) else "N/A"
            recovery_str = f"{recovery:.3f}" if not (np.isnan(recovery) or np.isinf(recovery)) else "N/A"
            pf_str = f"{profit_factor:.3f}" if not np.isinf(profit_factor) else "∞"
            
            stats_text = QLabel()
            stats_text.setWordWrap(True)
            stats_html = f"""
            <h3 style='color: #00ff7f;'>Portfolio Performance</h3>
            <table style='width: 100%; color: #e5e5e5;'>
            <tr><td><b>Starting Equity:</b></td><td>${self.settings.starting_equity:,.2f}</td></tr>
            <tr><td><b>Current Equity:</b></td><td>${equity.iloc[-1]:,.2f}</td></tr>
            <tr><td><b>Total P&L:</b></td><td style='color: {"#00ff7f" if total_pnl > 0 else "#ff4b4b"};'>${total_pnl:,.2f}</td></tr>
            <tr><td><b>Total Return:</b></td><td style='color: {"#00ff7f" if total_return_pct > 0 else "#ff4b4b"};'>{total_return_pct:.2f}%</td></tr>
            <tr><td><b>Trading Days:</b></td><td>{trading_days}</td></tr>
            <tr><td><b>Total Sessions:</b></td><td>{len(df)}</td></tr>
            </table>
            
            <h3 style='color: #00ff7f; margin-top: 20px;'>Risk Metrics</h3>
            <table style='width: 100%; color: #e5e5e5;'>
            <tr><td><b>Max Drawdown:</b></td><td style='color: #ff4b4b;'>{max_dd:.2f}%</td></tr>
            <tr><td><b>Sharpe Ratio:</b></td><td>{sharpe_str}</td></tr>
            <tr><td><b>Sortino Ratio:</b></td><td>{sortino_str}</td></tr>
            <tr><td><b>Calmar Ratio:</b></td><td>{calmar_str}</td></tr>
            <tr><td><b>Recovery Factor:</b></td><td>{recovery_str}</td></tr>
            <tr><td><b>Ann. Return:</b></td><td>${ann_ret:,.2f}</td></tr>
            <tr><td><b>Ann. Volatility:</b></td><td>${ann_vol:,.2f}</td></tr>
            </table>
            
            <h3 style='color: #00ff7f; margin-top: 20px;'>Trade Statistics</h3>
            <table style='width: 100%; color: #e5e5e5;'>
            <tr><td><b>Win Rate:</b></td><td>{win_rate:.2f}%</td></tr>
            <tr><td><b>Avg Win:</b></td><td style='color: #00ff7f;'>${avg_win:.2f}</td></tr>
            <tr><td><b>Avg Loss:</b></td><td style='color: #ff4b4b;'>${avg_loss:.2f}</td></tr>
            <tr><td><b>Expectancy:</b></td><td>${expectancy:.2f}</td></tr>
            <tr><td><b>Profit Factor:</b></td><td>{pf_str}</td></tr>
            </table>
            """
            
            stats_text.setText(stats_html)
            layout.addWidget(stats_text)
            
            layout.addSpacing(20)
            instr_label = QLabel("<h3 style='color: #00ff7f;'>Per-Instrument Performance</h3>")
            layout.addWidget(instr_label)
        
        by_instr = df.groupby("instrument")
        for instr, grp in by_instr:
            g_returns = pd.Series(grp["net_pnl"].values)
            total_pnl_instr = g_returns.sum()
            win_rate_instr = self.metrics.win_rate(g_returns) * 100
            trades_count = grp["trades"].sum()
            
            instr_html = f"""
            <div style='background-color: #101218; padding: 10px; margin: 5px 0; border-left: 3px solid #00ff7f;'>
            <b>{instr}:</b> 
            Total P&L: <span style='color: {"#00ff7f" if total_pnl_instr > 0 else "#ff4b4b"};'>${total_pnl_instr:,.2f}</span>, 
            Win Rate: {win_rate_instr:.1f}%, 
            Sessions: {len(grp)}, 
            Trades: {trades_count}
            </div>
            """
            instr_widget = QLabel(instr_html)
            instr_widget.setWordWrap(True)
            layout.addWidget(instr_widget)
        layout.addStretch()
        stats_container.setLayout(layout)
        self.statistics.setWidget(stats_container)
def run() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1200, 750)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()