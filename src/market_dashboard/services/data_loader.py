import polars as pl
import streamlit as st

from config.computation.compute import ComputeConfig


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
