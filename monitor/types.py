import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ErrorRule:
    error_type: str
    regex: re.Pattern[str] | None
    severity: str
    min_count: int


@dataclass(frozen=True)
class IncidentContext:
    withdrawal_id: str = ""
    lambda_request_id: str = ""
    clave_rastreo: str = ""
    descripcion_error: str = ""
    stp_result_id: str = ""

    def score(self) -> int:
        return sum(
            bool(value)
            for value in (
                self.withdrawal_id,
                self.lambda_request_id,
                self.clave_rastreo,
                self.descripcion_error,
                self.stp_result_id,
            )
        )
