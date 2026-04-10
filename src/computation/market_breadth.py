"""
Market Breadth Calculator
=========================
Computes a composite market breadth score from daily OHLCV data.

Input DataFrame columns: symbol, timestamp, open, high, low, close, volume
Output: one row per trading day with breadth metrics, composite scores,
        regime labels, and trade signals.

See help_docs/breadth_methodology.md for full interpretation guide.
"""

import polars as pl

# -----------------------------------------------------------------------------
# CONFIGURATION
# -----------------------------------------------------------------------------

SMA_DAYS = [20, 50]
HL_DAYS = [20, 252]  # 252 = 52-week
MICRO_WINDOW = 20  # Rolling rank window (1-month context for swing trading)
EWM_SPANS = {"fast": 5, "medium": 10, "slow": 20}
MCO_SPANS = (19, 39)  # McClellan Oscillator EMA spans
HL_INDEX_SPAN = 10  # EMA span for High-Low Index

# Universe filters
MIN_PRICE = 10.0  # Minimum close price
MIN_AVG_VOL = 50_000  # Minimum 20-day average volume

# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------


def rolling_percentile(expr: pl.Expr, window: int) -> pl.Expr:
    """Rank within rolling window, normalized to [0, 1]."""
    return expr.rolling_rank(window_size=window) / window


def tanh_pl(expr: pl.Expr) -> pl.Expr:
    """
    Vectorized tanh using native Polars ops - no Python loops.
    tanh(x) = (e^2x - 1) / (e^2x + 1)
    """
    e2x = (2.0 * expr).exp()
    return (e2x - 1.0) / (e2x + 1.0)


# -----------------------------------------------------------------------------
# MAIN FUNCTION
# -----------------------------------------------------------------------------


def compute_breadth(data: pl.DataFrame) -> pl.LazyFrame:
    """
    Compute market breadth indicators from a daily OHLCV DataFrame.

    Parameters
    ----------
    data : pl.DataFrame
        Must have columns: symbol, timestamp, open, high, low, close, volume

    Returns
    -------
    pl.DataFrame
        One row per trading day. Null rows (insufficient history for rolling
        windows) are dropped.
    """

    # --- STEP 1: Universe Filtering ------------------------------------------
    filtered = (
        data.lazy()
        .with_columns(pl.col("timestamp").cast(pl.Date))
        .with_columns(
            pl.col("volume")
            .rolling_mean(window_size=20)
            .over(partition_by="symbol", order_by="timestamp")
            .alias("_avg_vol_20")
        )
        .filter((pl.col("close") >= MIN_PRICE) & (pl.col("_avg_vol_20") >= MIN_AVG_VOL))
        .drop("_avg_vol_20")
    )

    # --- STEP 2: Per-Symbol Indicators ---------------------------------------
    symbol_df = (
        filtered.with_columns(
            [
                # SMA
                pl.col("close")
                .rolling_mean(window_size=n)
                .over(partition_by="symbol", order_by="timestamp")
                .alias(f"sma_{n}")
                for n in SMA_DAYS
            ]
            + [
                # Rolling High / Low
                pl.col("close")
                .rolling_max(window_size=n)
                .over(partition_by="symbol", order_by="timestamp")
                .alias(f"high_{n}")
                for n in HL_DAYS
            ]
            + [
                pl.col("close")
                .rolling_min(window_size=n)
                .over(partition_by="symbol", order_by="timestamp")
                .alias(f"low_{n}")
                for n in HL_DAYS
            ]
            + [
                # Previous close
                pl.col("close")
                .shift(1)
                .over(partition_by="symbol", order_by="timestamp")
                .alias("_prev_close")
            ]
        )
        .with_columns(
            [
                # APPROACH A: Binary SMA breadth
                (pl.col("close") > pl.col(f"sma_{n}"))
                .cast(pl.Int8)
                .alias(f"above_sma_{n}_binary")
                for n in SMA_DAYS
            ]
        )
        .with_columns(
            [
                # APPROACH B: Proximity / tanh SMA breadth
                tanh_pl(
                    3.0 * (pl.col("close") - pl.col(f"sma_{n}")) / pl.col(f"sma_{n}")
                ).alias(f"proximity_sma_{n}")
                for n in SMA_DAYS
            ]
            + [
                # New Highs / Lows
                (pl.col("close") >= pl.col(f"high_{n}")).cast(pl.Int8).alias(f"nh_{n}")
                for n in HL_DAYS
            ]
            + [
                (pl.col("close") <= pl.col(f"low_{n}")).cast(pl.Int8).alias(f"nl_{n}")
                for n in HL_DAYS
            ]
            + [
                # Advance / Decline
                (pl.col("close") > pl.col("_prev_close"))
                .cast(pl.Int8)
                .alias("_advance"),
                (pl.col("close") < pl.col("_prev_close"))
                .cast(pl.Int8)
                .alias("_decline"),
            ]
            + [
                # Volume tagging (for TRIN)
                pl.when(pl.col("close") > pl.col("_prev_close"))
                .then(pl.col("volume"))
                .otherwise(pl.lit(0))
                .alias("_adv_vol"),
                pl.when(pl.col("close") < pl.col("_prev_close"))
                .then(pl.col("volume"))
                .otherwise(pl.lit(0))
                .alias("_dec_vol"),
            ]
        )
    )

    # --- STEP 3: Market-Level Aggregation ------------------------------------
    market_df = (
        symbol_df.group_by("timestamp")
        .agg(
            [
                pl.col(f"above_sma_{n}_binary")
                .mean()
                .round(4)
                .alias(f"pct_above_sma_{n}")
                for n in SMA_DAYS
            ]
            + [
                pl.col(f"proximity_sma_{n}")
                .mean()
                .round(4)
                .alias(f"avg_proximity_sma_{n}")
                for n in SMA_DAYS
            ]
            + [pl.col(f"nh_{n}").sum().alias(f"nh_{n}") for n in HL_DAYS]
            + [pl.col(f"nl_{n}").sum().alias(f"nl_{n}") for n in HL_DAYS]
            + [pl.col(f"nh_{n}").mean().round(4).alias(f"pct_nh_{n}") for n in HL_DAYS]
            + [pl.col(f"nl_{n}").mean().round(4).alias(f"pct_nl_{n}") for n in HL_DAYS]
            + [
                pl.col("_advance").sum().alias("adv"),
                pl.col("_decline").sum().alias("dec"),
                pl.col("_adv_vol").sum().alias("adv_vol"),
                pl.col("_dec_vol").sum().alias("dec_vol"),
                pl.col("symbol").len().alias("universe_count"),
            ]
        )
        .sort("timestamp")
    )

    # --- STEP 4: Derived Indicators ------------------------------------------
    derived_df = (
        market_df.with_columns(
            (pl.col("adv") - pl.col("dec")).alias("net_adv"),
            (
                (
                    pl.col("adv").cast(pl.Float64)
                    / pl.col("dec").clip(lower_bound=1).cast(pl.Float64)
                )
                / (
                    pl.col("adv_vol").cast(pl.Float64)
                    / pl.col("dec_vol").clip(lower_bound=1).cast(pl.Float64)
                )
            )
            .round(4)
            .alias("trin"),
            *[
                (pl.col(f"nh_{n}") - pl.col(f"nl_{n}")).alias(f"nh_nl_net_{n}")
                for n in HL_DAYS
            ],
            (pl.col("adv") - pl.col("dec")).cum_sum().alias("cum_ad"),
        )
        .with_columns(
            pl.col("net_adv").ewm_mean(span=MCO_SPANS[0]).alias("_mco_ema19"),
            pl.col("net_adv").ewm_mean(span=MCO_SPANS[1]).alias("_mco_ema39"),
            (
                pl.col("nh_252").cast(pl.Float64)
                / (pl.col("nh_252") + pl.col("nl_252") + 1).cast(pl.Float64)
            )
            .ewm_mean(span=HL_INDEX_SPAN)
            .round(4)
            .alias("hl_index_252"),
            (
                pl.col("nh_20").cast(pl.Float64)
                / (pl.col("nh_20") + pl.col("nl_20") + 1).cast(pl.Float64)
            )
            .ewm_mean(span=HL_INDEX_SPAN)
            .round(4)
            .alias("hl_index_20"),
        )
        .with_columns(
            (pl.col("_mco_ema19") - pl.col("_mco_ema39")).round(2).alias("mco"),
            (pl.col("_mco_ema19") - pl.col("_mco_ema39"))
            .cum_sum()
            .round(2)
            .alias("msi"),
        )
        .drop("_mco_ema19", "_mco_ema39")
    )

    # --- STEP 5: Percentile Ranks --------------------------------------------
    percentile_df = derived_df.with_columns(
        rolling_percentile(pl.col("avg_proximity_sma_20"), MICRO_WINDOW).alias(
            "p_trend"
        ),
        rolling_percentile(pl.col("pct_above_sma_20"), MICRO_WINDOW).alias(
            "p_trend_binary"
        ),
        rolling_percentile(pl.col("pct_nh_20"), MICRO_WINDOW).alias("p_momentum"),
        rolling_percentile(
            pl.col("nh_20").cast(pl.Float64) / (pl.col("nl_20") + 1).cast(pl.Float64),
            MICRO_WINDOW,
        ).alias("p_expansion"),
        rolling_percentile(
            pl.col("adv").cast(pl.Float64) / (pl.col("dec") + 1).cast(pl.Float64),
            MICRO_WINDOW,
        ).alias("p_participation"),
    )

    # --- STEP 6: Composite Scores --------------------------------------------
    scored_df = (
        percentile_df.with_columns(
            (
                0.30 * pl.col("p_trend")
                + 0.30 * pl.col("p_momentum")
                + 0.20 * pl.col("p_expansion")
                + 0.20 * pl.col("p_participation")
            ).alias("breadth_raw"),
            (
                0.30 * pl.col("p_trend_binary")
                + 0.30 * pl.col("p_momentum")
                + 0.20 * pl.col("p_expansion")
                + 0.20 * pl.col("p_participation")
            ).alias("breadth_raw_binary"),
        )
        .with_columns(
            pl.col("breadth_raw").ewm_mean(span=EWM_SPANS["fast"]).alias("_ema_fast"),
            pl.col("breadth_raw")
            .ewm_mean(span=EWM_SPANS["medium"])
            .alias("_ema_medium"),
            pl.col("breadth_raw").ewm_mean(span=EWM_SPANS["slow"]).alias("_ema_slow"),
            pl.col("breadth_raw_binary")
            .ewm_mean(span=EWM_SPANS["medium"])
            .alias("_ema_medium_binary"),
        )
        .with_columns(
            (2.0 * pl.col("_ema_fast") - 1.0).alias("final_fast"),
            (2.0 * pl.col("_ema_medium") - 1.0).alias("final_medium"),
            (2.0 * pl.col("_ema_slow") - 1.0).alias("final_slow"),
            (2.0 * pl.col("_ema_medium_binary") - 1.0).alias("final_medium_binary"),
        )
    )

    # --- STEP 7: Momentum and Velocity ---------------------------------------
    velocity_df = scored_df.with_columns(
        (pl.col("final_fast") - pl.col("final_medium"))
        .round(6)
        .alias("breadth_momentum"),
        (pl.col("final_medium") - pl.col("final_medium").shift(3))
        .round(6)
        .alias("breadth_velocity_3d"),
    )

    # --- STEP 8: Regime Classification ---------------------------------------
    labelled_df = (
        velocity_df.with_columns(
            pl.when(pl.col("final_medium") >= 0.6)
            .then(pl.lit("🟢 Strong Bull 🚀"))
            .when(pl.col("final_medium") >= 0.2)
            .then(pl.lit("🟢 Bullish 📈"))
            .when(pl.col("final_medium") > -0.2)
            .then(pl.lit("🟡 Neutral ⚖️"))
            .when(pl.col("final_medium") > -0.6)
            .then(pl.lit("🟠 Bearish 📉"))
            .otherwise(pl.lit("🔴 Strong Bear 💥"))
            .alias("regime"),
            pl.when(pl.col("breadth_momentum") > 0.02)
            .then(pl.lit("⚡ Strengthening"))
            .when(pl.col("breadth_momentum") < -0.02)
            .then(pl.lit("❄️ Weakening"))
            .otherwise(pl.lit("➖ Flat"))
            .alias("regime_modifier"),
        )
        .with_columns(
            (pl.col("regime") + pl.lit(" / ") + pl.col("regime_modifier")).alias(
                "regime_label"
            )
        )
        .with_columns(
            pl.when(
                (pl.col("final_medium") > -0.1) & (pl.col("breadth_velocity_3d") > 0.15)
            )
            .then(pl.lit("🚀 Long (Thrust)"))
            .when((pl.col("final_medium") > 0.2) & (pl.col("breadth_momentum") > 0))
            .then(pl.lit("📈 Long (Strengthening)"))
            .when((pl.col("final_medium") > 0.2) & (pl.col("breadth_momentum") < 0))
            .then(pl.lit("🟡 Long (Weakening - tighten stops)"))
            .when((pl.col("final_medium") < -0.2) & (pl.col("breadth_momentum") < 0))
            .then(pl.lit("📉 Short (Strengthening)"))
            .when((pl.col("final_medium") < -0.2) & (pl.col("breadth_momentum") > 0))
            .then(pl.lit("🟠 Short (Weakening - cover partial)"))
            .otherwise(pl.lit("⚪ No Trade / Choppy"))
            .alias("trade_recommendation")
        )
    )

    # --- STEP 9: Clean output ------------------------------------------------
    result = labelled_df.filter(pl.col("final_medium").is_not_null()).select(
        [
            "timestamp",
            "final_fast",
            "final_medium",
            "final_slow",
            "breadth_momentum",
            "breadth_velocity_3d",
            "mco",
            "msi",
            "trin",
            "hl_index_252",
            "hl_index_20",
            "cum_ad",
            "avg_proximity_sma_20",
            # "pct_above_sma_20_binary",
            "nh_20",
            "nl_20",
            "nh_252",
            "nl_252",
            "adv",
            "dec",
            "universe_count",
            "regime_label",
            "trade_recommendation",
            "final_medium_binary",
        ]
    )

    return result


# -----------------------------------------------------------------------------
# CONVENIENCE: Latest-day summary
# -----------------------------------------------------------------------------


def latest_breadth_summary(breadth_df: pl.DataFrame) -> dict:
    """Return a human-readable summary of the latest trading day's breadth."""
    row = breadth_df.sort("timestamp").tail(1).to_dicts()[0]

    return {
        "date": str(row["timestamp"]),
        "regime": row["regime_label"],
        "signal": row["trade_recommendation"],
        "score_fast": round(row["final_fast"], 4),
        "score_medium": round(row["final_medium"], 4),
        "score_slow": round(row["final_slow"], 4),
        "breadth_momentum": round(row["breadth_momentum"], 4),
        "velocity_3d": round(row["breadth_velocity_3d"] or 0, 4),
        "mco": round(row["mco"] or 0, 2),
        "trin": round(row["trin"] or 1.0, 4),
        "hl_index_252": round(row["hl_index_252"] or 0.5, 4),
        "nh_20_count": row["nh_20"],
        "nl_20_count": row["nl_20"],
        "adv_dec_ratio": round(row["adv"] / max(row["dec"], 1), 2),
        "universe_count": row["universe_count"],
        "note_binary_vs_proximity": (
            f"Binary score: {round(row['final_medium_binary'], 4)} | "
            f"Proximity score: {round(row['final_medium'], 4)} | "
            f"Delta: {round(row['final_medium'] - row['final_medium_binary'], 4)}"
        ),
    }
