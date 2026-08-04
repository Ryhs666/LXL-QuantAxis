# Release and Rollback Runbook

## Release gate

Tests, type checking, lint, security scan, package build, and a backup/restore drill must all pass.
Deploy the new version with Classic routes and the Professional Dashboard flag still available.

## Rollback

1. Activate the paper kill switch if execution behavior is implicated.
2. Route users back to Classic Dashboard and the previous API implementation.
3. Deploy the previous application artifact; do not downgrade expand-only database changes.
4. Verify login, research reads, portfolio reconciliation, and deterministic Daily Brief output.
5. Re-enable paper execution only after reconciliation and two-person approval.
