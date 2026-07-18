"""
backtest.py

Contains utilities for:
- Running strategy backtests
- Computing performance metrics
- Printing reports
"""

import pandas as pd
import numpy as np

# Run Backtest 
def run_backtest(df, initial_capital=100000):
    capital      = initial_capital
    position     = None       # holds current open trade
    trades       = []         # log of all completed trades
    equity_curve = []         # capital value at each candle

    for timestamp, row in df.iterrows():
        signal = row["signal"]
        price  = row["close"]

        # Entry — BUY signal and not already in a trade
        if signal == "BUY" and position is None:
            shares   = capital // price      # how many shares we can afford
            cost     = shares * price
            position = {
                "entry_time":  timestamp,
                "entry_price": price,
                "shares":      shares,
                "cost":        cost
            }
            capital -= cost                  # deduct cost from capital

        # Exit — SELL signal and currently holding a position
        elif signal == "SELL" and position is not None:
            proceeds = position["shares"] * price
            pnl      = proceeds - position["cost"]
            pnl_pct  = (pnl / position["cost"]) * 100

            trades.append({
                "entry_time":  position["entry_time"],
                "exit_time":   timestamp,
                "entry_price": position["entry_price"],
                "exit_price":  price,
                "shares":      position["shares"],
                "pnl":         pnl,
                "pnl_pct":     pnl_pct,
                "result":      "WIN" if pnl > 0 else "LOSS"
            })

            capital  += proceeds             # add sale proceeds to capital
            position  = None                 # clear the position

        # Track equity at every candle
        if position is not None:
            current_value = capital + (position["shares"] * price)
        else:
            current_value = capital

        equity_curve.append({
            "timestamp":    timestamp,
            "equity":       current_value,
            "signal":       signal
        })

    # If still holding at end of data — force close at last price
    if position is not None:
        last_price = df.iloc[-1]["close"]
        proceeds   = position["shares"] * last_price
        pnl        = proceeds - position["cost"]
        pnl_pct    = (pnl / position["cost"]) * 100

        trades.append({
            "entry_time":  position["entry_time"],
            "exit_time":   df.index[-1],
            "entry_price": position["entry_price"],
            "exit_price":  last_price,
            "shares":      position["shares"],
            "pnl":         pnl,
            "pnl_pct":     pnl_pct,
            "result":      "WIN" if pnl > 0 else "LOSS"
        })

    trades_df      = pd.DataFrame(trades)
    equity_df      = pd.DataFrame(equity_curve).set_index("timestamp")

    final_equity = (capital +
    (position["shares"] * df.iloc[-1]["close"])
    if position
    else capital
    )

    return trades_df, equity_df


#  Calculate Metrics
def calculate_metrics(trades_df, equity_df, initial_capital=100000):
    if trades_df.empty:
        return {}

    total_trades  = len(trades_df)
    wins          = trades_df[trades_df["result"] == "WIN"]
    losses        = trades_df[trades_df["result"] == "LOSS"]

    win_rate      = (len(wins) / total_trades) * 100
    avg_win       = wins["pnl_pct"].mean()   if not wins.empty   else 0
    avg_loss      = losses["pnl_pct"].mean() if not losses.empty else 0

    total_pnl     = trades_df["pnl"].sum()
    total_return  = (total_pnl / initial_capital) * 100

    # Risk/Reward Ratio
    rr_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    # Max Drawdown
    equity        = equity_df["equity"]
    rolling_max   = equity.cummax()
    drawdown      = (equity - rolling_max) / rolling_max * 100
    max_drawdown  = drawdown.min()

    # Sharpe Ratio (simplified — daily returns)
    equity_df["returns"] = equity_df["equity"].pct_change()
    returns = equity_df["returns"].dropna()

    if len(returns) > 1 and returns.std() > 0:
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
    else:
        sharpe = 0

    metrics = {
        "Total Trades":      total_trades,
        "Win Rate (%)":      round(win_rate, 2),
        "Total Return (%)":  round(total_return, 2),
        "Total PnL (₹)":     round(total_pnl, 2),
        "Avg Win (%)":       round(avg_win, 2),
        "Avg Loss (%)":      round(avg_loss, 2),
        "Risk/Reward":       round(rr_ratio, 2),
        "Max Drawdown (%)":  round(max_drawdown, 2),
        "Sharpe Ratio":      round(sharpe, 2)
    }

    return metrics


# Print Report 
def print_report(metrics, trades_df):
    print("\n" + "═"*40)
    print("      BACKTEST REPORT")
    print("═"*40)

    for key, value in metrics.items():
        print(f"  {key:<22} {value}")

    print("═"*40)

    if not trades_df.empty:
        print("\n── Trade Log ──")
        print(trades_df[[
            "entry_time", "exit_time",
            "entry_price", "exit_price",
            "pnl", "pnl_pct", "result"
        ]].to_string(index=False))


# Test Block 
if __name__ == "__main__":
    import datetime

    from fetch_data import login, fetch_candles
    from indicators import add_all_indicators
    from signals import generate_signals

    smart = login()
    if smart:
        today    = datetime.date.today()
        month_ago = today - datetime.timedelta(days=30)

        df = fetch_candles(
            smart, "2885", "FIVE_MINUTE",
            f"{month_ago} 09:15",
            f"{today} 15:30"
        )

        if df is not None:
            df = add_all_indicators(df)
            df = generate_signals(df)

            trades_df, equity_df = run_backtest(df)
            metrics = calculate_metrics(trades_df, equity_df)
            print_report(metrics, trades_df)