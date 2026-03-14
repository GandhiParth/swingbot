from datetime import datetime

import polars as pl

from config.computation.indicator import IndicatorConfig


def gen_market_dashboard_data(
    nse_indices_df: pl.DataFrame,
    indices_df: pl.DataFrame,
    stocks_df: pl.DataFrame,
    nse_ind_df: pl.DataFrame,
    scan_date: datetime,
):
    _select_cols = [
        "timestamp",
        "index_type",
        "index_name",
        "symbol",
        "close",
        "1D",
        "1W",
        "1M",
        "3M",
        "6M",
    ]

    indices_data_list = indices_df.get_column("symbol").unique().to_list()
    nse_ind_df = nse_ind_df.lazy().select("symbol", "market_cap_cr")

    indices_stock_data = (
        nse_indices_df.lazy()
        .filter(pl.col("index_name").is_in(indices_data_list))
        .join(stocks_df.lazy(), on="symbol", how="left")
        .join(nse_ind_df, on="symbol", how="left")
        .with_columns(pl.col("timestamp").cast(pl.Date()))
        .with_columns(
            # Shift Columns
            [
                pl.col(col)
                .shift(i)
                .over(
                    partition_by=["symbol", "index_name", "index_type"],
                    order_by="timestamp",
                    descending=False,
                )
                .alias(f"{col}_prev_{i}")
                for col in ["close", "timestamp"]
                for i in IndicatorConfig.LOOKBACK_RETURN_PCT.keys()
            ]
        )
        .with_columns(
            # Gains Calculation
            [
                (
                    (pl.col("close") - pl.col(f"close_prev_{i}"))
                    * 100
                    / pl.col(f"close_prev_{i}")
                )
                .round(2)
                .alias(f"{name}")
                for i, name in IndicatorConfig.LOOKBACK_RETURN_PCT.items()
            ]
        )
        .filter(pl.col("timestamp") == scan_date)
        .select(_select_cols + ["market_cap_cr"])
        .sort(["index_type", "index_name", "1W"], descending=[False, False, True])
    )

    _nse_indices_df = nse_indices_df.lazy().select("index_name", "index_type").unique()

    indices_data = (
        indices_df.lazy()
        .with_columns(pl.col("timestamp").cast(pl.Date()))
        .join(
            _nse_indices_df.lazy(), left_on="symbol", right_on="index_name", how="left"
        )
        .with_columns(
            # Shift Columns
            [
                pl.col(col)
                .shift(i)
                .over(
                    partition_by=["symbol"],
                    order_by="timestamp",
                    descending=False,
                )
                .alias(f"{col}_prev_{i}")
                for col in ["close", "timestamp"]
                for i in IndicatorConfig.LOOKBACK_RETURN_PCT.keys()
            ]
            + [pl.col("symbol").alias("index_name")]
        )
        .with_columns(
            # Gains Calculation
            [
                (
                    (pl.col("close") - pl.col(f"close_prev_{i}"))
                    * 100
                    / pl.col(f"close_prev_{i}")
                )
                .round(2)
                .alias(f"{name}")
                for i, name in IndicatorConfig.LOOKBACK_RETURN_PCT.items()
            ]
        )
        .filter(pl.col("timestamp") == scan_date)
        .select(_select_cols)
        .sort(["index_type", "index_name", "1W"], descending=[False, False, True])
    )
    return indices_stock_data, indices_data
