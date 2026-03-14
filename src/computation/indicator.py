import logging

import polars as pl

from config.computation.indicator import IndicatorConfig

logger = logging.getLogger(__name__)


def add_indicators(data: pl.LazyFrame | pl.DataFrame) -> pl.LazyFrame:
    """
    Add SMA, EMA, ADR & RVOL Columns
    """
    res = (
        data.lazy()
        .with_columns(pl.col("timestamp").cast(pl.Date()))
        .with_columns(
            # Close SMA expression
            [
                pl.col("close")
                .rolling_mean(window_size=n)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(2)
                .alias(f"close_sma_{n}")
                for n in IndicatorConfig.SMA_DAYS
            ]
            # Close EMA Experssion
            + [
                pl.col("close")
                .ewm_mean(alpha=2 / (n + 1))
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(2)
                .alias(f"close_ema_{n}")
                for n in IndicatorConfig.EMA_DAYS
            ]
            # Volume SMA Expression
            + [
                pl.col("volume")
                .rolling_mean(window_size=n)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(0)
                .cast(pl.Int64())
                .alias(f"volume_sma_{n}")
                for n in IndicatorConfig.VOL_SMA_DAYS
            ]
            # Day Range
            + [(pl.col("high") / pl.col("low")).round(4).alias("day_range")]
            # Body to Range ratio
            + [
                (
                    (
                        ((pl.col("open") - pl.col("close")).abs())
                        / (pl.col("high") - pl.col("low"))
                    ).rolling_mean(window_size=n)
                    * 100
                )
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(2)
                .alias(f"body_by_range_pct_sma_{n}")
                for n in IndicatorConfig.CLEAN_SCORE_DAYS
            ]
            # Lower Wick to Body Ratio
            + [
                (
                    (
                        (pl.min_horizontal("open", "close") - pl.col("low"))
                        / (pl.col("high") - pl.col("low"))
                    ).rolling_mean(window_size=n)
                    * 100
                )
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(2)
                .alias(f"lower_wick_by_range_pct_sma_{n}")
                for n in IndicatorConfig.CLEAN_SCORE_DAYS
            ]
            # Uppwer Wick to Body Ratio
            + [
                (
                    (
                        (pl.col("high") - pl.max_horizontal("open", "close"))
                        / (pl.col("high") - pl.col("low"))
                    ).rolling_mean(window_size=n)
                    * 100
                )
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .round(2)
                .alias(f"upper_wick_by_range_pct_sma_{n}")
                for n in IndicatorConfig.CLEAN_SCORE_DAYS
            ]
        )
        .with_columns(
            # ADR calculation
            [
                (
                    (
                        pl.col("day_range")
                        .rolling_mean(window_size=i)
                        .over(
                            partition_by="symbol",
                            order_by="timestamp",
                            descending=False,
                        )
                        - 1
                    )
                    * 100
                )
                .round(2)
                .alias(f"adr_pct_{i}")
                for i in IndicatorConfig.ADR_DAYS
            ]
            # RVOL calculation
            + [
                (pl.col("volume") * 100 / pl.col(f"volume_sma_{i}"))
                .round()
                .alias(f"rvol_pct_{i}")
                for i in IndicatorConfig.VOL_SMA_DAYS
            ]
            # Clean Score Calculation
            + [
                (
                    pl.col(f"body_by_range_pct_sma_{n}")
                    * (100 - pl.col(f"lower_wick_by_range_pct_sma_{n}"))
                    / 100
                )
                .round(2)
                .alias(f"clean_score_pct_{n}")
                for n in IndicatorConfig.CLEAN_SCORE_DAYS
            ]
        )
    )

    return res
