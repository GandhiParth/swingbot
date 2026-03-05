from dataclasses import dataclass
from pathlib import Path

BASE_PATH = "/home/parthgandhi/data"


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
