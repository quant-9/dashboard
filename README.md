# Trading Analytics Dashboard

A local, Python-based **post-trade analytics dashboard** for traders who want to track performance, visualize equity curves, drawdowns, and analyze trading statistics over time.

This project is **not** a live trading platform and does **not** connect to any broker or exchange.  
All data is entered manually and stored locally.

---

## Features

- Log daily trading sessions
- Track PnL, wins, losses, risk, reward, and trade count
- Equity curve visualization
- Drawdown (underwater) chart
- PnL distribution histogram
- Rolling performance metrics
- Local SQLite database (no cloud, no APIs)
- Desktop GUI built with PyQt

---

## Requirements

- Python **3.9 or newer**
- macOS, Linux, or Windows
- Git (recommended)

---

## Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/quant-9/dashboard.git
cd dashboard
2. Create a virtual environment
macOS / Linux

bash
Copy code
python3 -m venv .venv
source .venv/bin/activate
Windows (PowerShell)

powershell
Copy code
python -m venv .venv
.venv\Scripts\Activate.ps1
You should see (.venv) in your terminal after activation.

3. Install dependencies
bash
Copy code
pip install -r requirements.txt
4. Run the application
bash
Copy code
python ui_app.py
The Trading Analytics Dashboard window should open.

How to Use
Open the app

Go to Log Trade

Enter your session data:

Net PnL

Trades

Wins / losses

Risk / reward

Click Save Session

Use the sidebar to view:

Equity curve

Drawdowns

PnL distribution

Rolling metrics

Trade history

All data is saved locally in an SQLite database.

Project Structure
bash
Copy code
dashboard/
│
├── ui_app.py              # Main GUI application
├── database.py            # SQLite database logic
├── metrics_engine.py      # Performance & risk calculations
├── models.py              # Data models
├── visualizations.py      # Charts and plots
├── requirements.txt       # Python dependencies
└── README.md              # Project documentation
Data Storage
Trading data is stored locally in an SQLite database (*.db)

No external services are used

Deleting the database file resets all data

Notes
This is a manual journal and analytics tool

No broker integration

No real-time market data

Designed for post-trade review and performance tracking

Disclaimer
This software is provided for educational and analytical purposes only.
It does not constitute financial advice or trading recommendations.

Use at your own risk.

yaml
Copy code

---

## Add it to GitHub

Run:
```bash
git add README.md
git commit -m "Add README with setup and usage instructions"
git push
