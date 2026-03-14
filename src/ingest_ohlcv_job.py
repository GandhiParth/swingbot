import argparse
import logging
from datetime import datetime, timedelta

from config.ingestion.brokers import KiteConfig
from ingestion import fetch_nse_indices, fetch_nse_indices_data, fetch_nse_stocks_data
from ingestion.brokers.kite import KiteLogin, fetch_instruments
from utils import setup_logger, to_datetime_str

logger = logging.getLogger(__name__)
setup_logger()


def _get_start_lookback_date(end_date: str) -> tuple[str, str]:

    _date_obj = datetime.strptime(end_date, "%Y-%m-%d")

    start_date = _date_obj - timedelta(days=KiteConfig.HIST_DATA_START_LOOKBACK * 30)

    lookback_date = start_date - timedelta(
        days=KiteConfig.HIST_DATA_MONTHS_LOOKBACK * 30
    )

    start_date = start_date.strftime("%Y-%m-%d")
    lookback_date = lookback_date.strftime("%Y-%m-%d")

    logger.info(
        f"LOOKBACK DATE: {lookback_date} | START_DATE: {start_date} | END_DATE: {end_date}"
    )

    return start_date, lookback_date


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Ingestion Pipeline")
    parser.add_argument("--fetch", action="store_true", help="Fetch NSE Indices")
    parser.add_argument("--end_date", required=True, help="End date YYYY-MM-DD")
    args = parser.parse_args()

    nse_indices_df = fetch_nse_indices(download_flag=args.fetch)

    kite = KiteLogin(credentials_path=KiteConfig.CREDENTIALS_PATH)()
    nse_kite_df = fetch_instruments(kite=kite, exchange="NSE").select(
        "instrument_token", "symbol", "name", "segment"
    )

    end_date = args.end_date
    _, lookback_date = _get_start_lookback_date(end_date=end_date)

    end_date = to_datetime_str(end_date)
    lookback_date = to_datetime_str(lookback_date)

    fetch_nse_indices_data(
        kite=kite,
        instruments_df=nse_kite_df,
        nse_indices_df=nse_indices_df,
        start_date=lookback_date,
        end_date=end_date,
        frequency="day",
    )

    fetch_nse_stocks_data(
        kite=kite,
        instruments_df=nse_kite_df,
        start_date=lookback_date,
        end_date=end_date,
        frequency="day",
    )

#     fetch_nse_industry_classification(
#     ins_df=nse_kite_df.sample(100), fetch_date="2026-03-05"
# )
