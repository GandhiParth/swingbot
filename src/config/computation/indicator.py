class IndicatorConfig:
    LOOKBACK_RETURN_PCT = {1: "1D", 5: "1W", 21: "1M", 63: "3M", 126: "6M"}

    LOOKBACK_DAYS_TO_MIN_RETURN_PCT = {
        1: 4.99,  # close today ≥ close 1 day ago * 1.05
        5: 7.5,  # close today ≥ close 5 day ago * 1.075
        21: 10,  # close today ≥ close 21 days ago * 1.10
        63: 20,  # close today ≥ close 63 days ago * 1.22
        126: 60,  # close today ≥ close 126 days ago * 1.60
    }

    SMA_DAYS = [50, 200]
    EMA_DAYS = [9, 21]
    VOL_SMA_DAYS = [20, 50]
    CLEAN_SCORE_DAYS = [20, 50]
    ADR_DAYS = [20]
