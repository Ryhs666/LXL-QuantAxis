"""Schema violations returned without coupling providers to gate policy."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SchemaViolation:
    code: str
    message: str
