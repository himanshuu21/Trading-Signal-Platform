"""
Trading Signal Generation Module

This module combines multiple technical indicators
using a voting-based approach to generate BUY, SELL,
or NEUTRAL trading signals.
"""

from indicators import add_all_indicators

# ==========================
# Strategy Thresholds
# ==========================

RSI_BUY_THRESHOLD = 35
RSI_SELL_THRESHOLD = 65

ADX_THRESHOLD = 25

HIGH_VOLUME_RATIO = 1.5
LOW_VOLUME_RATIO = 0.7

BUY_SIGNAL_THRESHOLD = 3
SELL_SIGNAL_THRESHOLD = -3


# ==========================
# Individual Indicator Votes
# ==========================

def vote_rsi(row):
    """
    RSI vote.

    Oversold -> BUY
    Overbought -> SELL
    """
    if row["rsi"] < RSI_BUY_THRESHOLD:
        return 1
    elif row["rsi"] > RSI_SELL_THRESHOLD:
        return -1
    return 0


def vote_macd(row):
    """
    MACD crossover vote.
    """
    if row["macd"] > row["macd_signal"]:
        return 1
    elif row["macd"] < row["macd_signal"]:
        return -1
    return 0


def vote_bollinger(row):
    """
    Bollinger Band vote.
    """
    if row["bb_percent"] < 0.2:
        return 1
    elif row["bb_percent"] > 0.8:
        return -1
    return 0


def vote_ema(row):
    """
    EMA crossover vote.
    """
    if row["ema_20"] > row["ema_50"]:
        return 1
    elif row["ema_20"] < row["ema_50"]:
        return -1
    return 0


def vote_sma(row):
    """
    SMA crossover vote.
    """
    if row["sma_20"] > row["sma_50"]:
        return 1
    elif row["sma_20"] < row["sma_50"]:
        return -1
    return 0


def vote_vwap(row):
    """
    VWAP vote.
    """
    if row["close"] > row["vwap"]:
        return 1
    elif row["close"] < row["vwap"]:
        return -1
    return 0


def vote_volume(row):
    """
    Volume confirmation vote.
    """
    if row["volume_ratio"] > HIGH_VOLUME_RATIO:
        return 1
    elif row["volume_ratio"] < LOW_VOLUME_RATIO:
        return -1
    return 0


# ==========================
# Market Regime Filter
# ==========================

def regime_gate(row):
    """
    Allow trades only when the market
    is trending and supported by volume.
    """
    trend_exists = row["adx"] > ADX_THRESHOLD
    volume_confirms = row["volume_ratio"] > 1.0

    return trend_exists and volume_confirms


# ==========================
# Trading Signal Generator
# ==========================

def generate_signal(row):
    """
    Generate BUY, SELL or NEUTRAL signal
    using a multi-indicator voting strategy.
    """

    if not regime_gate(row):
        return "NEUTRAL"

    signal_score = sum(
        [
            vote_rsi(row),
            vote_macd(row),
            vote_bollinger(row),
            vote_ema(row),
            vote_sma(row),
            vote_vwap(row),
            vote_volume(row),
        ]
    )

    if signal_score >= BUY_SIGNAL_THRESHOLD:
        return "BUY"

    elif signal_score <= SELL_SIGNAL_THRESHOLD:
        return "SELL"

    return "NEUTRAL"


# ==========================
# Apply Signals
# ==========================

def generate_signals(df):
    """
    Generate trading signals
    for every row in the DataFrame.
    """

    # Remove rows where one or more
    # indicators are unavailable.
    result = df.dropna(
        subset=[
            "rsi",
            "macd",
            "macd_signal",
            "bb_percent",
            "ema_20",
            "ema_50",
            "sma_20",
            "sma_50",
            "vwap",
            "volume_ratio",
            "adx",
        ]
    ).copy()

    result["signal"] = result.apply(generate_signal, axis=1)

    return result