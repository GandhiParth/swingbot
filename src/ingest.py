import logging
from pathlib import Path

import polars as pl

from config.ingestion.data_sources import NSEConfig
from ingestion.data_sources.nse import NSEIndexDownloader
from kiteconnect import KiteConnect
from ingestion.brokers.kite import KiteHistorical
from config.ingestion.brokers import KiteConfig

logger = logging.getLogger(__name__)


def fetch_nse_indices(download_flag: bool = True) -> pl.DataFrame:
    """
    Fetches the NSE Indices File and Return their DataFrame
    """

    download_path = NSEConfig.INDICES_DOWNLOAD_PATH
    if download_flag:
        indices_config = NSEConfig.MARKET_INDICES + NSEConfig.SECTOR_INDICES
        nse_index_downloader = NSEIndexDownloader(download_path=download_path)
        for i in indices_config:
            nse_index_downloader.download(i)

        logger.info("NSE Indices Download Complete")

    market_idx_map_df = pl.DataFrame(
        [
            {
                "filename": Path(cfg.filename).stem,
                "index_name": cfg.name,
                "index_type": "MARKET",
            }
            for cfg in NSEConfig.MARKET_INDICES
        ]
    ).lazy()
    sector_idx_map_df = pl.DataFrame(
        [
            {
                "filename": Path(cfg.filename).stem,
                "index_name": cfg.name,
                "index_type": "SECTOR",
            }
            for cfg in NSEConfig.SECTOR_INDICES
        ]
    ).lazy()

    mapping_df = pl.concat([market_idx_map_df, sector_idx_map_df])

    dfs = []

    for file in download_path.glob("*.csv"):
        try:
            df = (
                pl.read_csv(file)
                .lazy()
                .select("Symbol")
                .rename({"Symbol": "symbol"})
                .with_columns(pl.lit(file.stem).alias("filename"))
            )
            dfs.append(df)
        except Exception as e:
            logger.error(f"Failed for {file}. Error: {e}")

    indices_df = (
        pl.concat(dfs)
        .join(mapping_df, on="filename", how="left")
        .drop(["filename"])
        .collect()
    )

    return indices_df


def fetch_nse_indices_data(
    kite: KiteConnect,
    instruments_df: pl.DataFrame,
    indices_lst: list,
    start_date: str,
    end_date: str,
    frequency: str,
):

    kite_indices = (
        instruments_df.filter(pl.col("name").is_in(indices_lst))
        .get_column("name")
        .to_list()
    )

    logger.warning(
        f"Following Indices not Mapped with Kite Instruments: {list(set(indices_lst) - set(kite_indices))}"
    )

    index_fetch_df = instruments_df.filter(pl.col("name").is_in(indices_lst)).select(
        "symbol", "instrument_token"
    )

    kite_hist = KiteHistorical(
        kite=kite, instruments_df=index_fetch_df, config=KiteConfig
    )
    kite_hist.get_historical_data(
        start_date=start_date,
        end_date=end_date,
        frequency=frequency,
        db_conn=KiteConfig.DB_CONN,
        insert_table_name=KiteConfig.get_db_tbl(
            KiteConfig.TYP_INDICES, frequency=frequency, failed_tbl=False
        ),
        failed_table_name=KiteConfig.get_db_tbl(
            KiteConfig.TYP_INDICES, frequency=frequency, failed_tbl=True
        ),
    )
