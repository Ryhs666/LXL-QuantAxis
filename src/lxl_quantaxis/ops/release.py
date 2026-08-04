"""Release and rollback gate evaluation."""

from dataclasses import dataclass

REQUIRED_GATES = frozenset({"tests", "types", "lint", "security", "build", "backup_restore"})


@dataclass(frozen=True, slots=True)
class ReleaseDecision:
    approved: bool
    failed_gates: tuple[str, ...]


def evaluate_release(results: dict[str, bool]) -> ReleaseDecision:
    missing = REQUIRED_GATES - set(results)
    failed = sorted(missing | {name for name in REQUIRED_GATES if not results.get(name, False)})
    return ReleaseDecision(not failed, tuple(failed))
