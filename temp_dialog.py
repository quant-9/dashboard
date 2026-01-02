
class EditSessionDialog(QDialog):
    def __init__(self, data: dict, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Edit Trade")
        self.setFixedWidth(400)
        self.data = data
        self._build_ui()
        
    def _build_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        form = QFormLayout()
        form.setSpacing(12)
        
        self.date = QDateEdit()
        self.date.setCalendarPopup(True)
        d = QDate.fromString(self.data.get('trade_date'), "yyyy-MM-dd")
        if not d.isValid(): d = QDate.currentDate()
        self.date.setDate(d)
        
        self.instrument = QComboBox()
        self.instrument.addItems(INSTRUMENTS)
        self.instrument.setCurrentText(self.data.get('instrument', 'NQ'))
        
        self.direction = QComboBox()
        self.direction.addItems(["Long", "Short"])
        self.direction.setCurrentText(self.data.get('direction', 'Long'))
        
        self.contracts = QSpinBox()
        self.contracts.setRange(2, 100)
        self.contracts.setSingleStep(2)
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
        
        self.net_pnl = QDoubleSpinBox()
        self.net_pnl.setRange(-1000000.0, 1000000.0)
        self.net_pnl.setPrefix("$")
        self.net_pnl.setValue(self.data.get('net_pnl', 0.0))
        
        self.notes = QTextEdit()
        self.notes.setMaximumHeight(60)
        self.notes.setText(self.data.get('notes', ''))
        
        form.addRow("Date", self.date)
        form.addRow("Instrument", self.instrument)
        form.addRow("Direction", self.direction)
        form.addRow("Contracts", self.contracts)
        form.addRow("Stop (pts)", self.stop_points)
        form.addRow("Trim 1", self.trim1_points)
        form.addRow("Trim 2", self.trim2_points)
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
            'net_pnl': self.net_pnl.value(),
            'notes': self.notes.toPlainText(),
            # preserve original or defaults logic
            'entry_price': 0.0
        }
