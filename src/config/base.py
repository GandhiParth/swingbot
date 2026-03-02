from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitConfig:
    calls: int
    period: int  # seconds
