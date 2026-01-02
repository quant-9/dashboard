
import pandas as pd
import random
import numpy as np
from datetime import timedelta

total_sessions = 260
trade_win_rate = 0.457
daily_cap = 300.0
fees = 3.80 # Per trade (2 contracts)

# Trade Logic Values
# Outcome 1: Full TP
net_full_tp = 296.20
gross_full_tp = 300.0
# Outcome 2: Trim 1 + BE
net_trim1 = 96.20
gross_trim1 = 100.0
# Outcome 3: Stopped Out
net_stop = -43.80
gross_stop = -40.0

rows = []
start_date = pd.Timestamp("2024-01-01")
current_date = start_date

count = 0
while count < total_sessions:
    # Skip weekends
    if current_date.dayofweek > 4:
        current_date += timedelta(days=1)
        continue
        
    day_net = 0.0
    day_gross = 0.0
    day_trades = 0
    day_wins = 0
    day_losses = 0
    day_be = 0
    
    # Track gross win amounts for avg_reward calc
    day_gross_wins = 0.0
    
    # Random max trades for the day
    max_trades = random.choices([1, 2, 3, 4, 5, 6], weights=[0.1, 0.2, 0.2, 0.2, 0.2, 0.1])[0]
    
    session_notes = []
    trim1_hit_session = False
    trim2_hit_session = False
    
    largest_win_trade = 0.0
    largest_loss_trade = 0.0
    
    for _ in range(max_trades):
        if day_net >= daily_cap - 0.01:
            break
            
        day_trades += 1
        
        is_win = random.random() < trade_win_rate
        
        trade_net = 0.0
        trade_gross = 0.0
        outcome_str = ""
        
        if is_win:
            if random.random() < 0.5:
                trade_net = net_full_tp
                trade_gross = gross_full_tp
                outcome_str = "Full TP"
                trim1_hit_session = True
                trim2_hit_session = True
            else:
                trade_net = net_trim1
                trade_gross = gross_trim1
                outcome_str = "Trim 1 + BE"
                trim1_hit_session = True
        else:
            trade_net = net_stop
            trade_gross = gross_stop
            outcome_str = "Stopped Out"
            
        # Check Cap
        potential_total = day_net + trade_net
        
        if potential_total > daily_cap:
            # Partial fill to hit exact cap
            diff = daily_cap - day_net
            trade_net = diff
            trade_gross = trade_net + fees # approximate gross
            outcome_str = f"Target Hit (+${trade_net:.2f})"
            is_win = True
            trim1_hit_session = True
        
        day_net += trade_net
        day_gross += trade_gross
        
        if trade_net > 0:
            day_wins += 1
            day_gross_wins += trade_gross
            largest_win_trade = max(largest_win_trade, trade_net)
        elif trade_net < 0:
            day_losses += 1
            largest_loss_trade = min(largest_loss_trade, trade_net)
        else:
            day_be += 1
        
        # Approximate check if simple stop/trim outcome logic holds
        # "Wins" here means net profit > 0
        
        session_notes.append(outcome_str)
        
        if day_net >= daily_cap - 0.01:
            break
            
    # Metrics
    avg_risk = 40.0 # Standard risk per trade roughly
    avg_reward = (day_gross_wins / day_wins) if day_wins > 0 else 0.0
    rr = (avg_reward / avg_risk) if avg_risk > 0 else 0.0

    row = {
        "trade_date": current_date.date(),
        "instrument": "MNQ",
        "direction": "Long",
        "contracts": 2,
        "entry_price": 0.0,
        "stop_points": 10.0,
        "trim1_points": 50.0,
        "trim2_points": 100.0,
        "trim1_hit": trim1_hit_session,
        "trim2_hit": trim2_hit_session,
        "gross_pnl": day_gross,
        "net_pnl": day_net,
        "trades": day_trades,
        "wins": day_wins,
        "losses": day_losses,
        "breakeven_trades": day_be,
        "win_rate": (day_wins / day_trades) if day_trades > 0 else 0.0,
        "avg_risk": avg_risk,
        "avg_reward": avg_reward,
        "rr_ratio": rr,
        "trims": 2 if trim2_hit_session else (1 if trim1_hit_session else 0),
        "notes": ", ".join(session_notes),
        "largest_win": largest_win_trade,
        "largest_loss": largest_loss_trade,
        "max_drawdown": 0.0
    }
    
    rows.append(row)
    current_date += timedelta(days=1)
    count += 1

df = pd.DataFrame(rows)
df.to_csv("example_data.csv", index=False)
print(f"Generated {len(df)} sessions with Daily Cap logic (and fixed columns).")
