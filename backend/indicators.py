"""
Technical Indicators Module

This module computes commonly used technical indicators
such as SMA, EMA, RSI, MACD, Bollinger Bands, ATR, ADX,
VWAP, and Volume Moving Average for market analysis.
"""

import pandas as pd
import numpy as np


def add_sma(df, period=20, column="close"):
    """
    Add Simple Moving Average (SMA).

    Args:
        df (DataFrame): OHLCV data.
        period (int): Moving average period.
        column (str): Price column.

    Returns:
        DataFrame
    """
    df[f"sma_{period}"] = df[column].rolling(window=period).mean()
    return df


def add_ema(df, period=20, column="close"):
    """
    Add Exponential Moving Average (EMA).
    """
    df[f"ema_{period}"] = df[column].ewm(span=period, adjust=False).mean()
    return df


def add_rsi(df, period=14, column="close"):
    """
    Calculate Relative Strength Index (RSI).
    """
    delta = df[column].diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(span=period, adjust=False).mean()
    avg_loss = loss.ewm(span=period, adjust=False).mean()

    rs = avg_gain / avg_loss

    df["rsi"] = 100 - (100 / (1 + rs))

    return df


def add_macd(df, fast=12, slow=26, signal=9, column="close"):
    """
    Calculate Moving Average Convergence Divergence (MACD).
    """
    ema_fast = df[column].ewm(span=fast, adjust=False).mean()
    ema_slow = df[column].ewm(span=slow, adjust=False).mean()

    df["macd"] = ema_fast - ema_slow
    df["macd_signal"] = df["macd"].ewm(span=signal, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    return df


def add_bollinger(df, period=20, std_dev=2, column="close"):
    """
    Calculate Bollinger Bands.
    """
    df["bb_middle"] = df[column].rolling(window=period).mean()

    rolling_std = df[column].rolling(window=period).std()

    df["bb_upper"] = df["bb_middle"] + (std_dev * rolling_std)
    df["bb_lower"] = df["bb_middle"] - (std_dev * rolling_std)

    df["bb_width"] = df["bb_upper"] - df["bb_lower"]
    df["bb_percent"] = (df[column] - df["bb_lower"]) / df["bb_width"]

    return df


def add_atr(df, period=14):
    """
    Calculate Average True Range (ATR).
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    df["atr"] = true_range.ewm(span=period, adjust=False).mean()

    return df


def add_adx(df, period=14):
    """
    Calculate Average Directional Index (ADX).
    """
    high = df["high"]
    low = df["low"]
    close = df["close"]

    # Directional Movement
    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

    # True Range
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr_smooth = true_range.ewm(span=period, adjust=False).mean()
    plus_dm_smooth = plus_dm.ewm(span=period, adjust=False).mean()
    minus_dm_smooth = minus_dm.ewm(span=period, adjust=False).mean()

    df["adx_plus_di"] = 100 * (plus_dm_smooth / atr_smooth)
    df["adx_minus_di"] = 100 * (minus_dm_smooth / atr_smooth)

    di_diff = (df["adx_plus_di"] - df["adx_minus_di"]).abs()
    di_sum = (df["adx_plus_di"] + df["adx_minus_di"]).abs()

    dx = 100 * (di_diff / di_sum)
    df["adx"] = dx.ewm(span=period, adjust=False).mean()

    return df


def add_vwap(df):
    """
    Calculate Volume Weighted Average Price (VWAP).
    """
    typical_price = (df["high"] + df["low"] + df["close"]) / 3

    df["tp_vol"] = typical_price * df["volume"]

    df["vwap"] = (
        df.groupby(df.index.normalize())["tp_vol"].transform(lambda x: x.cumsum())
        / df.groupby(df.index.normalize())["volume"].transform(lambda x: x.cumsum())
    )

    df.drop(columns=["tp_vol"], inplace=True)

    return df


def add_volume_ma(df, period=20):
    """
    Calculate Volume Moving Average.
    """
    df["volume_ma"] = df["volume"].rolling(window=period).mean()
    df["volume_ratio"] = df["volume"] / df["volume_ma"]

    return df


def add_all_indicators(df):
    """
    Apply all supported technical indicators.
    """

    df = add_sma(df, period=20)
    df = add_sma(df, period=50)

    df = add_ema(df, period=20)
    df = add_ema(df, period=50)

    df = add_rsi(df, period=14)
    df = add_macd(df)

    df = add_bollinger(df, period=20)
    df = add_atr(df, period=14)
    df = add_adx(df, period=14)

    df = add_vwap(df)
    df = add_volume_ma(df, period=20)

    # Remove rows where rolling indicators
    # cannot be computed.
    df.dropna(inplace=True)

    return df


if __name__ == "__main__":
    import time

    from fetch_data import fetch_candles, login

    smart = login()

    time.sleep(3)

    if smart:
        df = fetch_candles(
            smart,
            symboltoken="2885",
            interval="FIVE_MINUTE",
            from_date="2026-07-01 09:15",
            to_date="2026-07-02 12:00",
        )

        if df is not None:
            df = add_all_indicators(df)

            print(df.tail())
            print("\nColumns added:")
            print(list(df.columns))