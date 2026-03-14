from config.base import StorageConfig


class EditConfig:
    FOLDER_NAME = "compute"

    MKT_DB_STOCKS_PATH = "market_dashboard_stocks_data.csv"
    MKT_DB_INDICES_PATH = "market_dashboard_indices_data.csv"


class ComputeConfig(EditConfig):

    DATA_PATH = StorageConfig().store_root(EditConfig.FOLDER_NAME)
