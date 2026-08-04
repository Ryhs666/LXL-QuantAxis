# Incident Response Runbook

## Trigger

Use this runbook for sustained API errors, stale research data, failed reconciliation, or an
unexpected paper order. Record the incident owner, start time, affected organization, and
correlation IDs before changing state.

## Contain

1. Activate the operational kill switch when order safety or reconciliation is uncertain.
2. Leave accepted evidence and immutable ledgers intact; do not edit historical records.
3. Degrade AI workflows to deterministic summaries when model or evidence services fail.
4. Capture logs, metrics, traces, provider revisions, order IDs, and the latest backup checksum.

## Recover

Restore service one dependency at a time. Reconcile orders, fills, ledger, cash, and positions
before disabling the kill switch. The incident owner and a second reviewer must record the reason.

## Close

Confirm SLO recovery, preserve the timeline, add a regression test, and document follow-up work.
