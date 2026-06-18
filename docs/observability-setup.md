# Observability Setup

BunkLogs uses Datadog for browser RUM, browser logs, APM tracing, and log management.

## End-to-end correlation on Render (multi-service)

BunkLogs production on Render splits across separate services. Correlation works across
them when each hop uses matching tags and trace propagation — not because they share a
process or agent.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Browser (clc.bunklogs.net)                                                 │
│  Static frontend — no Node/dd-trace at runtime                              │
│                                                                             │
│  @datadog/browser-rum  ──► RUM views, resources, errors, session replay     │
│  @datadog/browser-logs ──► warn/error console + structured logs             │
│         │                                                                   │
│         │  traceContextInjection: 'all' + allowedTracingUrls                │
│         │  injects x-datadog-* / traceparent headers on API calls           │
└─────────┼───────────────────────────────────────────────────────────────────┘
          │ HTTPS  (admin.bunklogs.net)
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  BunkLogs (Render web service — admin.bunklogs.net)                         │
│  ddtrace-run gunicorn                                                       │
│                                                                             │
│  • Continues distributed trace from browser headers                         │
│  • Emits APM spans (Django, DRF, psycopg, Redis) ──► DD_AGENT_HOST:8126     │
│  • DD_LOGS_INJECTION=true adds dd.trace_id to stdout log lines              │
└─────────┼───────────────────────────────────────────────────────────────────┘
          │ private network
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  datadog-agent (private service; internal hostname datadog-agent-fbsh)     │
│  Forwards traces + DogStatsD metrics to Datadog intake                      │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│  clc-bunklogs-postgres (Render Postgres)                                    │
│  Appears as child spans inside backend traces (psycopg instrumentation).    │
│  Not a separate log/trace source.                                           │
└─────────────────────────────────────────────────────────────────────────────┘

Log paths (two separate pipelines, linked by trace_id / session_id):

  Browser logs  ──► browser-intake-datadoghq.com  (direct from SDK, no agent)
  Backend logs  ──► Render stdout ──► Render Log Stream ──► Datadog Logs
```

### Correlation matrix

| Link | Mechanism | Required config |
|------|-----------|-----------------|
| **RUM ↔ Browser Logs** | Same `clientToken`, `site`, `env`, `service`, `version` on both SDKs; shared `session_id` | `initDatadogRum()` initializes Logs immediately after RUM |
| **RUM ↔ Backend APM** | RUM injects trace headers on XHR/fetch to `VITE_API_URL`; ddtrace continues the trace | `allowedTracingUrls`, `traceContextInjection: 'all'`, backend `DD_TRACE_ENABLED=true`, CORS allows `traceparent` + `x-datadog-*` (in `base.py`) |
| **APM ↔ Backend Logs** | `DD_LOGS_INJECTION=true` + log formatter emits `dd.trace_id` / `dd.span_id` | `ddtrace-run`, `config/datadog_logging.py`, Render log stream to Datadog |
| **RUM ↔ Backend Logs** | **Indirect** — pivot through the shared trace in APM, or match `session_id` on browser logs | No direct link; use Traces tab in RUM Explorer |

Datadog documents this explicitly: there is no direct RUM-view ↔ server-log link; you
navigate through traces. See
[Ease troubleshooting with cross-product correlation](https://docs.datadoghq.com/logs/guide/ease-troubleshooting-with-cross-product-correlation/).

### Tag alignment checklist (must match across services)

| Tag | Frontend (`VITE_*`) | Backend (`DD_*` in render.yaml) |
|-----|---------------------|----------------------------------|
| env | `VITE_DATADOG_ENV=prod` | `DD_ENV=prod` |
| service | `bunklogs-frontend` | `bunklogs-backend` |
| version | `VITE_DATADOG_VERSION` | `DD_VERSION` |

Different `service` names are correct (frontend vs backend). **`env` must match** or
traces won't group in the same environment facet.

### Render production service map

| Render dashboard name | Role | APM `DD_SERVICE` / notes |
|-----------------------|------|--------------------------|
| `BunkLogs` | Django API (`admin.bunklogs.net`) | `bunklogs-backend` |
| `BunkLogs-frontend` | Static site (`clc.bunklogs.net`) | RUM `bunklogs-frontend` |
| `datadog-agent` | Private agent (internal: `datadog-agent-fbsh`) | — |
| `bunklogs-celery` | Celery worker | `bunklogs-celery` |
| `bunklogs-redis` | Valkey cache + Celery broker | child spans as `redis` |
| `clc-bunklogs-postgres` | PostgreSQL | child spans as `postgres` |

### Render prerequisites

1. **Backend APM**: `DD_AGENT_HOST=datadog-agent-fbsh` on **BunkLogs** (private network hostname from
   **datadog-agent → Connect**) + agent running with valid `DD_API_KEY`.
2. **Backend logs in Datadog**: Render dashboard → **BunkLogs** → **Log Streams** →
   add Datadog drain with `DD_API_KEY`. Without this, `DD_LOGS_INJECTION` enriches
   stdout but logs never reach Datadog Log Management.
3. **Frontend**: `VITE_DATADOG_ENV=prod` baked in at build time (`frontend/.env.production`
   or Render env vars on **BunkLogs-frontend**).
4. **Redis cache**: `REDIS_URL` linked from `bunklogs-redis` on **BunkLogs** and
   **bunklogs-celery**. Production settings enable TLS when the URL uses `rediss://`.
5. **Postgres**: no extra setup; query spans appear under Django request traces.

### Validate after deploy

1. **RUM → APM**: In Datadog RUM Explorer, open a session → Resources tab → click an
   API call to `admin.bunklogs.net` → should show linked backend trace.
2. **RUM → Browser Logs**: Same session → Logs tab → warn/error console output appears
   with matching `session_id`.
3. **APM → Backend Logs**: APM Trace Explorer → open a trace → Logs tab → Django
   stdout lines with the same `dd.trace_id`.
4. **Network sanity**: Browser DevTools → API request headers include `traceparent`
   and/or `x-datadog-trace-id`.

## Components

### Browser RUM + Logs (frontend)

Packages: `@datadog/browser-rum`, `@datadog/browser-rum-react`, `@datadog/browser-logs`.

Initialized in `frontend/src/lib/datadog.js`:

- **RUM**: views (via `createBrowserRouter`), errors, session replay, API resource timing.
- **Logs**: `forwardErrorsToLogs`, `forwardConsoleLogs: ['error', 'warn']`, plus
  `logToDatadog()` for structured messages.
- **Trace propagation**: headers injected on requests to `VITE_API_URL`.

Browser telemetry goes **directly** to Datadog intake — it does not route through the
Render Datadog Agent.

### ddtrace (backend APM)

`ddtrace==4.7.1` in base.txt. Django starts via `ddtrace-run gunicorn` (see `render.yaml`).

- Traces sent to `DD_AGENT_HOST:8126`.
- Log injection via `DD_LOGS_INJECTION=true` and `config/datadog_logging.py`.

### Log forwarding (Render → Datadog)

Render streams stdout/stderr. Forward to Datadog:

1. Render dashboard → **Log Streams** → **Add Log Stream** → Datadog
2. Paste `DD_API_KEY`, select site `datadoghq.com`

### Custom metrics (DogStatsD)

UDP to agent port 8125. See `bunk_logs/utils/metrics.py`.

## Environment Variables

| Variable | Frontend | Backend | Description |
|----------|----------|---------|-------------|
| `DD_ENV` / `VITE_DATADOG_ENV` | `prod` | `prod` | **Must match** for cross-product correlation |
| `DD_SERVICE` / `VITE_DATADOG_SERVICE` | `bunklogs-frontend` | `bunklogs-backend` | Different per tier (expected) |
| `DD_VERSION` / `VITE_DATADOG_VERSION` | `1.0.0` | `1.0` | Release tag |
| `DD_LOGS_INJECTION` | — | `true` | Injects trace IDs into Django log records |
| `DD_TRACE_ENABLED` | — | `true` | Master switch for APM |
| `DD_AGENT_HOST` | — | `datadog-agent-fbsh` | Private Render agent hostname (from datadog-agent → Connect) |
| `VITE_DATADOG_CLIENT_TOKEN` | required | — | Shared by RUM + Logs SDKs |
| `VITE_DATADOG_APPLICATION_ID` | required | — | RUM application ID |

## Local Development

Tracing disabled by default (`DD_TRACE_ENABLED=false`). To test full correlation locally:

```bash
# Terminal 1: local Datadog Agent (optional)
docker run -d --name dd-agent \
  -e DD_API_KEY=<key> -e DD_SITE=datadoghq.com \
  -p 8125:8125/udp -p 8126:8126/tcp \
  gcr.io/datadoghq/agent:7

# .envs/.local/.django
DD_TRACE_ENABLED=true
DD_LOGS_INJECTION=true
DD_ENV=development
DD_AGENT_HOST=localhost

# frontend/.env
VITE_DATADOG_FORCE_ENABLE=true
VITE_DATADOG_ENV=development
# + application ID and client token
```

`ddtrace` "failed to send traces to localhost:8126" without an agent is harmless.

## Synthetic Checks

Definitions in `docs/synthetics.yml`.
