import logging
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from ratelimit import limits, sleep_and_retry

from config.data_sources import NSEConfig
from config.data_sources.nse import DownloadSoure, IndexConfig


class IndexDownloader:
    def __init__(self, download_path: str):

        self._download_path = Path(download_path)
        self._download_path.mkdir(parents=True, exist_ok=True)

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

        self.logger = logging.getLogger(self.__class__.__name__)

    @sleep_and_retry
    @limits(
        calls=NSEConfig.INDICES_DOWNLOAD_RATE_LIMIT.calls,
        period=NSEConfig.INDICES_DOWNLOAD_RATE_LIMIT.period,
    )
    def download(self, config: IndexConfig):
        if config.source == DownloadSoure.NSE:
            try:
                self._download_from_nse(config)
                self.logger.debug(f"{config.name} downloaded successfully")
            except Exception as e:
                self.logger.error(f"{config.name} download failed. Error: {e}")

        elif config.source == DownloadSoure.NSE_INDICES:
            try:
                self._download_from_nse_indices(config)
                self.logger.debug(f"{config.name} downloaded successfully")
            except Exception as e:
                self.logger.error(f"{config.name} download failed. Error: {e}")

        else:
            raise ValueError("Unsupported source")

    def _download_from_nse(self, config: IndexConfig):

        self.session.get(NSEConfig.NSE_URL)

        response = self.session.get(config.url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        link = soup.find("a", href=lambda h: h and h.endswith(".csv"))

        if not link:
            raise ValueError("CSV link not found")

        file_url = link["href"]

        file_response = self.session.get(file_url)
        file_response.raise_for_status()

        file_path = self._download_path / config.filename

        with open(file_path, "wb") as f:
            f.write(file_response.content)

    def _download_from_nse_indices(self, config: IndexConfig):
        response = self.session.get(config.url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        link = soup.find("a", string="Index Constituent")

        if not link:
            raise ValueError("Index Constituent link not found")

        relative_href = link["href"]
        absolute_url = urljoin(config.url, relative_href)

        file_response = self.session.get(absolute_url)
        file_response.raise_for_status()

        file_path = self._download_path / config.filename

        with open(file_path, "wb") as f:
            f.write(file_response.content)
