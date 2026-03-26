import polars as pl
import polars.selectors as cs
import streamlit as st

from config.computation.compute import ComputeConfig
from config.computation.indicator import IndicatorConfig


def available_dates():
    """
    Get Available Compute Dates
    """

    return sorted(
        [p.name for p in ComputeConfig.DATA_PATH.iterdir() if p.is_dir()], reverse=True
    )


@st.cache_data
def load_mkt_db_data(date: str):
    """
    Loads the Data for the Market Dashboard
    """

    path = ComputeConfig.DATA_PATH / date

    stocks_df = pl.read_csv(path / ComputeConfig.MKT_DB_STOCKS_PATH)
    indices_df = pl.read_csv(path / ComputeConfig.MKT_DB_INDICES_PATH)

    return indices_df, stocks_df


@st.cache_data
def load_mkt_breadth_data(date: str):
    """
    Loads the Data for the Market Dashboard
    """

    path = ComputeConfig.DATA_PATH / date

    mkt_breadth_df = pl.read_csv(path / ComputeConfig.MKT_BREADTH_PATH)

    return mkt_breadth_df


@st.cache_data
def load_scanner_data(date: str):
    """
    Loads the Data for the Scanner Dashboard
    """

    path = ComputeConfig.DATA_PATH / date

    rss_df = pl.scan_csv(path / ComputeConfig.STOCKS_RS_PATH).select(
        "symbol", "rss_score"
    )
    scanner_df = (
        pl.scan_csv(path / ComputeConfig.FILTER_RESULT_PATH)
        .select(
            [
                "symbol",
                "pct_gain_prev_1",
                "pct_gain_prev_5",
                "pct_gain_prev_21",
                "pct_gain_prev_63",
                "pct_gain_prev_126",
                "rvol_pct_50",
                "adr_pct_20",
                "adr_filter_flag",
                "pullback_filter_flag",
                "mid_down_streak",
                "near_ema_9",
                "near_ema_21",
                "near_sma_50",
                "macro_economic_sector",
                "sector",
                "industry",
                "basic_industry",
                "market_cap_cr",
            ]
        )
        .rename(
            {
                f"pct_gain_prev_{i}": f"{value}"
                for i, value in IndicatorConfig.LOOKBACK_RETURN_PCT.items()
            }
        )
        .join(rss_df, on="symbol", how="left")
        .collect()
    )

    scanner_df = (
        scanner_df.lazy()
        .rename({i: i.replace("_", " ").upper() for i in scanner_df.columns})
        .with_columns(cs.float().round(2))
        .collect()
    )

    return scanner_df
