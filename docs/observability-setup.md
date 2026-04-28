# Observability Setup

BunkLogs uses Datadog for APM tracing, log management, and custom metrics.

## Architecture

```
Render (Django) ──ddtrace-run──► Datadog Agent (if present)
                                       │
                                       ├── Traces  → Datadog APM
                                       ├── Metrics → Datadog Metrics
                                       └── Logs    → Datadog Log Management

Render logs ──► Render Log Drain ──► Datadog Log Management (always on)
```

## Components

### ddtrace (APM tracing)

`ddtrace==4.7.1` is installed in all environments (base.txt). The Django process
starts via `ddtrace-run gunicorn ...` which auto-instruments Django, DRF, psycopg,
and Redis without code changes.

- **Traces**: sent to `DD_AGENT_HOST:8126` (TCP). Dropped silently if no agent.
- **Log injection**: when `DD_LOGS_INJECTION=true`, trace/span IDs are injected
  into every log line so logs and traces correlate in the Datadog UI.

### Log forwarding (Render → Datadog)

Render streams all stdout/stderr to its log drain. To forward to Datadog:

1. Render dashboard → **Environment** → **Log Streams** → **Add Log Stream**
2. Select **Datadog**
3. Paste your **DD_API_KEY** and choose the correct Datadog site (e.g. `datadoghq.com`)
4. Save — logs start flowing within minutes

No code changes are required for log forwarding.

### Custom metrics (DogStatsD)

Custom metrics are sent via UDP to the Datadog Agent on port 8125.

| Metric | Type | Tags | Source |
|--------|------|------|--------|
| `bunklogs.reflections.submitted` | counter | `tenant`, `env`, `service` | Reflection model signal (Phase 2) |
| `bunklogs.users.logged_in` | counter | `method`, `env`, `service` | `user_logged_in` signal |

Metrics silently no-op when `DD_AGENT_HOST` is unreachable (e.g. local dev without agent).

To add a new metric, call `_send()` from `bunk_logs/utils/metrics.py` or add a
typed helper alongside the existing ones.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DD_API_KEY` | — | **Required in production.** Set in Render dashboard, never commit. |
| `DD_ENV` | `development` / `production` | Separates dev/prod in Datadog |
| `DD_SERVICE` | `bunklogs` | Service name shown in APM |
| `DD_VERSION` | `""` | App version tag (set to git SHA in CI for deployment tracking) |
| `DD_AGENT_HOST` | `localhost` | Hostname of the Datadog Agent. Leave unset on Render unless running an agent service. |
| `DD_DOGSTATSD_PORT` | `8125` | DogStatsD UDP port |
| `DD_TRACE_ENABLED` | `false` (dev) / `true` (prod) | Master switch for APM traces |
| `DD_LOGS_INJECTION` | `false` (dev) / `true` (prod) | Injects trace IDs into Django log records |

## Enabling in Production (Render)

All DD env vars are declared in `render.yaml`. Only `DD_API_KEY` requires manual
entry in the Render dashboard (it is marked `sync: false` to avoid accidental
commits).

Steps:
1. Render dashboard → `bunklogs-backend` → **Environment**
2. Add `DD_API_KEY` with your Datadog API key
3. Optionally set `DD_VERSION` to the current release SHA
4. Redeploy — `ddtrace-run` will pick up the vars at startup

## Running a Datadog Agent on Render (optional, for full APM)

Render does not support sidecars. To get APM traces (not just logs) in production:

**Option A – Render Background Worker as Agent** (not recommended; agent is heavyweight)

**Option B – Datadog Agentless Tracing** (ddtrace 2.x+ supports sending traces
directly to the Datadog intake without an agent):
```
DD_TRACE_AGENT_URL=https://trace.agent.datadoghq.com
DD_API_KEY=<your key>
```
Set `DD_TRACE_AGENT_URL` in the Render dashboard alongside `DD_API_KEY`.

**Option C – Logs only** (current default): rely on Render log drain + log injection
for correlated traces via logs. This is zero-infrastructure-cost and sufficient for
most debugging needs.

## Local Development

ddtrace is installed locally but tracing is disabled by default (`DD_TRACE_ENABLED=false`).
The app starts normally without any Datadog agent running.

To test metrics locally:
```bash
# Start a local Datadog Agent (requires a Datadog account)
docker run -d --name dd-agent \
  -e DD_API_KEY=<your-key> \
  -e DD_SITE=datadoghq.com \
  -p 8125:8125/udp \
  -p 8126:8126/tcp \
  gcr.io/datadoghq/agent:7

# Then in .envs/.local/.django add:
DD_TRACE_ENABLED=true
DD_LOGS_INJECTION=true
DD_AGENT_HOST=localhost
```

## Synthetic Checks

Synthetic monitor definitions are in `docs/synthetics.yml`. Import them via the
Datadog API or Terraform provider (`datadog_synthetics_test` resource).
