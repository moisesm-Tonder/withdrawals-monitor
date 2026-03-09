from monitor.rules import ERROR_PREFIX, RULES
from monitor.types import ErrorRule


def classify_error(message: str) -> ErrorRule | None:
    if not ERROR_PREFIX.search(message):
        return None
    for rule in RULES:
        if rule.regex is not None and rule.regex.search(message):
            return rule
    return next(rule for rule in RULES if rule.error_type == "other_disbursement_error")
