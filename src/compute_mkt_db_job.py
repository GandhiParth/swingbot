import argparse
import logging
from datetime import datetime, timedelta

import polars as pl

from computation.compute import (
    cal_stocks_rs,
    gen_market_breadth_data,
    gen_market_dashboard_data,
    gen_scanner_data,
    gen_short_scanner_data,
    cal_dispersion_score,
)
from computation.market_breadth import compute_breadth
from config.base import StorageConfig
from config.computation.compute import ComputeConfig
from config.ingestion.brokers import KiteConfig
from config.ingestion.data_sources import NSEConfig
from ingestion import fetch_nse_indices
from utils import setup_logger

logger = logging.getLogger(__name__)

setup_logger()


def _write_scan_dict(res, save_path):
    res["basic_scan_df"].write_csv(save_path / ComputeConfig.BASIC_SCAN_PATH)
    res["basic_filter_df"].write_csv(save_path / ComputeConfig.BASIC_FILTER_PATH)
    res["adr_filter_df"].write_csv(save_path / ComputeConfig.ADR_FILTER_PATH)
    res["pullback_filter_df"].write_parquet(
        save_path / ComputeConfig.PULLBACK_FILTER_PARQ_PATH
    )
    res["final_res"].write_csv(save_path / ComputeConfig.FILTER_RESULT_PATH)


def _write_short_scan_dict(res, save_path):
    res["basic_scan_df"].write_csv(save_path / ComputeConfig.BASIC_SCAN_PATH)
    res["basic_filter_df"].write_csv(save_path / ComputeConfig.BASIC_SHORT_FILTER_PATH)
    res["adr_filter_df"].write_csv(save_path / ComputeConfig.ADR_SHORT_FILTER_PATH)
    res["final_res"].write_csv(save_path / ComputeConfig.FILTER_SHORT_RESULT_PATH)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Market Dashboard Computation")
    parser.add_argument("--end_date", required=True, help="End date YYYY-MM-DD")
    parser.add_argument("--adr_cutoff", default=3, help="ADR Cutoff for Filter")
    args = parser.parse_args()

    end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    start_date = end_date - timedelta(days=KiteConfig.HIST_DATA_START_LOOKBACK * 30)

    save_path = StorageConfig().store_root(ComputeConfig.FOLDER_NAME, args.end_date)

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
        scan_date=end_date,
    )

    mkt_db_stocks_df.sink_csv(save_path / ComputeConfig.MKT_DB_STOCKS_PATH)
    mkt_db_indices_df.sink_csv(save_path / ComputeConfig.MKT_DB_INDICES_PATH)

    # Get Market Breadth Data

    mkt_breadth_df = gen_market_breadth_data(stocks_df=stocks_df)
    mkt_breadth_df.sink_csv(save_path / ComputeConfig.MKT_BREADTH_PATH)

    mkt_regime_df = compute_breadth(data=stocks_df)
    mkt_regime_df.sink_csv(save_path / ComputeConfig.MKT_REGIME_PATH)

    ## Get Scanners & Filters
    scanner_df_dict = gen_scanner_data(
        stocks_df=stocks_df,
        nse_ind_df=nse_ind_df,
        start_date=start_date,
        end_date=end_date,
        adr_cutoff=float(args.adr_cutoff),
    )
    _write_scan_dict(res=scanner_df_dict, save_path=save_path)

    short_scanner_df_dict = gen_short_scanner_data(
        stocks_df=stocks_df,
        nse_ind_df=nse_ind_df,
        start_date=start_date,
        end_date=end_date,
        adr_cutoff=float(args.adr_cutoff),
    )
    _write_short_scan_dict(res=short_scanner_df_dict, save_path=save_path)

    ## Calculate Stocks RS
    stocks_rs_df = cal_stocks_rs(
        indices_df=indices_df.lazy().filter(pl.col("symbol") == ComputeConfig.RS_INDEX),
        stocks_df=stocks_df,
        end_date=end_date,
    )
    stocks_rs_df.sink_csv(save_path / ComputeConfig.STOCKS_RS_PATH)
    logger.info("Stocks RS Calculated")

    ## Calculate Stocks Dispersion Score
    stocks_dsp_df = cal_dispersion_score(data=stocks_df, atr_lag=14, end_date=end_date)
    stocks_dsp_df.sink_csv(save_path / ComputeConfig.STOCKS_DSP_PATH)
    logger.info("Stocks Dispersion Score Calculated")
