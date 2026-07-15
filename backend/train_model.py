"""
Model Training Script

Fetches historical market data, computes technical indicators,
generates trading signals, and trains the Random Forest model.
"""

import datetime

from fetch_data import login, fetch_candles
from indicators import add_all_indicators
from signals import generate_signals
from ml import train_full_pipeline

# Training Configuration
SYMBOL_TOKEN = "2885"          # RELIANCE
INTERVAL = "FIVE_MINUTE"
TRAINING_DAYS = 60


def main():
    """Run the complete model training pipeline."""

    smart = login()

    if smart is None:
        print("Failed to login to Angel One.")
        return

    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=TRAINING_DAYS)

    print(f"Fetching {TRAINING_DAYS} days of historical data...")

    df = fetch_candles(
        smart=smart,
        symboltoken=SYMBOL_TOKEN,
        interval=INTERVAL,
        from_date=f"{start_date} 09:15",
        to_date=f"{today} 15:30",
    )

    if df is None:
        print("Failed to fetch market data.")
        return

    print("Calculating technical indicators...")
    df = add_all_indicators(df)

    print("Generating trading signals...")
    df = generate_signals(df)

    print("Training ML model...")
    model, scaler = train_full_pipeline(df)

    if model is not None:
        print("\n✅ Model training completed successfully!")
    else:
        print("\n❌ Model training failed.")


if __name__ == "__main__":
    main()