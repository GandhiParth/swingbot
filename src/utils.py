import configparser
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from config.base import BASE_PATH

logger = logging.getLogger(__name__)


def setup_logger():
    root_logger = logging.getLogger()
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(funcName)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler()],
    )


def read_ini_file(file_location: str) -> Optional[configparser.ConfigParser]:
    """
    Reads an ini file and returns a ConfigParser object.

    Parameters:
    file_location (str): The path to the ini file.

    Returns:
    Optional[configparser.ConfigParser]: The ConfigParser object if the file exists, None otherwise.
    """

    if not Path(file_location).exists():
        logger.warning(f"File: {file_location} does not exist")
        return None

    config = configparser.ConfigParser()
    config.read(file_location)

    return config


@dataclass(frozen=True)
class RateLimitConfig:
    calls: int
    period: int  # seconds


@dataclass
class StorageConfig:
    base_dir: Path = Path(BASE_PATH)

    def __post_init__(self):
        self.base_dir = self.base_dir.resolve()

    def store_root(self, *subpaths: str, create: bool = True) -> Path:
        path = self.base_dir / "store"
        if subpaths:
            path = path.joinpath(*subpaths)

        if create:
            path.mkdir(parents=True, exist_ok=True)

        return path

    def tmp_root(self, *subpaths: str, create: bool = True) -> Path:
        path = self.base_dir / "tmp"
        if subpaths:
            path = path.joinpath(*subpaths)

        if create:
            path.mkdir(parents=True, exist_ok=True)

        return path
