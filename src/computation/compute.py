from datetime import datetime

import polars as pl
import polars.selectors as cs

from computation.filter import adr_filter, basic_filter, pullback_filter
from computation.scanner import basic_scan, find_stocks, prep_scan_data
from config.computation.compute import ComputeConfig
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
        .with_columns(pl.col("market_cap_cr").fill_null(100))
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


def gen_market_breadth_data(stocks_df: pl.DataFrame):

    scan_data = prep_scan_data(stocks_df)

    res = (
        scan_data.group_by(
            "timestamp",
        )
        .agg(
            [pl.col("symbol").count().alias("# Stocks")]
            + [
                (pl.col("close") >= pl.col(f"close_ema_{i}"))
                .sum()
                .alias(f"above_ema_{i}")
                for i in IndicatorConfig.EMA_DAYS
            ]
            + [
                (pl.col("close") >= pl.col(f"close_sma_{i}"))
                .sum()
                .alias(f"above_sma_{i}")
                for i in IndicatorConfig.SMA_DAYS
            ]
            + [
                (pl.col("pct_gain_prev_1") >= 4.5).sum().alias("UP 4.5% 1D"),
                (pl.col("pct_gain_prev_1") < 4.5).sum().alias("DOWN 4.5% 1D"),
            ]
        )
        .with_columns(
            (pl.col(col) * 100 / pl.col("# Stocks"))
            .round(2)
            .alias(f"% {col.replace('_', ' ').upper()}")
            for col in ["UP 4.5% 1D", "DOWN 4.5% 1D"]
            + [f"above_ema_{i}" for i in IndicatorConfig.EMA_DAYS]
            + [f"above_sma_{i}" for i in IndicatorConfig.SMA_DAYS]
        )
        .select(
            pl.exclude(
                ["UP 4.5% 1D", "DOWN 4.5% 1D"]
                + [f"above_ema_{i}" for i in IndicatorConfig.EMA_DAYS]
                + [f"above_sma_{i}" for i in IndicatorConfig.SMA_DAYS]
            )
        )
        .sort("timestamp", descending=True)
        .head(ComputeConfig.MKT_BREADTH_DAYS)
    )

    return res


def gen_scanner_data(
    stocks_df: pl.DataFrame,
    nse_ind_df: pl.DataFrame,
    start_date: datetime,
    end_date: datetime,
    adr_cutoff: float,
) -> dict[str : pl.DataFrame]:
    res_dict = {}

    # Preparing Scan Data

    scan_df = prep_scan_data(data=stocks_df)
    basic_scan_df = basic_scan(data=scan_df)
    res_dict["basic_scan_df"] = basic_scan_df.collect()

    find_stocks_scan_df = find_stocks(
        data=basic_scan_df, start_date=start_date, end_date=end_date
    ).collect()
    scan_stocks_list = find_stocks_scan_df.get_column("symbol").to_list()

    # Preparing Filter Data
    basic_filter_df = basic_filter(
        data=scan_df, symbol_list=scan_stocks_list, scan_date=end_date
    )
    res_dict["basic_filter_df"] = basic_filter_df
    basic_filter_stocks = basic_filter_df.get_column("symbol").to_list()

    adr_filter_df = adr_filter(
        data=scan_df,
        symbol_list=basic_filter_stocks,
        scan_date=end_date,
        adr_cutoff=adr_cutoff,
    )
    res_dict["adr_filter_df"] = adr_filter_df
    adr_filter_stocks = adr_filter_df.get_column("symbol").to_list()

    pullback_filter_df = pullback_filter(
        data=scan_df, symbol_list=basic_filter_stocks, scan_date=end_date
    )
    res_dict["pullback_filter_df"] = pullback_filter_df
    pullback_filter_stocks = pullback_filter_df.get_column("symbol").unique().to_list()

    # Final Output

    final_res = (
        scan_df.filter(
            (pl.col("symbol").is_in(basic_filter_stocks))
            & (pl.col("timestamp") == end_date)
        )
        .with_columns(
            pl.when(pl.col("symbol").is_in(value))
            .then(True)
            .otherwise(False)
            .alias(key)
            for key, value in {
                "basic_filter_flag": basic_filter_stocks,
                "adr_filter_flag": adr_filter_stocks,
                "pullback_filter_flag": pullback_filter_stocks,
            }.items()
        )
        .join(
            pullback_filter_df.lazy().select(
                "symbol",
                "mid_down_streak",
                "near_ema_9",
                "near_ema_21",
                "near_sma_50",
            ),
            on="symbol",
            how="left",
        )
        .join(nse_ind_df.lazy(), on="symbol", how="left")
        .collect()
    )
    res_dict["final_res"] = final_res
    return res_dict


def cal_atr(data: pl.DataFrame | pl.LazyFrame, lag: int = ComputeConfig.ATR_DAYS):

    res = (
        data.lazy()
        .with_columns(pl.col("timestamp").cast(pl.Date()))
        .with_columns(
            pl.col("close")
            .shift(1)
            .over(partition_by="symbol", order_by="timestamp", descending=False)
            .alias("close_prev_1")
        )
        .with_columns(
            pl.max_horizontal(
                pl.col("high") - pl.col("low"),
                (pl.col("high") - pl.col("close_prev_1")).abs(),
                (pl.col("low") - pl.col("close_prev_1")).abs(),
            ).alias("true_range")
        )
        .with_columns(
            pl.col("true_range")
            .ewm_mean(alpha=2 / (n + 1))
            .over(partition_by="symbol", order_by="timestamp", descending=False)
            .round(2)
            .alias(f"atr_{n}")
            for n in [lag]
        )
        .select("symbol", "timestamp", "close", f"atr_{lag}")
    )

    return res


def cal_stocks_rs(
    indices_df: pl.DataFrame | pl.LazyFrame,
    stocks_df: pl.DataFrame | pl.LazyFrame,
    end_date: datetime,
) -> pl.LazyFrame:

    index_atr = (
        cal_atr(data=indices_df)
        .rename(
            {f"atr_{ComputeConfig.ATR_DAYS}": f"index_atr_{ComputeConfig.ATR_DAYS}"}
        )
        .with_columns(
            pl.col("close")
            .shift(1)
            .over(partition_by="symbol", order_by="timestamp", descending=False)
            .alias("close_prev_1")
        )
        .with_columns((pl.col("close") - pl.col("close_prev_1")).alias("price_change"))
        .with_columns(
            (
                pl.col("price_change") / pl.col(f"index_atr_{ComputeConfig.ATR_DAYS}")
            ).alias("spi")
        )
        .select("timestamp", "spi")
    )
    stocks_atr = (
        cal_atr(data=stocks_df)
        .rename(
            {f"atr_{ComputeConfig.ATR_DAYS}": f"stock_atr_{ComputeConfig.ATR_DAYS}"}
        )
        .drop("close")
    )

    res = (
        stocks_df.lazy()
        .with_columns(pl.col("timestamp").cast(pl.Date()))
        .with_columns(
            pl.col("close")
            .shift(1)
            .over(partition_by="symbol", order_by="timestamp", descending=False)
            .alias("close_prev_1")
        )
        .with_columns((pl.col("close") - pl.col("close_prev_1")).alias("price_change"))
        .join(stocks_atr, on=["symbol", "timestamp"])
        .join(index_atr, on="timestamp", how="left")
        .with_columns(
            (pl.col("spi") * pl.col(f"stock_atr_{ComputeConfig.ATR_DAYS}")).alias(
                "expected_change"
            )
        )
        .with_columns(
            (pl.col("price_change") - pl.col("expected_change")).alias("excess_move")
        )
        .with_columns(
            (
                pl.col("excess_move") / pl.col(f"stock_atr_{ComputeConfig.ATR_DAYS}")
            ).alias(f"rss_{ComputeConfig.ATR_DAYS}")
        )
        .with_columns(
            pl.col(f"rss_{ComputeConfig.ATR_DAYS}")
            .rolling_mean(ComputeConfig.ATR_DAYS)
            .over(partition_by="symbol", order_by="timestamp", descending=False)
            .alias("rolling RSS")
        )
        .select("symbol", "timestamp", f"rss_{ComputeConfig.ATR_DAYS}", "rolling RSS")
        .with_columns(
            pl.col("rolling RSS")
            .rank(method="dense")
            .over("timestamp", descending=False)
            .alias("rank")
        )
        .with_columns(
            ((pl.col("rank") - 1) / (pl.len().over("timestamp") - 1) * 100).alias(
                "rss_score"
            )
        )
        .filter((pl.col("timestamp") == end_date) & pl.col("rss_score").is_not_null())
        .sort("rss_score", descending=True)
        .with_columns(cs.float().round(4))
    )

    return res
