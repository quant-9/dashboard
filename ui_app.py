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
    QDoubleSpinBox,
    QSpinBox,
    QRadioButton,
    QButtonGroup,
    QGroupBox,
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prioritize micros that user trades, then e-minis as backup
INSTRUMENTS = ["MNQ", "MES", "MGC", "NQ", "ES", "GC"]
ROLLING_WINDOW_DEFAULT = 20
MIN_SESSIONS_FOR_ROLLING = 10
ROLLING_WINDOW_MIN_DIVISOR = 2
CSV_EXPORT_DEFAULT = "sessions.csv"

from database import Database
from metrics_engine import MetricsEngine
from models import DerivedMetrics, SessionRecord, AppSettings, FeeConfig





# -----------------------------------------------------------------------------
# VISUAL THEME: Institutional Dark (OpenAI / Linear inspired)
# -----------------------------------------------------------------------------
STYLESHEET_INSTITUTIONAL = """
/* Global Reset */
QWidget {
    font-family: -apple-system, 'Segoe UI', 'Roboto', sans-serif;
    font-size: 13px;
    background-color: #000000; /* True Black */
    color: #EDEDED; /* High Contrast Text */
}

/* Sidebar */
QWidget#Sidebar {
    background-color: #090909;
    border-right: 1px solid #1F1F1F;
}
QPushButton#SidebarBtn {
    background-color: transparent;
    color: #757575;
    text-align: left;
    padding: 10px 12px;
    border: none;
    border-radius: 6px;
    font-weight: 500;
    margin: 2px 8px;
}
QPushButton#SidebarBtn:hover {
    color: #D4D4D4;
    background-color: #141414;
}
QPushButton#SidebarBtn:checked {
    background-color: #1C1C1C;
    color: #FFFFFF;
    font-weight: 600;
}

/* Content Area */
QWidget#ContentArea {
    background-color: #000000; 
}

/* Cards & Containers */
QFrame#Card, QWidget#Card {
    background-color: #0A0A0A;
    border: 1px solid #1F1F1F;
    border-radius: 8px;
}

/* Inputs (Minimalist) */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QDateEdit, QTextEdit {
    background-color: #0A0A0A;
    border: 1px solid #262626;
    border-radius: 6px;
    padding: 8px;
    color: #FFFFFF;
    selection-background-color: #333333;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #555555;
    background-color: #0F0F0F;
}

/* Combo Dropdown */
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #0F0F0F;
    border: 1px solid #262626;
    selection-background-color: #1F1F1F;
}

/* Buttons (Primary Action) */
QPushButton#PrimaryBtn {
    background-color: #FFFFFF;
    color: #000000; /* Black text on white */
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: 600;
    border: 1px solid #FFFFFF;
}
QPushButton#PrimaryBtn:hover {
    background-color: #E0E0E0;
    border-color: #E0E0E0;
}
QPushButton#PrimaryBtn:pressed {
    background-color: #CCCCCC;
}

/* Buttons (Secondary/Ghost) */
QPushButton {
    background-color: transparent;
    color: #A0A0A0;
    border: 1px solid #262626;
    border-radius: 6px;
    padding: 6px 12px;
}
QPushButton:hover {
    border-color: #444444;
    color: #FFFFFF;
    background-color: #0F0F0F;
}

/* Tables / Lists */
QListWidget {
    background-color: #0A0A0A;
    border: 1px solid #1F1F1F;
    border-radius: 6px;
    outline: none;
}
QListWidget::item {
    padding: 8px;
    border-bottom: 1px solid #141414;
}
QListWidget::item:selected {
    background-color: #141414;
    color: #FFFFFF;
    border-left: 2px solid #FFFFFF;
}
QListWidget::item:hover {
    background-color: #0F0F0F;
}

/* Scrollbars (Subtle) */
QScrollBar:vertical {
    border: none;
    background: #000000;
    width: 8px;
    margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #262626;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

/* Radio Buttons */
QRadioButton {
    color: #A0A0A0;
    spacing: 5px;
}
QRadioButton::indicator {
    width: 14px;
    height: 14px;
    border-radius: 7px;
    border: 1px solid #444444;
    background: transparent;
}
QRadioButton::indicator:checked {
    background-color: #FFFFFF;
    border-color: #FFFFFF;
}
"""

class Sidebar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self.setFixedWidth(220) # Defined rail width
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 20, 0, 20)
        self.layout.setSpacing(4)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.setLayout(self.layout)
        
        
        # Branding / Title - Removed per user request
        # title = QLabel("  TRADING\n  DASHBOARD")
        # title.setStyleSheet("color: #FFFFFF; font-weight: 700; font-size: 11px; letter-spacing: 1px; margin-bottom: 20px; margin-left: 8px;")
        # self.layout.addWidget(title)
        
        # Spacer for top
        self.layout.addSpacing(20)

        self.buttons = {}
        
        # Menu Items structure
        items = [
            ("Dashboard", "Statistics"), # Renamed Statistics to Dashboard
            ("New Trade", "Log Trade"),  
            ("Journal", "History"),
            ("Equity Curve", "Equity"),
            ("Drawdown", "Drawdown"),
            ("PnL Analysis", "PnL Distribution"),
            ("Rolling Stats", "Rolling Metrics"),
            ("Settings", "Settings"),
        ]
        
        for display_name, internal_name in items:
            btn = QPushButton(display_name)
            btn.setObjectName("SidebarBtn")
            btn.setCheckable(True)
            # Exclusive check behavior handled manually or via ButtonGroup, 
            # but simpler to handle in Main for page switching.
            self.buttons[internal_name] = btn
            self.layout.addWidget(btn)
            
        self.layout.addStretch()
        
        # Footer
        version = QLabel("  v2.0 Institutional")
        version.setStyleSheet("color: #444444; font-size: 10px; margin-left: 8px;")
        self.layout.addWidget(version)

class SessionForm(QWidget):
    def __init__(self, db: Database, metrics: MetricsEngine, parent=None) -> None:
        super().__init__(parent)
        self.db = db
        self.metrics = metrics
        self.setObjectName("Card") # Make it a Card
        self._build_ui()

    def _build_ui(self) -> None:
        # Container style
        self.setStyleSheet("""
            QWidget#InnerForm { background-color: transparent; }
            QLabel { color: #A0A0A0; font-weight: 500; font-size: 12px; }
            QLabel#Header { color: #FFFFFF; font-size: 16px; font-weight: 600; margin-bottom: 10px; }
            QLabel#SubHeader { color: #888888; font-size: 11px; margin-top: -5px; }
            QPushButton#LogTradeBtn { 
                background-color: #FFFFFF; 
                color: #000000; 
                font-weight: 600; 
                border-radius: 6px; 
                padding: 10px;
                border: 1px solid #FFFFFF;
            }
            QPushButton#LogTradeBtn:hover { background-color: #E0E0E0; border-color: #E0E0E0; }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        
        header = QLabel("Log Trade")
        header.setObjectName("Header")
        layout.addWidget(header)
        
        form_grid = QFormLayout()
        form_grid.setSpacing(16)
        form_grid.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        self.date.setDate(QDate.currentDate())
        self.date.setFixedWidth(140)
        
        self.instrument = QComboBox()
        self.instrument.addItems(INSTRUMENTS)
        self.instrument.setFixedWidth(140)
        
        # Direction
        dir_layout = QHBoxLayout()
        self.direction_group = QButtonGroup(self)
        self.long_radio = QRadioButton("Long")
        self.short_radio = QRadioButton("Short")
        self.long_radio.setChecked(True)
        self.direction_group.addButton(self.long_radio)
        self.direction_group.addButton(self.short_radio)
        dir_layout.addWidget(self.long_radio)
        dir_layout.addWidget(self.short_radio)
        dir_layout.addStretch()

        # Total contracts
        self.contracts = QSpinBox()
        self.contracts.setRange(1, 100)
        self.contracts.setSingleStep(1)
        self.contracts.setValue(2)
        self.contracts.setFixedWidth(140)
        
        # Custom trim contract allocation (for uneven splits)
        trim_contract_layout = QHBoxLayout()
        self.trim1_contracts = QSpinBox()
        self.trim1_contracts.setRange(0, 100)
        self.trim1_contracts.setValue(1)
        self.trim1_contracts.setFixedWidth(60)
        self.trim1_contracts.setToolTip("Contracts to exit at Trim 1")
        
        self.trim2_contracts = QSpinBox()
        self.trim2_contracts.setRange(0, 100)
        self.trim2_contracts.setValue(1)
        self.trim2_contracts.setFixedWidth(60)
        self.trim2_contracts.setToolTip("Contracts to exit at Trim 2 (runner)")
        
        trim_contract_layout.addWidget(QLabel("T1:"))
        trim_contract_layout.addWidget(self.trim1_contracts)
        trim_contract_layout.addWidget(QLabel("T2:"))
        trim_contract_layout.addWidget(self.trim2_contracts)
        trim_contract_layout.addStretch()
        
        self.stop_points = QDoubleSpinBox()
        self.stop_points.setRange(0.5, 500.0)
        self.stop_points.setValue(10.0)
        self.stop_points.setFixedWidth(140)
        
        self.trim1_target = QDoubleSpinBox()
        self.trim1_target.setRange(1.0, 5000.0)
        self.trim1_target.setValue(50.0)
        self.trim1_target.setFixedWidth(140)
        
        self.trim2_target = QDoubleSpinBox()
        self.trim2_target.setRange(1.0, 5000.0)
        self.trim2_target.setValue(100.0)
        self.trim2_target.setFixedWidth(140)
        
        self.result_type = QComboBox()
        self.result_type.addItems([
            "Full TP (Both Trims)", 
            "Trim 1 + BE (Runner Stopped)",
            "Trim 1 Only (Partial)",
            "Stopped Out (Full Loss)",
            "Custom P&L (Manual Entry)"
        ])
        
        # Calculated Fields
        self.gross_pnl = QDoubleSpinBox()
        self.gross_pnl.setReadOnly(True)
        self.gross_pnl.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.gross_pnl.setRange(-1000000.0, 1000000.0)
        self.gross_pnl.setPrefix("$")
        self.gross_pnl.setFixedWidth(140)
        
        # Editable fee override (shows calculated but allows editing)
        self.fees_display = QDoubleSpinBox()
        self.fees_display.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.fees_display.setRange(0.0, 100000.0)
        self.fees_display.setPrefix("$")
        self.fees_display.setFixedWidth(140)
        self.fees_display.setToolTip("Auto-calculated from settings. Override if needed.")
        
        self.net_pnl = QDoubleSpinBox()
        self.net_pnl.setReadOnly(True)
        self.net_pnl.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
        self.net_pnl.setRange(-1000000.0, 1000000.0)
        self.net_pnl.setPrefix("$")
        self.net_pnl.setFixedWidth(140)
        
        # Manual P&L entry field (only visible for Custom P&L option)
        self.manual_gross_pnl = QDoubleSpinBox()
        self.manual_gross_pnl.setRange(-1000000.0, 1000000.0)
        self.manual_gross_pnl.setPrefix("$")
        self.manual_gross_pnl.setFixedWidth(140)
        self.manual_gross_pnl.setValue(0.0)
        self.manual_gross_pnl.setVisible(False)
        
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(80)
        self.notes.setPlaceholderText("Execution notes...")
        
        # Compose Form
        form_grid.addRow("Date", self.date)
        form_grid.addRow("Instrument", self.instrument)
        form_grid.addRow("Direction", dir_layout)
        form_grid.addRow("Total Contracts", self.contracts)
        form_grid.addRow("Trim Split", trim_contract_layout)
        form_grid.addRow("Stop (pts)", self.stop_points)
        form_grid.addRow("Trim 1 (pts)", self.trim1_target)
        form_grid.addRow("Trim 2 (pts)", self.trim2_target)
        form_grid.addRow("Outcome", self.result_type)
        form_grid.addRow("Manual Gross", self.manual_gross_pnl)
        form_grid.addRow("Gross P&L", self.gross_pnl)
        form_grid.addRow("Fees", self.fees_display)
        form_grid.addRow("Net P&L", self.net_pnl)
        form_grid.addRow("Notes", self.notes)
        
        # Connect signals
        recalc_widgets = [
            self.contracts, self.stop_points, self.trim1_target, self.trim2_target,
            self.trim1_contracts, self.trim2_contracts, self.instrument, self.manual_gross_pnl
        ]
        for w in recalc_widgets:
            if isinstance(w, (QDoubleSpinBox, QSpinBox)):
                w.valueChanged.connect(self._calculate_pnl)
            elif isinstance(w, QComboBox):
                w.currentTextChanged.connect(self._calculate_pnl)
                
        self.result_type.currentTextChanged.connect(self._on_outcome_changed)
        self.fees_display.valueChanged.connect(self._update_net_pnl)
        
        # Sync total contracts with trim splits
        self.contracts.valueChanged.connect(self._sync_trim_contracts)

        # Submit
        submit = QPushButton("Log Trade")
        submit.setObjectName("LogTradeBtn")
        submit.setCursor(Qt.CursorShape.PointingHandCursor)
        submit.clicked.connect(self.save_session)
        
        layout.addLayout(form_grid)
        layout.addSpacing(20)
        layout.addWidget(submit)
        layout.addStretch()
        
        self.setLayout(layout)
        self._calculate_pnl()

    def _sync_trim_contracts(self) -> None:
        """Auto-distribute contracts between trims when total changes."""
        total = self.contracts.value()
        # Default: split evenly (or as close as possible)
        t1 = total // 2
        t2 = total - t1
        self.trim1_contracts.blockSignals(True)
        self.trim2_contracts.blockSignals(True)
        self.trim1_contracts.setValue(t1)
        self.trim2_contracts.setValue(t2)
        self.trim1_contracts.blockSignals(False)
        self.trim2_contracts.blockSignals(False)
        self._calculate_pnl()
        
    def _on_outcome_changed(self) -> None:
        """Show/hide manual P&L entry based on outcome selection."""
        is_custom = "Custom" in self.result_type.currentText()
        self.manual_gross_pnl.setVisible(is_custom)
        self.gross_pnl.setReadOnly(not is_custom)
        self._calculate_pnl()

    # Reuse methods for calculation but adapt colors
    def _get_tick_value(self) -> float:
        instr = self.instrument.currentText()
        if instr == "MNQ": return 2.0
        if instr == "MES": return 5.0
        if instr == "MGC": return 1.0
        if instr == "NQ": return 20.0
        if instr == "ES": return 50.0
        if instr == "GC": return 10.0
        return 1.0

    def _get_fee_per_contract(self) -> float:
        """Get fee from main window settings if available."""
        instr = self.instrument.currentText()
        try:
            # Try to get settings from parent MainWindow
            if hasattr(self, 'parent') and self.parent() and hasattr(self.parent(), 'settings'):
                return self.parent().settings.fees.get_fee(instr)
        except:
            pass
        # Fallback defaults (new broker rates)
        fee_map = {
            "MNQ": 1.00, "MES": 1.00, "MGC": 1.00,
            "NQ": 1.75, "ES": 2.50, "GC": 2.50
        }
        return fee_map.get(instr, 1.50)

    def _calculate_pnl(self) -> None:
        tick_val = self._get_tick_value()
        contracts_num = self.contracts.value()
        stop = self.stop_points.value()
        trim1 = self.trim1_target.value()
        trim2 = self.trim2_target.value()
        outcome = self.result_type.currentText()
        
        # Use custom trim contract allocation (not necessarily half/half)
        t1_contracts = self.trim1_contracts.value()
        t2_contracts = self.trim2_contracts.value()
        
        gross = 0.0
        
        if "Custom" in outcome:
            # Use manual entry
            gross = self.manual_gross_pnl.value()
        elif "Full TP" in outcome:
            # Both trims hit
            gross = (trim1 * t1_contracts * tick_val) + (trim2 * t2_contracts * tick_val)
        elif "Trim 1 + BE" in outcome:
            # Trim 1 hit, runner stopped at breakeven
            gross = (trim1 * t1_contracts * tick_val) + 0.0
        elif "Trim 1 Only" in outcome:
            # Trim 1 hit, no runner (partial exit before T2)
            gross = (trim1 * t1_contracts * tick_val)
        elif "Stopped Out" in outcome:
            # Full stop loss on all contracts
            gross = -(stop * contracts_num * tick_val)
            
        fees = self._get_fee_per_contract() * contracts_num
        net = gross - fees
        
        self.gross_pnl.setValue(gross)
        self.fees_display.blockSignals(True)
        self.fees_display.setValue(fees)
        self.fees_display.blockSignals(False)
        self.net_pnl.setValue(net)
        
        self._apply_pnl_colors(gross, net)

    def _update_net_pnl(self) -> None:
        """Called when user manually overrides fees."""
        gross = self.gross_pnl.value()
        fees = self.fees_display.value()
        net = gross - fees
        self.net_pnl.setValue(net)
        self._apply_pnl_colors(gross, net)
        
    def _apply_pnl_colors(self, gross: float, net: float) -> None:
        # Colors: Green #2E8B57, Red #CD5C5C
        c_green = "#2E8B57"
        c_red = "#CD5C5C"
        c_neutral = "#888888"
        
        self.gross_pnl.setStyleSheet(f"color: {c_green if gross > 0 else c_red if gross < 0 else c_neutral}; border: none; background: transparent;")
        self.net_pnl.setStyleSheet(f"color: {c_green if net > 0 else c_red if net < 0 else c_neutral}; font-weight: bold; border: none; background: transparent;")

    def save_session(self) -> None:
        try:
            contracts = self.contracts.value()
            t1_contracts = self.trim1_contracts.value()
            t2_contracts = self.trim2_contracts.value()
            
            # Validate trim contracts don't exceed total
            if t1_contracts + t2_contracts > contracts:
                QMessageBox.warning(self, "Invalid Split", 
                    f"Trim contracts ({t1_contracts} + {t2_contracts}) exceed total ({contracts}).")
                return

            gross = self.gross_pnl.value()
            fees = self.fees_display.value()
            net = gross - fees
            outcome = self.result_type.currentText()
            
            win = 1 if net > 0 else 0
            loss = 1 if net < 0 else 0
            be = 1 if net == 0 else 0
            
            trim1_hit = "Full TP" in outcome or "Trim 1" in outcome
            trim2_hit = "Full TP" in outcome
            
            tick_val = self._get_tick_value()
            risk = self.stop_points.value() * contracts * tick_val
            reward_pot = ((self.trim1_target.value() * t1_contracts) + 
                          (self.trim2_target.value() * t2_contracts)) * tick_val
            
            largest_win = net if win else 0.0
            largest_loss = net if loss else 0.0
            
            record = SessionRecord(
                session_id=None,
                trade_date=self.date.date().toPyDate(),
                start_time=None, end_time=None,
                instrument=self.instrument.currentText(),
                direction="Long" if self.long_radio.isChecked() else "Short",
                contracts=contracts,
                entry_price=0.0,
                stop_points=self.stop_points.value(),
                trim1_points=self.trim1_target.value(),
                trim2_points=self.trim2_target.value(),
                trim1_hit=trim1_hit, trim2_hit=trim2_hit,
                market_regime=None, notes=self.notes.toPlainText(),
                gross_pnl=gross, net_pnl=net,
                max_drawdown=0.0, mfe=0.0, mae=0.0,
                trades=1, wins=win, losses=loss, breakeven_trades=be,
                win_rate=1.0 if win else 0.0,
                avg_risk=risk, avg_reward=reward_pot,
                rr_ratio=reward_pot/risk if risk > 0 else 0.0,
                largest_win=largest_win, largest_loss=largest_loss,
            )
            
            sid = self.db.insert_session(record)
            
            # Upsert dummy derived for completeness
            derived = DerivedMetrics(session_id=sid, expectancy=net, profit_factor=0.0, sharpe=0.0, sortino=0.0, calmar=0.0, recovery_factor=0.0, ann_return=0.0, ann_vol=0.0)
            self.db.upsert_derived(derived)
            
            QMessageBox.information(self, "Saved", "Trade logged.")
            self.notes.clear()
            self._calculate_pnl()
            
            if self.parent():
                try:
                    self.parent().recalculate_all_metrics()
                except:
                    pass
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))



class EditSessionDialog(QDialog):
    def __init__(self, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Trade")
        self.setFixedWidth(450)
        self.data = data
        self.setStyleSheet("""
            QDialog { background-color: #0A0A0A; color: #FFFFFF; }
            QLabel { color: #A0A0A0; font-family: sans-serif; }
            QLineEdit, QDateEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit {
                background-color: #111111; border: 1px solid #333; color: #FFF; padding: 6px; border-radius: 4px;
            }
            QDialogButtonBox QPushButton {
                background-color: #FFF; color: #000; border-radius: 4px; padding: 6px 12px; font-weight: 600;
            }
            QDialogButtonBox QPushButton[text="Cancel"] {
                background-color: transparent; color: #AAA; border: 1px solid #333;
            }
        """)
        self._build_ui()
        
    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        form = QFormLayout()
        form.setSpacing(12)
        
        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        # Handle date conversion safely
        d_val = self.data.get('trade_date')
        if isinstance(d_val, str):
            d = QDate.fromString(d_val, "yyyy-MM-dd")
        else:
            try:
                d = QDate(d_val.year, d_val.month, d_val.day)
            except:
                d = QDate.currentDate()
            
        if not d.isValid(): d = QDate.currentDate()
        self.date.setDate(d)
        
        self.instrument = QComboBox()
        self.instrument.addItems(INSTRUMENTS)
        self.instrument.setCurrentText(self.data.get('instrument', 'MNQ'))
        
        self.direction = QComboBox()
        self.direction.addItems(["Long", "Short"])
        self.direction.setCurrentText(self.data.get('direction', 'Long'))
        
        # Allow any number of contracts (not just even)
        self.contracts = QSpinBox()
        self.contracts.setRange(1, 100)
        self.contracts.setSingleStep(1)
        self.contracts.setValue(self.data.get('contracts', 2))
        
        self.stop_points = QDoubleSpinBox()
        self.stop_points.setRange(0.5, 500.0)
        self.stop_points.setValue(self.data.get('stop_points', 10.0))
        
        self.trim1_points = QDoubleSpinBox()
        self.trim1_points.setRange(1.0, 5000.0)
        self.trim1_points.setValue(self.data.get('trim1_points', 50.0))
        
        self.trim2_points = QDoubleSpinBox()
        self.trim2_points.setRange(1.0, 5000.0)
        self.trim2_points.setValue(self.data.get('trim2_points', 100.0))
        
        # Gross P&L (editable for custom trades)
        self.gross_pnl = QDoubleSpinBox()
        self.gross_pnl.setRange(-1000000.0, 1000000.0)
        self.gross_pnl.setPrefix("$")
        self.gross_pnl.setValue(self.data.get('gross_pnl', 0.0))
        
        self.net_pnl = QDoubleSpinBox()
        self.net_pnl.setRange(-1000000.0, 1000000.0)
        self.net_pnl.setPrefix("$")
        self.net_pnl.setValue(self.data.get('net_pnl', 0.0))
        
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(60)
        self.notes.setText(self.data.get('notes', '') or '')
        
        form.addRow("Date", self.date)
        form.addRow("Instrument", self.instrument)
        form.addRow("Direction", self.direction)
        form.addRow("Contracts", self.contracts)
        form.addRow("Stop (pts)", self.stop_points)
        form.addRow("Trim 1 (pts)", self.trim1_points)
        form.addRow("Trim 2 (pts)", self.trim2_points)
        form.addRow("Gross P&L", self.gross_pnl)
        form.addRow("Net P&L", self.net_pnl)
        form.addRow("Notes", self.notes)
        
        layout.addLayout(form)
        
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)
        
        self.setLayout(layout)
        
    def get_data(self) -> dict:
        return {
            'trade_date': self.date.date().toPyDate(),
            'instrument': self.instrument.currentText(),
            'direction': self.direction.currentText(),
            'contracts': self.contracts.value(),
            'stop_points': self.stop_points.value(),
            'trim1_points': self.trim1_points.value(),
            'trim2_points': self.trim2_points.value(),
            'gross_pnl': self.gross_pnl.value(),
            'net_pnl': self.net_pnl.value(),
            'notes': self.notes.toPlainText(),
            'entry_price': 0.0
        }

class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.db = Database(Path("trading_dashboard.db"))
        self.settings = self.db.get_settings()
        self.metrics = MetricsEngine(risk_free_rate=self.settings.risk_free_rate)
        
        self.setWindowTitle("Citadel Trading | Professional Dashboard")
        self.resize(1400, 900)
        self.setStyleSheet(STYLESHEET_INSTITUTIONAL)
        
        self._build_layout()
        if len(self.db.fetch_sessions()) > 0:
            self.recalculate_all_metrics()

    def closeEvent(self, event):
        self.db.close()
        event.accept()

    def _build_layout(self) -> None:
        # Main Horizontal Layout
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)
        
        # Content Area (Stacked)
        self.content_area = QStackedWidget()
        self.content_area.setObjectName("ContentArea")
        main_layout.addWidget(self.content_area)
        
        self.setLayout(main_layout)
        
        # Initialize Pages
        self._init_pages()
        
        # Connect Sidebar
        for name, btn in self.sidebar.buttons.items():
            btn.clicked.connect(lambda checked, n=name: self.switch_page(n))
            
        # Default Page
        self.switch_page("Statistics") # Start at Dashboard

    def _init_pages(self):
        # 1. Statistics (Dashboard)
        self.stats_view = QScrollArea()
        self.stats_view.setWidgetResizable(True)
        self.stats_view.setStyleSheet("background: transparent; border: none;")
        self.content_area.addWidget(self.stats_view)
        
        # 2. Log Trade
        self.form_view = QWidget()
        form_layout = QHBoxLayout()
        form_layout.setContentsMargins(40, 40, 40, 40)
        form_layout.addStretch()
        self.form = SessionForm(self.db, self.metrics, parent=self)
        self.form.setFixedWidth(500) # Centered Form Card
        form_layout.addWidget(self.form)
        form_layout.addStretch()
        self.form_view.setLayout(form_layout)
        self.content_area.addWidget(self.form_view)
        
        # 3. History
        self.history_view = QWidget()
        hist_layout = QVBoxLayout()
        hist_layout.setContentsMargins(30, 30, 30, 30)
        
        hist_header = QLabel("Trade Journal")
        hist_header.setStyleSheet("color: #FFFFFF; font-size: 18px; font-weight: 600; margin-bottom: 20px;")
        hist_layout.addWidget(hist_header)
        
        self.history_list = QListWidget()
        hist_layout.addWidget(self.history_list)
        
        btn_layout = QHBoxLayout()
        self.history_edit = QPushButton("Edit Selected")
        self.history_delete = QPushButton("Delete Selected")
        self.history_delete_all = QPushButton("Delete All")
        self.history_delete_all.setStyleSheet("color: #CD5C5C; border: 1px solid #CD5C5C;") # Warning color
        
        self.history_edit.clicked.connect(self.edit_selected_history)
        self.history_delete.clicked.connect(self.delete_selected_history)
        self.history_delete_all.clicked.connect(self.delete_all_history)
        
        btn_layout.addWidget(self.history_edit)
        btn_layout.addWidget(self.history_delete)
        btn_layout.addWidget(self.history_delete_all)
        btn_layout.addStretch()
        hist_layout.addLayout(btn_layout)
        
        self.history_view.setLayout(hist_layout)
        self.content_area.addWidget(self.history_view)
        
        # 4. Equity
        self.equity_view = QScrollArea()
        self.equity_view.setWidgetResizable(True)
        self.content_area.addWidget(self.equity_view)
        
        # 5. Drawdown
        self.drawdown_view = QScrollArea()
        self.drawdown_view.setWidgetResizable(True)
        self.content_area.addWidget(self.drawdown_view)
        
        # 6. PnL Dist
        self.pnl_dist_view = QScrollArea()
        self.pnl_dist_view.setWidgetResizable(True)
        self.content_area.addWidget(self.pnl_dist_view)
        
        # 7. Rolling
        self.rolling_view = QScrollArea()
        self.rolling_view.setWidgetResizable(True)
        self.content_area.addWidget(self.rolling_view)
        
        # 8. Settings
        self.settings_view = QScrollArea()
        self.settings_view.setWidgetResizable(True)
        settings_container = QWidget()
        set_layout = QVBoxLayout()
        set_layout.setContentsMargins(60, 60, 60, 60)
        set_layout.setSpacing(30)
        
        # Title
        set_header = QLabel("Settings")
        set_header.setStyleSheet("color: #FFFFFF; font-size: 24px; font-weight: 600; margin-bottom: 20px;")
        set_layout.addWidget(set_header)

        # Portfolio Settings Card
        portfolio_card = QWidget()
        portfolio_card.setStyleSheet("background-color: #0A0A0A; border-radius: 8px; padding: 20px;")
        portfolio_form = QFormLayout()
        portfolio_form.setSpacing(12)
        
        self.starting_equity_input = QLineEdit(str(self.settings.starting_equity))
        self.starting_equity_input.setFixedWidth(200)
        portfolio_form.addRow("Starting Equity ($)", self.starting_equity_input)
        
        
        portfolio_card.setLayout(portfolio_form)
        
        portfolio_header = QLabel("Portfolio")
        portfolio_header.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: 600; margin-bottom: 10px;")
        set_layout.addWidget(portfolio_header)
        set_layout.addWidget(portfolio_card)

        # Fee Configuration Card
        fee_header = QLabel("Commission Fees (Roundtrip per Contract)")
        fee_header.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: 600; margin-top: 20px; margin-bottom: 10px;")
        set_layout.addWidget(fee_header)
        
        fee_card = QWidget()
        fee_card.setStyleSheet("background-color: #0A0A0A; border-radius: 8px; padding: 20px;")
        fee_form = QFormLayout()
        fee_form.setSpacing(12)
        
        # Micro contracts
        self.fee_mnq_input = QDoubleSpinBox()
        self.fee_mnq_input.setRange(0.0, 100.0)
        self.fee_mnq_input.setPrefix("$")
        self.fee_mnq_input.setDecimals(2)
        self.fee_mnq_input.setValue(self.settings.fees.mnq_fee)
        self.fee_mnq_input.setFixedWidth(120)
        fee_form.addRow("MNQ (Micro Nasdaq)", self.fee_mnq_input)
        
        self.fee_mes_input = QDoubleSpinBox()
        self.fee_mes_input.setRange(0.0, 100.0)
        self.fee_mes_input.setPrefix("$")
        self.fee_mes_input.setDecimals(2)
        self.fee_mes_input.setValue(self.settings.fees.mes_fee)
        self.fee_mes_input.setFixedWidth(120)
        fee_form.addRow("MES (Micro S&P)", self.fee_mes_input)
        
        self.fee_mgc_input = QDoubleSpinBox()
        self.fee_mgc_input.setRange(0.0, 100.0)
        self.fee_mgc_input.setPrefix("$")
        self.fee_mgc_input.setDecimals(2)
        self.fee_mgc_input.setValue(self.settings.fees.mgc_fee)
        self.fee_mgc_input.setFixedWidth(120)
        fee_form.addRow("MGC (Micro Gold)", self.fee_mgc_input)
        
        # E-mini contracts
        self.fee_nq_input = QDoubleSpinBox()
        self.fee_nq_input.setRange(0.0, 100.0)
        self.fee_nq_input.setPrefix("$")
        self.fee_nq_input.setDecimals(2)
        self.fee_nq_input.setValue(self.settings.fees.nq_fee)
        self.fee_nq_input.setFixedWidth(120)
        fee_form.addRow("NQ (E-mini Nasdaq)", self.fee_nq_input)
        
        self.fee_es_input = QDoubleSpinBox()
        self.fee_es_input.setRange(0.0, 100.0)
        self.fee_es_input.setPrefix("$")
        self.fee_es_input.setDecimals(2)
        self.fee_es_input.setValue(self.settings.fees.es_fee)
        self.fee_es_input.setFixedWidth(120)
        fee_form.addRow("ES (E-mini S&P)", self.fee_es_input)
        
        self.fee_gc_input = QDoubleSpinBox()
        self.fee_gc_input.setRange(0.0, 100.0)
        self.fee_gc_input.setPrefix("$")
        self.fee_gc_input.setDecimals(2)
        self.fee_gc_input.setValue(self.settings.fees.gc_fee)
        self.fee_gc_input.setFixedWidth(120)
        fee_form.addRow("GC (E-mini Gold)", self.fee_gc_input)
        
        self.fee_default_input = QDoubleSpinBox()
        self.fee_default_input.setRange(0.0, 100.0)
        self.fee_default_input.setPrefix("$")
        self.fee_default_input.setDecimals(2)
        self.fee_default_input.setValue(self.settings.fees.default_fee)
        self.fee_default_input.setFixedWidth(120)
        fee_form.addRow("Default (Other)", self.fee_default_input)
        
        fee_card.setLayout(fee_form)
        set_layout.addWidget(fee_card)

        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("PrimaryBtn")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setFixedWidth(200)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        set_layout.addWidget(save_btn)
        
        set_layout.addSpacing(30)
        
        # Data Management
        data_header = QLabel("Data Management")
        data_header.setStyleSheet("color: #FFFFFF; font-size: 16px; font-weight: 600; margin-bottom: 10px;")
        set_layout.addWidget(data_header)
        
        data_controls = QWidget()
        data_controls.setStyleSheet("background-color: #0A0A0A; border-radius: 8px; padding: 20px;")
        data_btn_layout = QHBoxLayout()
        data_btn_layout.setContentsMargins(0,0,0,0)
        
        import_btn = QPushButton("Import CSV")
        export_btn = QPushButton("Export CSV")
        import_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        import_btn.clicked.connect(self.import_csv)
        export_btn.clicked.connect(self.export_csv)
        
        data_btn_layout.addWidget(import_btn)
        data_btn_layout.addWidget(export_btn)
        data_btn_layout.addStretch()
        data_controls.setLayout(data_btn_layout)
        
        set_layout.addWidget(data_controls)

        set_layout.addStretch()
        settings_container.setLayout(set_layout)
        self.settings_view.setWidget(settings_container)
        self.content_area.addWidget(self.settings_view)
        
        # Map pages
        self.pages = {
            "Statistics": 0,
            "Log Trade": 1,
            "History": 2,
            "Equity": 3,
            "Drawdown": 4,
            "PnL Distribution": 5,
            "Rolling Metrics": 6,
            "Settings": 7
        }

    def switch_page(self, name: str):
        idx = self.pages.get(name, 0)
        self.content_area.setCurrentIndex(idx)
        
        # Update Sidebar State
        for n, btn in self.sidebar.buttons.items():
            btn.setChecked(n == name)
            
        # Refresh Logic
        if name == "History":
            self.refresh_history()
        elif name == "Equity":
            self.render_equity()
        elif name == "Drawdown":
            self.render_drawdown()
        elif name == "PnL Distribution":
            self.render_pnl_hist()
        elif name == "Rolling Metrics":
            self.render_rolling()
        elif name == "Statistics":
            self.render_statistics()

    def refresh_history(self) -> None:
        self.history_list.clear()
        for row in self.db.fetch_sessions():
            # Format: Date | Instrument | Direction | PnL | Result
            pnl = row['net_pnl']
            res_text = "WIN" if pnl > 0 else "LOSS"
            if pnl == 0: res_text = "BE"
            
            # sqlite3.Row doesn't have .get(), check keys manually
            direction = row['direction'] if 'direction' in row.keys() else ''
            
            label = f"{row['trade_date']}  |  {row['instrument']} {direction}  |  ${pnl:,.2f}  |  {res_text}"
            item = QListWidgetItem(label)
            item.setForeground(Qt.GlobalColor.white) 
            item.setData(Qt.ItemDataRole.UserRole, row["id"])
            self.history_list.addItem(item)
        self.history_list.setStyleSheet(
            "QListWidget { background-color: #111; border: 1px solid #2a2a2a; padding: 6px; font-family: monospace; }"
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
                
                # Logic for derived fields based on edit
                win = 1 if data['net_pnl'] > 0 else 0
                loss = 1 if data['net_pnl'] < 0 else 0
                be = 1 if data['net_pnl'] == 0 else 0
                
                # Tick value lookup
                tick_map = {
                    "MNQ": 2.0, "MES": 5.0, "MGC": 1.0,
                    "NQ": 20.0, "ES": 50.0, "GC": 10.0
                }
                tick_val = tick_map.get(data['instrument'], 1.0)
                
                risk = data['stop_points'] * data['contracts'] * tick_val
                
                record = SessionRecord(
                    session_id=session_id,
                    trade_date=data['trade_date'],
                    start_time=None,
                    end_time=None,
                    instrument=data['instrument'],
                    direction=data['direction'],
                    contracts=data['contracts'],
                    entry_price=data['entry_price'],
                    stop_points=data['stop_points'],
                    trim1_points=data['trim1_points'],
                    trim2_points=data['trim2_points'],
                    trim1_hit=data['net_pnl'] > 0,  # Infer from result
                    trim2_hit=data['gross_pnl'] > data['trim1_points'] * tick_val,  # Approximation
                    market_regime=None,
                    notes=data['notes'],
                    gross_pnl=data['gross_pnl'],
                    net_pnl=data['net_pnl'],
                    max_drawdown=0.0,
                    mfe=0.0,
                    mae=0.0,
                    trades=1,
                    wins=win,
                    losses=loss,
                    breakeven_trades=be,
                    win_rate=1.0 if win else 0.0,
                    avg_risk=risk,
                    avg_reward=0.0,
                    rr_ratio=0.0,
                    largest_win=data['net_pnl'] if win else 0.0,
                    largest_loss=data['net_pnl'] if loss else 0.0,
                )
                
                self.db.update_session(record)
                self.recalculate_all_metrics()
                self.refresh_history()
                QMessageBox.information(self, "Success", "Trade updated successfully.")
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
            
            if starting_equity <= 0:
                QMessageBox.warning(self, "Invalid", "Starting equity must be positive.")
                return
            
            # Update fee configuration
            fee_config = FeeConfig(
                mnq_fee=self.fee_mnq_input.value(),
                mes_fee=self.fee_mes_input.value(),
                mgc_fee=self.fee_mgc_input.value(),
                nq_fee=self.fee_nq_input.value(),
                es_fee=self.fee_es_input.value(),
                gc_fee=self.fee_gc_input.value(),
                default_fee=self.fee_default_input.value(),
            )
            
            self.settings.starting_equity = starting_equity
            self.settings.fees = fee_config
            self.db.save_settings(self.settings)
            
            self.recalculate_all_metrics()
            
            QMessageBox.information(self, "Saved", "Settings and fees saved. Metrics recalculated.")
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
                    direction=row.get("direction", "Long"),
                    contracts=int(row.get("contracts", 2)),
                    entry_price=float(row.get("entry_price", 0)),
                    stop_points=float(row.get("stop_points", 0)),
                    trim1_points=float(row.get("trim1_points", 0)),
                    trim2_points=float(row.get("trim2_points", 0)),
                    trim1_hit=bool(row.get("trim1_hit", False)),
                    trim2_hit=bool(row.get("trim2_hit", False)),
                    market_regime=row.get("market_regime"),
                    notes=row.get("notes"),
                    gross_pnl=float(row.get("gross_pnl", row["net_pnl"])),
                    net_pnl=float(row["net_pnl"]),
                    max_drawdown=float(row.get("max_drawdown", 0)),
                    mfe=float(row.get("mfe", row["largest_win"] if "largest_win" in row else 0)),
                    mae=abs(float(row.get("mae", row["largest_loss"] if "largest_loss" in row else 0))),
                    trades=trades,
                    wins=wins,
                    losses=losses,
                    breakeven_trades=int(row.get("breakeven_trades", 0)),
                    win_rate=win_rate,
                    avg_risk=float(row.get("avg_risk", 0)),
                    avg_reward=float(row.get("avg_reward", 0)),
                    rr_ratio=float(row.get("rr_ratio", 0)),
                    largest_win=float(row.get("largest_win", 0)),
                    largest_loss=float(row.get("largest_loss", 0)),
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
                
                # Institutional Chart Style
                fig = Figure(figsize=(10, 5), facecolor='#000000') # Match App Bg
                ax = fig.add_subplot(111, facecolor='#000000')
                
                # Equity Curve
                ax.plot(equity.index, equity.values, color="#FFFFFF", linewidth=1.5, label='Equity')
                
                # Subtle fills
                ax.fill_between(equity.index, equity.values, self.settings.starting_equity, 
                               where=(equity.values >= self.settings.starting_equity),
                               interpolate=True, color='#2E8B57', alpha=0.1)
                ax.fill_between(equity.index, equity.values, self.settings.starting_equity, 
                               where=(equity.values < self.settings.starting_equity),
                               interpolate=True, color='#CD5C5C', alpha=0.1)

                ax.set_title("Portfolio Equity", fontsize=12, fontweight='500', color='#FFFFFF', pad=20)
                ax.set_xlabel("")
                # ax.set_ylabel("Equity ($)", color='#888888') # Minimalist: remove label if obvious
                
                # Grid
                ax.grid(True, linestyle='-', linewidth=0.5, color='#222222')
                
                # Axes
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
                ax.spines['left'].set_color('#222222')
                ax.spines['bottom'].set_color('#222222')
                
                ax.tick_params(colors='#888888', which='both')
                ax.ticklabel_format(style="plain", axis="y")
                
                # Moving Average
                if len(equity) > 20:
                    ma20 = equity.rolling(window=20).mean()
                    ax.plot(equity.index, ma20, color='#444444', linestyle='--', linewidth=1, label='20 MA')

                ax.axhline(y=self.settings.starting_equity, color='#444444', linestyle=':', label='Start')
                
                # Legend
                legend = ax.legend(loc='upper left', frameon=False)
                for text in legend.get_texts():
                    text.set_color("#888888")
                
                layout.addWidget(FigureCanvas(fig))
            except Exception as e:
                logger.error(f"Error rendering equity: {e}")
                layout.addWidget(QLabel(f"Error: {e}"))
        
        equity_container.setLayout(layout)
        self.equity_view.setWidget(equity_container)

    def render_drawdown(self) -> None:
        df = self._sessions_df()
        drawdown_container = QWidget()
        layout = QVBoxLayout()
        
        if df.empty:
            layout.addWidget(QLabel("No data yet."))
        else:
            # Institutional Chart Style
            fig = Figure(figsize=(10, 4), facecolor='#000000')
            ax = fig.add_subplot(111, facecolor='#000000')
            
            try:
                equity = self._get_equity_curve(df)
                full_range = pd.date_range(equity.index.min(), equity.index.max(), freq='D')
                equity = equity.reindex(full_range, method='ffill')
                
                peaks = equity.cummax()
                drawdown = (equity - peaks) / peaks * 100
            except Exception as e:
                layout.addWidget(QLabel(f"Error calculating drawdown: {e}"))
                drawdown_container.setLayout(layout)
                self.drawdown_view.setWidget(drawdown_container)
                return
            
            # Drawdown Zones (Very subtle)
            ax.fill_between(drawdown.index, 0, -5, color='#FFFF00', alpha=0.02)
            ax.fill_between(drawdown.index, -5, -10, color='#FFA500', alpha=0.02)
            ax.fill_between(drawdown.index, -10, -100, color='#FF0000', alpha=0.02)
            
            ax.plot(drawdown.index, drawdown.values, color='#CD5C5C', linewidth=1.5)
            ax.fill_between(drawdown.index, drawdown.values, 0, color='#CD5C5C', alpha=0.1)
            
            ax.set_title("Drawdown", fontsize=12, fontweight='500', color='#FFFFFF', pad=20)
            ax.set_xlabel("")
            ax.grid(True, linestyle='-', linewidth=0.5, color='#222222')
            
            # Axes
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#222222')
            ax.spines['bottom'].set_color('#222222')
            ax.tick_params(colors='#888888')
            
            max_dd = drawdown.min()
            ax.axhline(y=max_dd, color='#CD5C5C', linestyle=':', linewidth=1)
            ax.text(0.02, 0.05, f'Max: {max_dd:.1f}%', transform=ax.transAxes, 
                   fontsize=10, color='#CD5C5C', verticalalignment='bottom')
            
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
            # Institutional Chart Style
            fig = Figure(figsize=(8, 5), facecolor='#000000')
            ax = fig.add_subplot(111, facecolor='#000000')
            
            pnl = df["net_pnl"]
            ax.hist(pnl, bins=30, color='#00bcd4', alpha=0.7, edgecolor='#000000')
            ax.axvline(x=0, color='#FFFFFF', linestyle='--', linewidth=2, alpha=0.5)
            ax.axvline(x=pnl.mean(), color='#FFD700', linestyle='--', linewidth=1.5, 
                       alpha=0.8, label=f'Mean: ${pnl.mean():.2f}')
            
            ax.set_title("P&L Distribution", fontsize=12, fontweight='500', color='#FFFFFF')
            ax.set_xlabel("P&L ($)", color='#888888')
            ax.set_ylabel("Frequency", color='#888888')
            ax.grid(True, alpha=0.2, axis='y', color='#333')
            ax.tick_params(colors='#888888')
            
            # Axes
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['left'].set_color('#222')
            ax.spines['bottom'].set_color('#222')
            
            legend = ax.legend(frameon=False)
            for text in legend.get_texts(): text.set_color("#888888")
            
            layout.addWidget(FigureCanvas(fig))
        
        pnl_container.setLayout(layout)
        self.pnl_dist_view.setWidget(pnl_container)

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
            
            # Institutional Chart Style
            fig = Figure(figsize=(10, 8), facecolor='#000000')
            
            ax1 = fig.add_subplot(211, facecolor='#000000')
            ax1.plot(rolling_wr.index, rolling_wr.values * 100, color='#9ecbff', linewidth=2)
            ax1.axhline(y=50, color='#444', linestyle='--', alpha=0.5)
            ax1.set_title(f"Rolling Win Rate (window={window})", fontsize=12, fontweight='500', color='#FFFFFF')
            ax1.set_ylabel("Win Rate (%)", color='#888888')
            ax1.grid(True, alpha=0.2, color='#333')
            ax1.set_ylim(0, 100)
            ax1.tick_params(colors='#888888')
            for s in ax1.spines.values(): s.set_color('#222')
            ax1.spines['top'].set_visible(False)
            ax1.spines['right'].set_visible(False)
            
            ax2 = fig.add_subplot(212, facecolor='#000000')
            ax2.plot(rolling_exp.index, rolling_exp.values, color='#F0BB40', linewidth=2)
            ax2.axhline(y=0, color='#444', linestyle='--', alpha=0.5)
            ax2.set_title(f"Rolling Expectancy (window={window})", fontsize=12, fontweight='500', color='#FFFFFF')
            ax2.set_ylabel("Expectancy ($)", color='#888888')
            ax2.set_xlabel("Session Number", color='#888888')
            ax2.grid(True, alpha=0.2, color='#333')
            ax2.tick_params(colors='#888888')
            for s in ax2.spines.values(): s.set_color('#222')
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
            
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
            
            # Recalculate win rate excluding BE if preferred, but standard is (wins / total)
            # User Win Rate target 45.7% likely excludes BE or counts them? 
            # Usual convention: Win / Total. 
            win_rate = self.metrics.win_rate(returns) * 100
            
            expectancy = self.metrics.expectancy(returns)
            profit_factor = self.metrics.profit_factor(returns)
            max_dd = self.metrics.max_drawdown_equity(equity) * 100
            sharpe = self.metrics.sharpe(returns, trading_days)
            sortino = self.metrics.sortino(returns, trading_days)
            calmar = self.metrics.calmar_ratio(equity, trading_days)
            recovery = self.metrics.recovery_factor(equity)
            ann_ret, ann_vol = self.metrics.annualized_return_vol(returns, trading_days)
            
            # New Strategy Metrics
            total_trades = len(df)
            be_trades = df['breakeven_trades'].sum() if 'breakeven_trades' in df.columns else 0
            
            trim1_hits = df['trim1_hit'].sum() if 'trim1_hit' in df.columns else 0
            trim2_hits = df['trim2_hit'].sum() if 'trim2_hit' in df.columns else 0
            
            trim1_rate = (trim1_hits / total_trades * 100) if total_trades else 0
            run_rate = (trim2_hits / total_trades * 100) if total_trades else 0
            
            # Formatting
            sharpe_str = f"{sharpe:.3f}" if not np.isnan(sharpe) else "N/A"
            sortino_str = f"{sortino:.3f}" if not np.isnan(sortino) else "N/A"
            calmar_str = f"{calmar:.3f}" if not (np.isnan(calmar) or np.isinf(calmar)) else "N/A"
            recovery_str = f"{recovery:.3f}" if not (np.isnan(recovery) or np.isinf(recovery)) else "N/A"
            pf_str = f"{profit_factor:.3f}" if not np.isinf(profit_factor) else "∞"
            
            # Institutional Dashboard HTML
            stats_text = QLabel()
            stats_text.setWordWrap(True)
            stats_text.setOpenExternalLinks(True)
            
            # Colors
            c_accent = "#FFFFFF"
            c_label = "#888888"
            c_green = "#2E8B57" # SeaGreen
            c_red = "#CD5C5C" # IndianRed
            c_card_bg = "#111111"
            c_card_border = "#222222"
            
            # Helper for Card format
            def card(title, value, subtext="", color="#FFFFFF"):
                return f"""
                <div style='background-color: {c_card_bg}; border: 1px solid {c_card_border}; border-radius: 8px; padding: 16px; margin: 0px 10px 10px 0px; min-width: 200px;'>
                    <div style='color: {c_label}; font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px;'>{title}</div>
                    <div style='color: {color}; font-size: 24px; font-weight: 500; margin-top: 8px;'>{value}</div>
                    <div style='color: {c_label}; font-size: 11px; margin-top: 4px;'>{subtext}</div>
                </div>
                """
            
            # Data prep
            pnl_color = c_green if total_pnl >= 0 else c_red
            pnl_str = f"${total_pnl:,.2f}"
            ret_str = f"{total_return_pct:+.2f}%"
            
            dd_color = c_red if max_dd > 10 else c_label
            
            # Dashboard Grid
            dashboard_html = f"""
            <h2 style='color: {c_accent}; margin-bottom: 20px;'>Dashboard Overview</h2>
            
            <div style='display: flex; flex-direction: row; flex-wrap: wrap;'>
                {card("Portfolio Equity", f"${equity.iloc[-1]:,.2f}", "vs Starting Equity", c_accent)}
                {card("Net P&L", pnl_str, ret_str, pnl_color)}
                {card("Win Rate", f"{win_rate:.1f}%", f"{total_trades} Trades", c_accent)}
                {card("Profit Factor", pf_str, f"Avg Win ${avg_win:.0f}", c_accent)}
                {card("Max Drawdown", f"{max_dd:.2f}%", "Peak to Trough", dd_color)}
            </div>
            
            <h3 style='color: {c_accent}; margin-top: 30px; margin-bottom: 10px;'>Detailed Metrics</h3>
            <table style='width: 100%; border-collapse: collapse; color: #CCCCCC;'>
                <tr style='border-bottom: none;'>
                    <td style='padding: 8px; color: {c_label};'>Expectancy</td>
                    <td style='padding: 8px; text-align: right;'>${expectancy:.2f}</td>
                </tr>
                 <tr style='border-bottom: none;'>
                    <td style='padding: 8px; color: {c_label};'>Sharpe Ratio</td>
                    <td style='padding: 8px; text-align: right;'>{sharpe_str}</td>
                </tr>
                 <tr style='border-bottom: none;'>
                    <td style='padding: 8px; color: {c_label};'>Sortino Ratio</td>
                    <td style='padding: 8px; text-align: right;'>{sortino_str}</td>
                </tr>
                <tr style='border-bottom: none;'>
                    <td style='padding: 8px; color: {c_label};'>Breakeven Trades</td>
                    <td style='padding: 8px; text-align: right;'>{be_trades}</td>
                </tr>
                 <tr style='border-bottom: none;'>
                    <td style='padding: 8px; color: {c_label};'>Full Runner Rate</td>
                    <td style='padding: 8px; text-align: right;'>{run_rate:.1f}%</td>
                </tr>
            </table>

            <h3 style='color: {c_accent}; margin-top: 30px; margin-bottom: 10px;'>Instrument Performance</h3>
            """
            
            # Instruments
            by_instr = df.groupby("instrument")
            for instr, grp in by_instr:
                g_returns = pd.Series(grp["net_pnl"].values)
                t_pnl = g_returns.sum()
                t_wr = self.metrics.win_rate(g_returns) * 100
                t_count = len(grp)
                
                c_i = c_green if t_pnl >= 0 else c_red
                
                dashboard_html += f"""
                <div style='background-color: #0F0F0F; padding: 12px; margin-bottom: 4px; border-left: 3px solid {c_i}; border-radius: 2px;'>
                    <span style='color: #FFF; font-weight: 600; width: 60px; display: inline-block;'>{instr}</span>
                    <span style='color: {c_label}; margin-left: 20px;'>P&L: </span><span style='color: {c_i};'>${t_pnl:,.2f}</span>
                    <span style='color: {c_label}; margin-left: 20px;'>Win Rate: </span>{t_wr:.1f}% ({t_count})
                </div>
                """
            
            stats_text.setText(dashboard_html)
            layout.addWidget(stats_text)
            layout.addStretch()
            stats_container.setLayout(layout)
            self.stats_view.setWidget(stats_container)
def run() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.resize(1200, 750)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()