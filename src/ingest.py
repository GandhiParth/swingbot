import logging
from pathlib import Path

import polars as pl

from config.ingestion.data_sources import NSEConfig
from ingestion.data_sources.nse import NSEIndexDownloader
from utils import setup_logger

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
