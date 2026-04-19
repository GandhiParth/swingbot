from config.base import StorageConfig


class EditConfig:
    FOLDER_NAME = "compute"
    MIDSML_400_INDEX = "NIFTY MIDSML 400"
    SMLCAP_250_INDEX = "NIFTY SMLCAP 250"
    ATR_DAYS = 20


class ComputeConfig(EditConfig):
    RS_INDEX = EditConfig.MIDSML_400_INDEX
    DATA_PATH = StorageConfig().store_root(EditConfig.FOLDER_NAME)

    MKT_DB_STOCKS_PATH = "market_dashboard_stocks_data.csv"
    MKT_DB_INDICES_PATH = "market_dashboard_indices_data.csv"

    MKT_BREADTH_DAYS = 30
    MKT_BREADTH_PATH = "market_breadth_lookback_data.csv"
    MKT_REGIME_PATH = "market_regime_lookback_data.csv"

    BASIC_SCAN_PATH = "basic_scan_data.csv"
    BASIC_FILTER_PATH = "basic_filter_data.csv"
    ADR_FILTER_PATH = "adr_filter_data.csv"
    PULLBACK_FILTER_PARQ_PATH = "pullback_filter_data.parquet"
    FILTER_RESULT_PATH = "overall_filter_result_data.csv"

    STOCKS_RS_PATH = "stocks_relatove_strength.csv"
    STOCKS_DSP_PATH = "stocks_dispersion_score.csv"

    BASIC_SHORT_SCAN_PATH = "short_basic_scan_data.csv"
    BASIC_SHORT_FILTER_PATH = "short_basic_filter_data.csv"
    ADR_SHORT_FILTER_PATH = "short_adr_filter_data.csv"
    FILTER_SHORT_RESULT_PATH = "short_overall_filter_result_data.csv"
