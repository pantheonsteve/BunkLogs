# Step 7_18: Observability Dashboards

**Goal:** Create Datadog dashboards for the new role-based platform surfaces. Anthropic's first SaaS deployment of this is also a self-monitoring case study; the observability work should reflect that.

**Depends on:** Steps 7_1 through 7_15.

**Scope of this step:**

1. Datadog dashboard: **Platform health**. Org-aggregate metrics:
   1. Active Memberships by role (over time, per program)
   2. Today's reflection completion rate by role (per org, per program)
   3. Open orders and tickets counts (per org)
   4. Active Camper Care flags counts (per org)
2. Datadog dashboard: **Translation pipeline**:
   1. `bunklogs.translation.submitted` rate
   2. `bunklogs.translation.completed` rate
   3. `bunklogs.translation.failed` rate
   4. `bunklogs.translation.tokens_used` cumulative + per-period
   5. P50, P95, P99 translation latency
   6. Anthropic API error rate
3. Datadog dashboard: **Email delivery**:
   1. Reminder email send success rate
   2. Digest email send success rate (per org)
   3. Email delivery latency
   4. SendGrid/Postmark API error rate
4. Datadog dashboard: **State machine activity**:
   1. Order/ticket transitions per state (per program)
   2. Time-to-first-acknowledgment (P50, P95)
   3. Time-to-fulfillment (P50, P95)
   4. Stale-order count (open past configured threshold)
5. Datadog monitor: digest delivery failure. Alert Admins via configured email when a digest fails 3+ consecutive days.
6. Datadog monitor: translation pipeline sustained failure. Alert platform team when failure rate exceeds 5% over 30 minutes.
7. Datadog monitor: dashboard FCP regression. Alert when any role's dashboard FCP exceeds 2.5s P95.
8. Datadog RUM: track frontend errors per role flow. Identify the highest-error-rate user journey.
9. Documentation: `docs/observability.md` documenting all dashboards, metrics, monitors, alerts, and on-call response procedures.

**Commit scope: `feat(7_18_observability_dashboards): ...`. PR title prefix: `7_18`.**
