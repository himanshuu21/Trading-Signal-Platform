import os
import time
import pandas as pd
import pyotp
from dotenv import load_dotenv
from SmartApi import SmartConnect

# Load environment variables from .env
load_dotenv()

# Angel One API credentials
API_KEY = os.getenv("API_KEY")
CLIENT_CODE = os.getenv("CLIENT_CODE")
MPIN = os.getenv("MPIN")
TOTP_SECRET = os.getenv("TOTP_SECRET")

# Validate required environment variables
required = {
    "API_KEY": API_KEY,
    "CLIENT_CODE": CLIENT_CODE,
    "MPIN": MPIN,
    "TOTP_SECRET": TOTP_SECRET,
}

missing = [key for key, value in required.items() if not value]

if missing:
    raise ValueError(
        f"Missing environment variables: {', '.join(missing)}"
    )


def login():
    """
    Authenticate with Angel One SmartAPI.

    Returns:
        SmartConnect: Authenticated SmartConnect object.
        None: If authentication fails.
    """
    smart = SmartConnect(api_key=API_KEY)

    totp_code = pyotp.TOTP(TOTP_SECRET).now()
    session = smart.generateSession(CLIENT_CODE, MPIN, totp_code)

    if not session.get("status"):
        print(f"Login failed: {session.get('message', 'Unknown error')}")
        return None

    return smart


def fetch_candles(
    smart,
    symboltoken,
    interval,
    from_date,
    to_date,
    exchange="NSE",
):
    """
    Fetch historical OHLCV candle data.

    Args:
        smart (SmartConnect): Authenticated SmartAPI object.
        symboltoken (str): Angel One symbol token.
        interval (str): Candle interval (e.g., FIVE_MINUTE).
        from_date (str): Start datetime.
        to_date (str): End datetime.
        exchange (str): Exchange name.

    Returns:
        pandas.DataFrame | None
    """

    params = {
        "exchange": exchange,
        "symboltoken": symboltoken,
        "interval": interval,
        "fromdate": from_date,
        "todate": to_date,
    }

    try:
        response = smart.getCandleData(params)

        if not response.get("status"):
            print(f"Failed to fetch candles: {response.get('message')}")
            return None

        raw_data = response["data"]

        print("Last 5 raw candles:")
        for candle in raw_data[-5:]:
            print(candle)

        df = pd.DataFrame(
            raw_data,
            columns=[
                "datetime",
                "open",
                "high",
                "low",
                "close",
                "volume",
            ],
        )

        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)

        print(f"Successfully fetched {len(df)} candles.")

        return df

    except Exception as e:
        print(f"Error fetching candle data: {e}")
        return None


if __name__ == "__main__":
    smart = login()

    if smart:
        print("Connected to Angel One SmartAPI.")

        time.sleep(3)

        df = fetch_candles(
            smart=smart,
            symboltoken="2885",
            interval="FIVE_MINUTE",
            from_date="2026-07-01 09:15",
            to_date="2026-07-02 12:00",
        )

        if df is not None:
            print(df.head())