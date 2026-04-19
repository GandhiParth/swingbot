"""
MA Coil Detector — Swing Trade Screener
========================================
Detects moving average convergence (coiling) patterns from OHLCV data
stored in a SQLite database. Uses Polars for all data operations.

Measures:
  - MA dispersion (std of 4 MAs, normalized by ATR)
  - Automatic coil window detection (no fixed lookback)
  - Convergence rate, consistency (R²), tightness percentile
  - Composite coil score (0–100)
  - Coil stage classification (emerging / active / mature)

Usage:
    python coil_detector.py --db market.db --watchlist AAPL,MSFT,NVDA
    python coil_detector.py --db market.db --watchlist-file tickers.txt
    python coil_detector.py --db market.db --watchlist AAPL --verbose
"""

import argparse
import sqlite3
import sys
import math
from dataclasses import dataclass, field
from typing import Optional

import polars as pl
import numpy as np


# ── Configuration ────────────────────────────────────────────────────────────


@dataclass
class CoilConfig:
    """All tunable parameters."""

    # Moving average periods
    ema_fast: int = 10
    ema_mid: int = 21
    sma_slow: int = 50
    sma_anchor: int = 200

    # ATR
    atr_period: int = 14

    # Dispersion smoothing
    dispersion_smooth: int = 5  # SMA period applied to raw dispersion

    # Rolling slope detection
    slope_window: int = 10  # bars used for rolling slope of dispersion

    # Coil duration bounds
    coil_min_days: int = 10  # below this = not confirmed
    coil_max_days: int = 60  # above this = capped / likely dead

    # Tolerance for brief slope interruptions during backward scan
    slope_interrupt_tolerance: int = 3

    # Tightness percentile lookback
    percentile_lookback: int = 252  # 1 year of trading days

    # Classification thresholds
    emerging_min_days: int = 10
    emerging_max_days: int = 18
    emerging_tightness_min: float = 50.0
    emerging_tightness_max: float = 70.0

    active_min_days: int = 18
    active_max_days: int = 40
    active_tightness_min: float = 70.0
    active_tightness_max: float = 85.0

    mature_min_days: int = 25
    mature_tightness_min: float = 85.0

    # Score weights
    w_rate: float = 25.0
    w_consistency: float = 25.0
    w_tightness: float = 30.0
    w_duration: float = 20.0

    # Reference range for convergence rate scoring (% per day)
    rate_floor: float = 1.0  # below this = 0 points
    rate_ceiling: float = 4.0  # above this = max points

    # Duration bell curve peak
    duration_peak: int = 30

    # MA structure filters (applied before coil detection)
    require_price_above_mas: bool = True
    require_ma_stacking: bool = True

    # Data
    lookback_bars: int = 500  # bars to load from DB (need 252 + 200 for warm-up)


# ── Step 1 & 2: Load Data and Compute MAs + ATR ─────────────────────────────


def load_ohlcv(db_path: str, symbol: str, lookback: int) -> Optional[pl.DataFrame]:
    """Load OHLCV from SQLite into a Polars DataFrame."""
    conn = sqlite3.connect(db_path)
    query = """
        SELECT timestamp, open, high, low, close, volume
        FROM ohlcv
        WHERE symbol = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """
    rows = conn.execute(query, (symbol, lookback)).fetchall()
    conn.close()

    if not rows or len(rows) < 260:  # need 200 for SMA + some runway
        return None

    df = pl.DataFrame(
        rows,
        schema=["timestamp", "open", "high", "low", "close", "volume"],
        orient="row",
    )

    df = df.with_columns(
        pl.col("timestamp").cast(pl.Utf8).str.to_datetime().alias("timestamp"),
        pl.col("open").cast(pl.Float64),
        pl.col("high").cast(pl.Float64),
        pl.col("low").cast(pl.Float64),
        pl.col("close").cast(pl.Float64),
        pl.col("volume").cast(pl.Float64),
    )

    # Data came DESC from query, reverse to chronological
    df = df.reverse().with_row_index("idx")

    return df


def compute_ema(series: np.ndarray, period: int) -> np.ndarray:
    """Compute EMA over a numpy array. Returns array of same length (NaN padded)."""
    ema = np.full_like(series, np.nan, dtype=np.float64)
    k = 2.0 / (period + 1)

    # Seed with SMA of first `period` values
    first_valid = np.where(~np.isnan(series))[0]
    if len(first_valid) < period:
        return ema

    start = first_valid[0]
    seed = np.mean(series[start : start + period])
    ema[start + period - 1] = seed

    for i in range(start + period, len(series)):
        if np.isnan(series[i]):
            ema[i] = ema[i - 1]
        else:
            ema[i] = series[i] * k + ema[i - 1] * (1.0 - k)

    return ema


def compute_indicators(df: pl.DataFrame, cfg: CoilConfig) -> pl.DataFrame:
    """
    Step 1: Compute 4 MAs (EMA10, EMA21, SMA50, SMA200).
    Step 2: Compute ATR(14).
    """
    close = df["close"].to_numpy()
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()

    # ── Moving Averages ───────────────────────────────────────────────────
    ema_fast = compute_ema(close, cfg.ema_fast)
    ema_mid = compute_ema(close, cfg.ema_mid)

    sma_slow = np.full_like(close, np.nan)
    for i in range(cfg.sma_slow - 1, len(close)):
        sma_slow[i] = np.mean(close[i - cfg.sma_slow + 1 : i + 1])

    sma_anchor = np.full_like(close, np.nan)
    for i in range(cfg.sma_anchor - 1, len(close)):
        sma_anchor[i] = np.mean(close[i - cfg.sma_anchor + 1 : i + 1])

    # ── ATR ───────────────────────────────────────────────────────────────
    prev_close = np.roll(close, 1)
    prev_close[0] = np.nan

    tr = np.maximum(
        high - low,
        np.maximum(np.abs(high - prev_close), np.abs(low - prev_close)),
    )

    atr = np.full_like(tr, np.nan)
    for i in range(cfg.atr_period - 1, len(tr)):
        atr[i] = np.mean(tr[i - cfg.atr_period + 1 : i + 1])

    df = df.with_columns(
        pl.Series("ema_fast", ema_fast),
        pl.Series("ema_mid", ema_mid),
        pl.Series("sma_slow", sma_slow),
        pl.Series("sma_anchor", sma_anchor),
        pl.Series("atr", atr),
    )

    return df


# ── Step 3 & 4: Dispersion Series (Raw + Smoothed) ──────────────────────────


def compute_dispersion(df: pl.DataFrame, cfg: CoilConfig) -> pl.DataFrame:
    """
    Step 3: At each bar, compute population std of the 4 MA values,
            normalized by ATR.
    Step 4: Smooth with SMA(5).
    """
    ema_f = df["ema_fast"].to_numpy()
    ema_m = df["ema_mid"].to_numpy()
    sma_s = df["sma_slow"].to_numpy()
    sma_a = df["sma_anchor"].to_numpy()
    atr = df["atr"].to_numpy()

    n = len(df)
    disp_raw = np.full(n, np.nan, dtype=np.float64)

    for i in range(n):
        vals = [ema_f[i], ema_m[i], sma_s[i], sma_a[i], atr[i]]
        if any(np.isnan(v) for v in vals) or atr[i] == 0:
            continue

        ma_vals = np.array([ema_f[i], ema_m[i], sma_s[i], sma_a[i]])
        mean_ma = np.mean(ma_vals)
        # Population std
        std_ma = np.sqrt(np.mean((ma_vals - mean_ma) ** 2))
        disp_raw[i] = std_ma / atr[i]

    # Step 4: Smooth with SMA
    sp = cfg.dispersion_smooth
    disp_smooth = np.full(n, np.nan, dtype=np.float64)
    for i in range(n):
        if i < sp - 1:
            continue
        window = disp_raw[i - sp + 1 : i + 1]
        if np.any(np.isnan(window)):
            continue
        disp_smooth[i] = np.mean(window)

    df = df.with_columns(
        pl.Series("disp_raw", disp_raw),
        pl.Series("disp_smooth", disp_smooth),
    )

    return df


# ── Step 5: Rolling Slope of Smoothed Dispersion ────────────────────────────


def compute_rolling_slope(df: pl.DataFrame, cfg: CoilConfig) -> pl.DataFrame:
    """
    Step 5: At each bar, fit a linear regression through the last
    `slope_window` values of smoothed dispersion. Store the slope.
    """
    disp = df["disp_smooth"].to_numpy()
    n = len(disp)
    w = cfg.slope_window
    slopes = np.full(n, np.nan, dtype=np.float64)

    # Pre-compute x-sums for the fixed window size
    x = np.arange(w, dtype=np.float64)
    sum_x = np.sum(x)
    sum_x2 = np.sum(x**2)
    denom = w * sum_x2 - sum_x**2

    if denom == 0:
        df = df.with_columns(pl.Series("disp_slope", slopes))
        return df

    for i in range(w - 1, n):
        y = disp[i - w + 1 : i + 1]
        if np.any(np.isnan(y)):
            continue
        sum_y = np.sum(y)
        sum_xy = np.dot(x, y)
        slopes[i] = (w * sum_xy - sum_x * sum_y) / denom

    df = df.with_columns(pl.Series("disp_slope", slopes))

    return df


# ── Step 6: Detect Coil Start ───────────────────────────────────────────────


@dataclass
class CoilWindow:
    """Result of coil window detection."""

    found: bool = False
    start_idx: int = 0  # index in the dataframe where coil begins
    end_idx: int = 0  # index of today (last bar)
    duration: int = 0  # number of bars
    stage: str = ""  # emerging / active / mature / none
    capped: bool = False  # True if duration was capped at max


def detect_coil_window(df: pl.DataFrame, cfg: CoilConfig) -> CoilWindow:
    """
    Step 6: Walk backward from today through rolling slope series.
    Find where convergence started (slope flipped from non-negative to negative).
    Allow brief interruptions up to `slope_interrupt_tolerance` bars.
    """
    slopes = df["disp_slope"].to_numpy()
    n = len(slopes)
    result = CoilWindow()
    result.end_idx = n - 1

    # Current slope must be negative — stock must be converging NOW
    if np.isnan(slopes[-1]) or slopes[-1] >= 0:
        return result

    # Walk backward
    i = n - 2
    interrupt_count = 0

    while i >= 0:
        if np.isnan(slopes[i]):
            break

        if slopes[i] >= 0:
            interrupt_count += 1
            if interrupt_count >= cfg.slope_interrupt_tolerance:
                # Real break in convergence — coil started after this interruption
                i += cfg.slope_interrupt_tolerance  # step forward past the interruption
                break
        else:
            interrupt_count = 0

        i -= 1

    coil_start = i + 1
    duration = n - 1 - coil_start

    if duration < cfg.coil_min_days:
        # Too short to be confirmed — flag as emerging if >= some minimum
        if duration >= 5:
            result.found = True
            result.start_idx = coil_start
            result.duration = duration
            result.stage = "emerging"
        return result

    if duration > cfg.coil_max_days:
        # Cap it
        coil_start = n - 1 - cfg.coil_max_days
        duration = cfg.coil_max_days
        result.capped = True

    result.found = True
    result.start_idx = coil_start
    result.duration = duration

    return result


# ── Step 7: Convergence Rate ────────────────────────────────────────────────


def compute_convergence_rate(
    disp_smooth: np.ndarray, start_idx: int, end_idx: int
) -> tuple[float, float, float]:
    """
    Step 7: Fit linear regression through all smoothed dispersion values
    in the coil window. Return (slope, pct_rate_per_day, intercept).
    """
    y = disp_smooth[start_idx : end_idx + 1]
    valid_mask = ~np.isnan(y)
    y = y[valid_mask]

    if len(y) < 5:
        return 0.0, 0.0, 0.0

    x = np.arange(len(y), dtype=np.float64)
    n = len(x)

    sum_x = np.sum(x)
    sum_y = np.sum(y)
    sum_xy = np.dot(x, y)
    sum_x2 = np.sum(x**2)
    denom = n * sum_x2 - sum_x**2

    if denom == 0:
        return 0.0, 0.0, 0.0

    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n

    # Percentage rate: fraction of starting dispersion contracted per day
    start_disp = intercept  # regression value at x=0 (coil start)
    if start_disp > 0:
        pct_rate = abs(slope) / start_disp * 100.0
    else:
        pct_rate = 0.0

    return slope, pct_rate, intercept


# ── Step 8: Consistency (R²) ────────────────────────────────────────────────


def compute_r_squared(
    disp_smooth: np.ndarray,
    start_idx: int,
    end_idx: int,
    slope: float,
    intercept: float,
) -> float:
    """
    Step 8: R² of the linear fit over the coil window.
    """
    y = disp_smooth[start_idx : end_idx + 1]
    valid_mask = ~np.isnan(y)
    y = y[valid_mask]

    if len(y) < 5:
        return 0.0

    x = np.arange(len(y), dtype=np.float64)
    y_pred = slope * x + intercept
    y_mean = np.mean(y)

    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y_mean) ** 2)

    if ss_tot == 0:
        return 0.0

    r2 = 1.0 - (ss_res / ss_tot)
    return max(0.0, r2)


# ── Step 9: Tightness Percentile ────────────────────────────────────────────


def compute_tightness_percentile(
    disp_smooth: np.ndarray, end_idx: int, lookback: int
) -> float:
    """
    Step 9: Where does today's smoothed dispersion rank vs the last
    `lookback` bars? Returns percentile (0–100) where higher = tighter.
    """
    today_val = disp_smooth[end_idx]
    if np.isnan(today_val):
        return 0.0

    start = max(0, end_idx - lookback)
    history = disp_smooth[start : end_idx + 1]
    history = history[~np.isnan(history)]

    if len(history) < 30:
        return 0.0

    # Count how many historical values are GREATER than today
    pct = np.sum(history > today_val) / len(history) * 100.0
    return pct


# ── Step 10: Classify Coil Stage ────────────────────────────────────────────


def classify_coil(window: CoilWindow, tightness_pct: float, cfg: CoilConfig) -> str:
    """
    Step 10: Classify into emerging / active / mature based on
    duration and tightness.
    """
    d = window.duration
    t = tightness_pct

    # Mature requires BOTH conditions
    if d >= cfg.mature_min_days and t >= cfg.mature_tightness_min:
        return "mature"

    # Active: either condition
    if (cfg.active_min_days <= d <= cfg.active_max_days) or (
        cfg.active_tightness_min <= t < cfg.active_tightness_max
    ):
        return "active"

    # Emerging: either condition
    if (cfg.emerging_min_days <= d <= cfg.emerging_max_days) or (
        cfg.emerging_tightness_min <= t < cfg.emerging_tightness_max
    ):
        return "emerging"

    return "emerging"


# ── Step 11: Composite Coil Score ────────────────────────────────────────────


def compute_coil_score(
    pct_rate: float,
    r_squared: float,
    tightness_pct: float,
    duration: int,
    cfg: CoilConfig,
) -> float:
    """
    Step 11: Weighted composite score (0–100).
    """
    # Component 1: Convergence rate (25 pts)
    rate_norm = (pct_rate - cfg.rate_floor) / (cfg.rate_ceiling - cfg.rate_floor)
    rate_norm = max(0.0, min(1.0, rate_norm))
    score_rate = rate_norm * cfg.w_rate

    # Component 2: Consistency / R² (25 pts)
    score_r2 = r_squared * cfg.w_consistency

    # Component 3: Tightness percentile (30 pts)
    score_tight = (tightness_pct / 100.0) * cfg.w_tightness

    # Component 4: Duration bell curve (20 pts)
    peak = cfg.duration_peak
    if duration <= 10:
        bell = 0.0
    elif duration <= peak:
        bell = (duration - 10) / (peak - 10)
    elif duration <= 60:
        bell = (60 - duration) / (60 - peak)
    else:
        bell = 0.0
    score_dur = bell * cfg.w_duration

    total = score_rate + score_r2 + score_tight + score_dur
    return round(total, 1)


# ── MA Structure Checks ─────────────────────────────────────────────────────


def check_ma_structure(df: pl.DataFrame, cfg: CoilConfig) -> tuple[bool, bool, str]:
    """
    Pre-filter: check price above all MAs and MA stacking.
    Returns (passed, ma_stacked, fail_reason).
    """
    last = df.row(-1, named=True)

    close = last["close"]
    ef = last["ema_fast"]
    em = last["ema_mid"]
    ss = last["sma_slow"]
    sa = last["sma_anchor"]

    for name, val in [
        ("ema_fast", ef),
        ("ema_mid", em),
        ("sma_slow", ss),
        ("sma_anchor", sa),
    ]:
        if val is None or math.isnan(val):
            return False, False, f"Insufficient data for {name}"

    price_above = close > ef and close > em and close > ss and close > sa
    ma_stacked = ef > em > ss > sa

    if cfg.require_price_above_mas and not price_above:
        return False, ma_stacked, "Price not above all MAs"

    if cfg.require_ma_stacking and not ma_stacked:
        return False, ma_stacked, "MAs not fully stacked"

    return True, ma_stacked, ""


# ── Main Scan for One Symbol ─────────────────────────────────────────────────


@dataclass
class CoilResult:
    symbol: str
    detected: bool = False
    close: float = 0.0
    stage: str = "none"
    score: float = 0.0
    duration: int = 0
    convergence_rate_pct: float = 0.0
    r_squared: float = 0.0
    tightness_pct: float = 0.0
    current_dispersion: float = 0.0
    ma_stacked: bool = False
    fail_reason: str = ""


def scan_symbol(db_path: str, symbol: str, cfg: CoilConfig) -> CoilResult:
    """Run full coil detection pipeline on one symbol."""

    result = CoilResult(symbol=symbol)

    # ── Load data ─────────────────────────────────────────────────────────
    df = load_ohlcv(db_path, symbol, cfg.lookback_bars)
    if df is None:
        result.fail_reason = "Insufficient data"
        return result

    # ── Step 1 & 2: MAs and ATR ───────────────────────────────────────────
    df = compute_indicators(df, cfg)

    # ── MA structure pre-filter ───────────────────────────────────────────
    passed, ma_stacked, reason = check_ma_structure(df, cfg)
    result.ma_stacked = ma_stacked
    result.close = df["close"].to_numpy()[-1]

    if not passed:
        result.fail_reason = reason
        return result

    # ── Step 3 & 4: Dispersion series ─────────────────────────────────────
    df = compute_dispersion(df, cfg)

    # ── Step 5: Rolling slope ─────────────────────────────────────────────
    df = compute_rolling_slope(df, cfg)

    # ── Step 6: Detect coil window ────────────────────────────────────────
    window = detect_coil_window(df, cfg)

    if not window.found:
        result.fail_reason = "No convergence detected (slope not negative)"
        return result

    disp_smooth = df["disp_smooth"].to_numpy()

    # ── Step 7: Convergence rate ──────────────────────────────────────────
    slope, pct_rate, intercept = compute_convergence_rate(
        disp_smooth, window.start_idx, window.end_idx
    )

    if slope >= 0:
        result.fail_reason = "Overall slope not negative across coil window"
        return result

    result.convergence_rate_pct = round(pct_rate, 2)

    # ── Step 8: R² ────────────────────────────────────────────────────────
    r2 = compute_r_squared(
        disp_smooth, window.start_idx, window.end_idx, slope, intercept
    )
    result.r_squared = round(r2, 3)

    # ── Step 9: Tightness percentile ──────────────────────────────────────
    tightness = compute_tightness_percentile(
        disp_smooth, window.end_idx, cfg.percentile_lookback
    )
    result.tightness_pct = round(tightness, 1)

    # ── Step 10: Classify ─────────────────────────────────────────────────
    stage = classify_coil(window, tightness, cfg)
    window.stage = stage

    # ── Step 11: Score ────────────────────────────────────────────────────
    score = compute_coil_score(pct_rate, r2, tightness, window.duration, cfg)

    # ── Populate result ───────────────────────────────────────────────────
    result.detected = True
    result.stage = stage
    result.score = score
    result.duration = window.duration
    result.current_dispersion = round(disp_smooth[window.end_idx], 3)

    return result


# ── Run Screener Across Watchlist ────────────────────────────────────────────


def run_screener(
    db_path: str,
    symbols: list[str],
    cfg: CoilConfig,
    verbose: bool = False,
) -> list[CoilResult]:
    """Scan all symbols and return sorted results."""

    results = []

    for sym in symbols:
        sym = sym.strip().upper()
        if not sym:
            continue

        res = scan_symbol(db_path, sym, cfg)
        results.append(res)

        if verbose:
            if res.detected:
                print(
                    f"  {sym:8s}  ✅ {res.stage:10s}  score={res.score:5.1f}  "
                    f"days={res.duration:3d}  rate={res.convergence_rate_pct:5.2f}%/d  "
                    f"R²={res.r_squared:.3f}  tight={res.tightness_pct:5.1f}%  "
                    f"disp={res.current_dispersion:.3f}"
                )
            else:
                print(f"  {sym:8s}  ❌ {res.fail_reason}")

    # Sort: detected first, then by score descending
    results.sort(key=lambda r: (-r.detected, -r.score))
    return results


# ── Display ──────────────────────────────────────────────────────────────────

STAGE_SYMBOLS = {
    "mature": "🔴",
    "active": "🟡",
    "emerging": "🟢",
    "none": "⚪",
}


def print_results(results: list[CoilResult]):
    """Pretty-print results."""

    detected = [r for r in results if r.detected]
    failed = [r for r in results if not r.detected]

    print("\n" + "=" * 100)
    print("  MA COIL DETECTOR — Moving Average Convergence Screener")
    print("=" * 100)

    if detected:
        # Group by stage
        for stage in ["mature", "active", "emerging"]:
            group = [r for r in detected if r.stage == stage]
            if not group:
                continue

            icon = STAGE_SYMBOLS[stage]
            print(f"\n  {icon} {stage.upper()} ({len(group)} stocks):\n")

            header = (
                f"    {'Symbol':8s} {'Score':>6s} {'Close':>9s} {'Days':>5s} "
                f"{'Rate%/d':>8s} {'R²':>6s} {'Tight%':>7s} {'Disp':>7s} {'Stacked':>8s}"
            )
            print(header)
            print("    " + "─" * 76)

            for r in group:
                stack_str = "yes" if r.ma_stacked else "no"
                print(
                    f"    {r.symbol:8s} {r.score:6.1f} {r.close:9.2f} {r.duration:5d} "
                    f"{r.convergence_rate_pct:8.2f} {r.r_squared:6.3f} {r.tightness_pct:7.1f} "
                    f"{r.current_dispersion:7.3f} {stack_str:>8s}"
                )
    else:
        print("\n  No coiling setups detected.")

    if failed:
        print(f"\n  ── {len(failed)} not coiling:\n")
        for r in failed:
            print(f"    {r.symbol:8s}  {r.fail_reason}")

    print()


# ── CLI ──────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="MA Coil Detector — Swing Trade Screener"
    )
    parser.add_argument("--db", required=True, help="Path to SQLite database")
    parser.add_argument("--watchlist", type=str, help="Comma-separated symbols")
    parser.add_argument(
        "--watchlist-file", type=str, help="File with one symbol per line"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Print per-symbol progress"
    )

    # Overrides
    parser.add_argument("--no-ma-stacking", action="store_true")
    parser.add_argument("--no-price-filter", action="store_true")
    parser.add_argument("--coil-min-days", type=int, default=10)
    parser.add_argument("--coil-max-days", type=int, default=60)

    args = parser.parse_args()

    symbols = []
    if args.watchlist:
        symbols = [s.strip() for s in args.watchlist.split(",")]
    elif args.watchlist_file:
        with open(args.watchlist_file) as f:
            symbols = [line.strip() for line in f if line.strip()]
    else:
        print("Error: provide --watchlist or --watchlist-file")
        sys.exit(1)

    cfg = CoilConfig(
        require_ma_stacking=not args.no_ma_stacking,
        require_price_above_mas=not args.no_price_filter,
        coil_min_days=args.coil_min_days,
        coil_max_days=args.coil_max_days,
    )

    print(f"\n  Scanning {len(symbols)} symbols from {args.db}...\n")
    results = run_screener(args.db, symbols, cfg, verbose=args.verbose)
    print_results(results)


if __name__ == "__main__":
    main()
