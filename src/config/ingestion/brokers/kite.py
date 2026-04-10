from pathlib import Path

from config.base import StorageConfig


class EditConfig:
    DATA_PATH = StorageConfig().tmp_root("kite")
    DB_PATH = DATA_PATH / "data.db"
    DB_CONN = f"sqlite:///{DB_PATH}"
    HIST_DATA_START_LOOKBACK = 3
    HIST_DATA_MONTHS_LOOKBACK = 15


class KiteConfig(EditConfig):
    NAME = "KITE"

    CREDENTIALS_PATH = Path("/home/parthgandhi/.conf/credentials/kite.ini")

    LOOKBACK_DAYS_LIMIT = None

    HISTORICAL_DATA_LIMIT_DAYS = {
        "minute": 30,
        "3minute": 90,
        "5minute": 90,
        "10minute": 90,
        "15minute": 180,
        "30minute": 180,
        "60minute": 365,
        "day": 2000,
    }

    API_RATE_LIMIT_SECONDS = {"quote": 1, "historical": 3, "order": 10, "others": 10}

    TICKER_LIMIT = {"max_tokens": 3000}

    TYP_INDICES = "indices"
    TYP_STOCKS = "stocks"

    FNO_STOCKS_PATH = "fno_stocks.csv"

    @staticmethod
    def get_db_tbl(data_type: str, frequency: str, failed_tbl: bool):
        prefix = "failed_" if failed_tbl else ""
        return f"{prefix}kite_{data_type}_ohlcv_{frequency}"
