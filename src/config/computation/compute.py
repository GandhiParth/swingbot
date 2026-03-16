from config.base import StorageConfig


class EditConfig:
    FOLDER_NAME = "compute"
    MIDSML_400_INDEX = "NIFTY MIDSML 400"
    SMLCAP_250_INDEX = "NIFTY SMLCAP 250"


class ComputeConfig(EditConfig):
    RS_INDEX = EditConfig.MIDSML_400_INDEX
    DATA_PATH = StorageConfig().store_root(EditConfig.FOLDER_NAME)

    MKT_DB_STOCKS_PATH = "market_dashboard_stocks_data.csv"
    MKT_DB_INDICES_PATH = "market_dashboard_indices_data.csv"

    MKT_BREADTH_DAYS = 10
    MKT_BREADTH_PATH = "market_breadth_lookback_data.csv"

    BASIC_SCAN_PATH = "basic_scan_data.csv"
    BASIC_FILTER_PATH = "basic_filter_data.csv"
    ADR_FILTER_PATH = "adr_filter_data.csv"
    PULLBACK_FILTER_PARQ_PATH = "pullback_filter_data.parquet"
    FILTER_RESULT_PATH = "overall_filter_result_data.csv"
