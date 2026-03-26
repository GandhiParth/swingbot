import logging
from datetime import datetime

import polars as pl
import polars.selectors as cs

from config.computation.filter import PullBackFilterConfig

logger = logging.getLogger(__name__)


def basic_filter(
    data: pl.LazyFrame | pl.DataFrame,
    symbol_list: list[str],
    scan_date: datetime,
) -> pl.DataFrame:

    logger.info("Applying Basic Filter")
    logger.info(f"Number of stocks in symbol list: {len(symbol_list)}")

    res = (
        data.lazy()
        .filter(
            (pl.col("timestamp") == scan_date)
            & (pl.col("symbol").is_in(symbol_list))
            & (
                (pl.col("close_ema_9") >= pl.col("close_sma_50"))
                | (pl.col("close_ema_21") >= pl.col("close_sma_50"))
            )
        )
        .collect()
    )

    logger.info(f"Symbols after basic filter: {len(res)}")
    return res


def adr_filter(
    data: pl.LazyFrame | pl.DataFrame,
    symbol_list: list[str],
    scan_date: datetime,
    adr_cutoff: float,
) -> pl.DataFrame:

    logger.info("Applying ADR Filter")
    logger.info(f"Number of stocks in symbol list: {len(symbol_list)}")

    res = (
        data.lazy()
        .filter(
            (pl.col("timestamp") == scan_date)
            & (pl.col("adr_pct_20") >= adr_cutoff)
            & (pl.col("symbol").is_in(symbol_list))
        )
        .collect()
    )

    logger.info(f"Symbols after ADR filter: {len(res)}")
    return res


def pullback_filter(
    data: pl.LazyFrame | pl.DataFrame,
    symbol_list: list[str],
    scan_date: datetime,
) -> pl.DataFrame:

    logger.info("Applying PullBack Filter")
    logger.info(f"Number of stocks in symbol list: {len(symbol_list)}")

    comparisons = [
        (pl.col(f"mid_prev_{i}")) <= pl.col(f"mid_prev_{i + 1}")
        for i in range(0, PullBackFilterConfig.PULLBACK_DAYS)
    ]

    cumulative_conditions = []
    current_chain = pl.lit(True)

    for cond in comparisons:
        # "Current streak is alive IF it was alive before AND this condition is met"
        current_chain = current_chain & cond
        cumulative_conditions.append(current_chain)

    # 3. Sum the cumulative conditions to get the streak count
    mid_down_streak_expr = pl.sum_horizontal(cumulative_conditions).alias(
        "mid_down_streak"
    )

    res = (
        data.lazy()
        .filter(pl.col("symbol").is_in(symbol_list))
        .with_columns(
            [pl.mean_horizontal(("open", "close")).round(2).alias("mid_prev_0")]
        )
        .with_columns(
            [
                pl.col("mid_prev_0")
                .shift(i)
                .over(partition_by="symbol", order_by="timestamp", descending=False)
                .alias(f"mid_prev_{i}")
                for i in range(1, PullBackFilterConfig.PULLBACK_DAYS + 1)
            ]
            + [
                (
                    ((pl.col("mid_prev_0") - pl.col(col)).abs() * 100 / pl.col(col))
                    <= PullBackFilterConfig.PULLBACK_NEAR_PCT
                ).alias(f"mid_near_{col}")
                for col in ["close_ema_9", "close_ema_21", "close_sma_50"]
            ]
            + [
                (
                    ((pl.col("low") - pl.col(col)).abs() * 100 / pl.col(col))
                    <= PullBackFilterConfig.PULLBACK_NEAR_PCT
                ).alias(f"low_near_{col}")
                for col in ["close_ema_9", "close_ema_21", "close_sma_50"]
            ]
        )
        .with_columns(mid_down_streak_expr)
        .with_columns(
            [
                (
                    pl.col(f"mid_near_close_ema_{i}")
                    | (pl.col(f"low_near_close_ema_{i}"))
                ).alias(f"near_ema_{i}")
                for i in [9, 21]
            ]
            + [
                (
                    pl.col(f"mid_near_close_sma_{i}")
                    | (pl.col(f"low_near_close_sma_{i}"))
                ).alias(f"near_sma_{i}")
                for i in [50]
            ]
        )
        .filter(
            (
                (pl.col("near_ema_9") == True)
                | (pl.col("near_ema_21") == True)
                | (pl.col("near_sma_50") == True)
            )
        )
        .with_columns(
            pl.col("timestamp")
            .sort()
            .implode()
            .over(partition_by="symbol")
            .alias("flag_dates")
        )
        .filter((pl.col("timestamp") == scan_date))
        .select(~cs.starts_with("mid_prev"))
        .collect()
    )

    logger.info(f"Symbols after PullBack filter: {len(res.select('symbol').unique())}")
    return res
