import argparse
import logging
from datetime import datetime

import polars as pl

from computation.compute import gen_market_dashboard_data
from config.base import StorageConfig
from config.computation.compute import ComputeConfig
from config.ingestion.brokers import KiteConfig
from config.ingestion.data_sources import NSEConfig
from ingestion import fetch_nse_indices
from utils import setup_logger

logger = logging.getLogger(__name__)

setup_logger()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Market Dashboard Computation")
    parser.add_argument("--end_date", required=True, help="End date YYYY-MM-DD")
    args = parser.parse_args()

    # get indices constituents
    nse_indices_df = fetch_nse_indices(download_flag=False)

    # get industry classification data
    nse_ind_table_id = NSEConfig.get_db_tbl(
        tbl_name=NSEConfig.CLASSIFICATION_TABLE_ID, failed_tbl=False
    )

    query = f"""
    select max(timestamp) from {nse_ind_table_id}
    """
    max_timestamp = pl.read_database_uri(query=query, uri=NSEConfig.DB_CONN).item(0, 0)

    logger.info(f"TimeStamp usef for NSE Industry Classification: {max_timestamp}")

    query = f"""
    select * from {nse_ind_table_id}
    where timestamp = '{max_timestamp}'
    """

    nse_ind_df = pl.read_database_uri(query=query, uri=NSEConfig.DB_CONN)

    # Get Stock & Indices Data
    stock_table_id = KiteConfig.get_db_tbl(
        data_type=KiteConfig.TYP_STOCKS, frequency="day", failed_tbl=False
    )
    indices_table_id = KiteConfig.get_db_tbl(
        data_type=KiteConfig.TYP_INDICES, frequency="day", failed_tbl=False
    )

    query = f"""
        select *
        from {stock_table_id}
    """

    stocks_df = pl.read_database_uri(query=query, uri=KiteConfig.DB_CONN)

    query = f"""
        select *
        from {indices_table_id}
    """

    indices_df = pl.read_database_uri(query=query, uri=KiteConfig.DB_CONN)

    # Get Market DashBoard Data

    mkt_db_stocks_df, mkt_db_indices_df = gen_market_dashboard_data(
        nse_indices_df=nse_indices_df,
        indices_df=indices_df,
        stocks_df=stocks_df,
        nse_ind_df=nse_ind_df,
        scan_date=datetime.strptime(args.end_date, "%Y-%m-%d"),
    )

    save_path = StorageConfig().store_root(ComputeConfig.FOLDER_NAME, args.end_date)

    mkt_db_stocks_df.collect().write_csv(save_path / ComputeConfig.MKT_DB_STOCKS_PATH)
    mkt_db_indices_df.collect().write_csv(save_path / ComputeConfig.MKT_DB_INDICES_PATH)
