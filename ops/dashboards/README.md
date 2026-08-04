# LXL QuantAxis Operations Dashboard

The production dashboard must expose four linked views using the same correlation ID:

1. **Research workflow:** completion rate, degraded briefs, evidence rejection rate, LLM cost.
2. **Data health:** provider freshness, schema failures, reconciliation failures.
3. **Paper execution:** submitted/rejected/filled orders, reconciliation state, kill-switch state.
4. **Platform:** API latency/error rate, task duration, backup age and release-gate status.

Alert when the 30-minute API success SLO falls below 99.5%, any paper reconciliation fails,
the kill switch changes state, or the latest verified backup is older than 24 hours.
