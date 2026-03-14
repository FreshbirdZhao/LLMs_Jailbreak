from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    timeout: int = 30
    max_retries: int = 0
    retry_backoff: float = 0.0

    def __post_init__(self):
        object.__setattr__(self, "timeout", max(1, int(self.timeout)))
        object.__setattr__(self, "max_retries", max(0, int(self.max_retries)))
        object.__setattr__(self, "retry_backoff", max(0.0, float(self.retry_backoff)))
