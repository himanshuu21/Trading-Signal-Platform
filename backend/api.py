"""
FastAPI Backend

Provides REST API endpoints for:
- Real-time trading signals
- Historical candle data
- Technical indicators
- Backtesting
- Health monitoring
"""

import datetime
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from ml import load_model, predict_signal_quality
from decision_engine import get_recommendation

from backtest import calculate_metrics, run_backtest
from fetch_data import fetch_candles, login
from indicators import add_all_indicators
from signals import generate_signals
from pathlib import Path

DEFAULT_INTERVAL = "FIVE_MINUTE"
DEFAULT_LOOKBACK_DAYS = 7
BACKTEST_LOOKBACK_DAYS = 30
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
BACKEND_DIR = Path(__file__).resolve().parent
MODEL_DIR = BACKEND_DIR / "model"
MODEL_PATH = BASE_DIR / "backend" / "model" / "model.pkl"
MODEL, SCALER = load_model()

# ── App Setup 
app = FastAPI(
    title="Stock Trading Signal API",
    description="Real-time trading signals using Angel One SmartAPI",
    version="1.0.0"
)

# ── CORS — allows frontend to talk to backend 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ── Mount frontend folder 
# NEW — only mounts if folder exists
import os
app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static"
)
# ── Stock Token Map 
STOCKS = {
    "RELIANCE": "2885",
    "TCS":      "11536",
    "INFY":     "1594",
    "HDFCBANK": "1333",
    "SBIN":     "3045"
}

# ── Login Once (cached) 
_smart = None

def get_smart():
    global _smart
    if _smart is None:
        _smart = login()
    return _smart

# ── Helper — Fetch + Process 
def get_processed_df(stock_name, days=DEFAULT_LOOKBACK_DAYS):
    token = STOCKS.get(stock_name.upper())
    if not token:
        raise HTTPException(
            status_code=404,
            detail=f"Stock '{stock_name}' not found"
        )

    smart = get_smart()
    if not smart:
        raise HTTPException(
            status_code=500,
            detail="Angel One login failed"
        )

    today = datetime.date.today()
    from_day = today - datetime.timedelta(days=days)

    df = fetch_candles(
        smart,
        token,
        DEFAULT_INTERVAL,
        f"{from_day} 09:15",
        f"{today} 15:30"
    )

    if df is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to fetch candle data"
        )

    # Clean data
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    df = df[df["volume"] > 100]

    # Debug
    print("After fetch")
    print(df.tail())

    # Indicators
    df = add_all_indicators(df)

    print("After indicators")
    print(df.tail())

    # Signals
    df = generate_signals(df)

    print("After signals")
    print(df.tail())

    # Return only recent candles
    return df.tail(100)


# 
#  API ENDPOINTS
# 

# ── Serve Frontend 
@app.get("/")
def serve_frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


# ── Health Check 
@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "message": "Trading Signal API is running",
        "time": datetime.datetime.now().strftime("%H:%M:%S")
    }


# ── Get Available Stocks 
@app.get("/api/stocks")
def get_stocks():
    return {"stocks": list(STOCKS.keys())}


# ── Get Current Signal 
@app.get("/api/signal/{stock_name}")
def get_signal(stock_name: str):
    df     = get_processed_df(stock_name, days=7)
    latest = df.iloc[-1]

    # Evaluate BUY signals using the trained ML model.
    ml_result = None
    if latest["signal"] == "BUY" and MODEL_PATH.exists():
        try:
            from ml import load_model, predict_signal_quality
            model, scaler = load_model()
            ml_result     = predict_signal_quality(model, scaler, latest)
        except Exception as e:
            ml_result = None

    return {
        "stock":        stock_name.upper(),
        "timestamp":    str(df.index[-1]),
        "price":        round(float(latest["close"]), 2),
        "signal":       latest["signal"],
        "indicators": {
            "rsi":          round(float(latest["rsi"]),          2),
            "macd":         round(float(latest["macd"]),         4),
            "macd_signal":  round(float(latest["macd_signal"]),  4),
            "macd_hist":    round(float(latest["macd_hist"]),    4),
            "adx":          round(float(latest["adx"]),          2),
            "atr":          round(float(latest["atr"]),          2),
            "bb_upper":     round(float(latest["bb_upper"]),     2),
            "bb_lower":     round(float(latest["bb_lower"]),     2),
            "bb_percent":   round(float(latest["bb_percent"]),   4),
            "vwap":         round(float(latest["vwap"]),         2),
            "ema_20":       round(float(latest["ema_20"]),       2),
            "ema_50":       round(float(latest["ema_50"]),       2),
            "sma_20":       round(float(latest["sma_20"]),       2),
            "sma_50":       round(float(latest["sma_50"]),       2),
            "volume_ratio": round(float(latest["volume_ratio"]), 2)
        },
        "ml": ml_result
    }


# ── Get Recent Signals Table 
@app.get("/api/signals/{stock_name}")
def get_recent_signals(stock_name: str, limit: int = 20):
    df = get_processed_df(stock_name, days=DEFAULT_LOOKBACK_DAYS)

    signals_df = df[df["signal"] != "NEUTRAL"][
        ["close", "rsi", "macd", "adx", "volume_ratio", "signal"]
    ].tail(limit).sort_index(ascending=False)

    records = []
    for timestamp, row in signals_df.iterrows():
        records.append({
            "time":         str(timestamp),
            "price":        round(float(row["close"]),        2),
            "rsi":          round(float(row["rsi"]),          1),
            "macd":         round(float(row["macd"]),         4),
            "adx":          round(float(row["adx"]),          1),
            "volume_ratio": round(float(row["volume_ratio"]), 2),
            "signal":       row["signal"]
        })

    return {"stock": stock_name.upper(), "signals": records}


# ── Get Backtest Results 
@app.get("/api/backtest/{stock_name}")
def get_backtest(stock_name: str, capital: int = 100000):
    df = get_processed_df(
    stock_name,
    days=BACKTEST_LOOKBACK_DAYS
    )

    trades_df, equity_df = run_backtest(df, initial_capital=capital)
    metrics = calculate_metrics(trades_df, equity_df, initial_capital=capital)

    if not metrics:
        return {
            "stock":   stock_name.upper(),
            "capital": capital,
            "metrics": None,
            "trades":  []
        }

    trades = []
    if not trades_df.empty:
        for _, row in trades_df.iterrows():
            trades.append({
                "entry_time":  str(row["entry_time"]),
                "exit_time":   str(row["exit_time"]),
                "entry_price": round(float(row["entry_price"]), 2),
                "exit_price":  round(float(row["exit_price"]),  2),
                "pnl":         round(float(row["pnl"]),         2),
                "pnl_pct":     round(float(row["pnl_pct"]),     2),
                "result":      row["result"]
            })

    # Equity curve — downsample to 100 points for frontend
    equity_sample = equity_df["equity"].resample("1h").last().dropna()
    equity_curve  = [
        {"time": str(t), "value": round(float(v), 2)}
        for t, v in equity_sample.items()
    ]

    return {
        "stock":        stock_name.upper(),
        "capital":      capital,
        "metrics":      metrics,
        "trades":       trades,
        "equity_curve": equity_curve
    }


# ── Get Candle Data For Chart 
@app.get("/api/candles/{stock_name}")
def get_candles(stock_name: str):
    df = get_processed_df(stock_name, days=7)

    candles = []
    for timestamp, row in df.iterrows():
        candles.append({
            "time":   str(timestamp),
            "open":   round(float(row["open"]),  2),
            "high":   round(float(row["high"]),  2),
            "low":    round(float(row["low"]),   2),
            "close":  round(float(row["close"]), 2),
            "volume": int(row["volume"]),
            "signal": row["signal"]
        })

    return {"stock": stock_name.upper(), "candles": candles}


@app.get("/api/predict/{stock_name}")
def predict(stock_name: str):

    df = get_processed_df(stock_name)

    latest = df.iloc[-1]

    # Rule Engine
    rule_signal = latest["signal"]

    # ML Prediction
    prediction = predict_signal_quality(
        MODEL,
        SCALER,
        latest
    )

    # Decision Engine
    decision = get_recommendation(
        rule_signal,
        prediction["prediction"],
        prediction["confidence"]
    )

    return {
        "stock": stock_name.upper(),

        "price": round(float(latest["close"]), 2),

        "rule_signal": rule_signal,

        "ml_prediction": (
            "UP"
            if prediction["prediction"] == 1
            else "DOWN"
        ),

        "confidence": prediction["confidence"],

        "decision": {
            "recommendation": decision.recommendation,
            "risk": decision.risk,
            "agreement": decision.agreement,
            "score": decision.score,
            "reasons": decision.reasons
        },

        "timestamp": str(latest.name)
    }