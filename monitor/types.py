import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorRule:
    error_type: str
    regex: re.Pattern[str] | None
    severity: str
    min_count: int
