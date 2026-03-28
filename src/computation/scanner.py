import logging
from datetime import datetime
from functools import reduce

import polars as pl

from computation.indicator import add_indicators
from config.computation.indicator import IndicatorConfig

logger = logging.getLogger(__name__)


def prep_scan_data(
    data: pl.DataFrame | pl.LazyFrame,
) -> pl.LazyFrame:
    """
    Fetch all data from DB and prepare it for scan
    """

    data = add_indicators(data=data)

    res = (
        data.with_columns(
            # Shift Columns
            [
                pl.col(col)
                .shift(i)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
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
                .round(4)
                .alias(f"pct_gain_prev_{i}")
                for i in IndicatorConfig.LOOKBACK_RETURN_PCT.keys()
            ]
        )
        .with_columns(
            pl.when(pl.any_horizontal(pl.col("*").is_null()))
            .then(False)
            .otherwise(True)
            .alias("all_data_flag")
        )
    )

    return res


def basic_scan(data: pl.LazyFrame) -> pl.LazyFrame:
    """
    Basic Scan checking if EMA's and Vol are aligned along with Past Pct Gains
    """
    pct_gain_expr = reduce(
        lambda a, b: a | b,
        [
            pl.col(f"pct_gain_prev_{days}") >= threshold
            for days, threshold in IndicatorConfig.LOOKBACK_DAYS_TO_MIN_RETURN_PCT.items()
        ],
    )
    res = data.lazy().filter((pl.col("all_data_flag") == True)).filter(pct_gain_expr)

    return res


def basic_short_scan(data: pl.LazyFrame) -> pl.LazyFrame:
    """
    Basic Short Scan checking if EMA's and Vol are aligned along with Past Pct Gains
    """
    pct_gain_expr = reduce(
        lambda a, b: a | b,
        [
            pl.col(f"pct_gain_prev_{days}") <= -threshold
            for days, threshold in IndicatorConfig.LOOKBACK_DAYS_TO_MIN_RETURN_PCT.items()
        ],
    )
    res = data.lazy().filter((pl.col("all_data_flag") == True)).filter(pct_gain_expr)

    return res


def high_adr_scan(data: pl.LazyFrame, adr_cutoff: float) -> pl.LazyFrame:
    """
    High ADR cutoff on top of Basic Scan
    """
    res = (
        data.lazy()
        .filter((pl.col("all_data_flag") == True))
        .filter(pl.col("adr_pct_20") >= adr_cutoff)
    )

    return res


def find_stocks(
    data: pl.LazyFrame | pl.DataFrame, start_date: datetime, end_date: datetime
) -> pl.DataFrame:
    """
    Get the unique stocks flagged between the date ranges
    """
    res = (
        data.lazy()
        .filter(
            pl.col("timestamp").is_between(
                lower_bound=start_date, upper_bound=end_date, closed="both"
            )
        )
        .collect()
    )

    min_date = res.select(pl.col("timestamp").min()).item(0, 0)
    max_date = res.select(pl.col("timestamp").max()).item(0, 0)

    logger.info(f"MIN DATE IN DATA: {min_date} & START DATE is {start_date}")
    logger.info(f"MAX DATE IN DATA: {max_date} & END DATE IS {end_date}")

    res = (
        res.lazy()
        .select(pl.col("symbol").unique())
        .with_columns(pl.lit((end_date)).alias("scan_date"))
        .select("scan_date", "symbol")
    )

    return res
