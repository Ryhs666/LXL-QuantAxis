# Backup and Restore Runbook

1. Stop new Alpha Memory writes; reads and Classic Dashboard may remain available.
2. Create a SQLite backup with `create_backup` and record its SHA-256 checksum and timestamp.
3. Restore into a new, explicitly named database path—never over the only verified backup.
4. Run schema checks, organization-isolation tests, row counts, and a sample research read.
5. Point one non-production instance at the restored database and run the smoke suite.
6. Promote only after two-person approval. Keep the previous database for rollback.

A checksum mismatch is a hard stop. Do not attempt a partial or unverified restore.
