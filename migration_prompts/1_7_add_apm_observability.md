Add Datadog APM and log forwarding. Steve works at Datadog and wants to dogfood the product.

Tasks:
1. Add `ddtrace` to requirements/base.txt (latest stable).
2. Configure ddtrace for Django via standard `ddtrace-run` or auto-instrumentation. Add config to settings.py.
3. Set environment variables for Datadog (placeholders; real key set in Render).
4. Document log forwarding setup in `docs/observability-setup.md`.
5. Add basic synthetic check definitions for login and reflection submission endpoints.
6. Add custom metrics: count of reflections submitted, count of users logged in.

Acceptance criteria:
- App starts without Datadog credentials (graceful degradation)
- ddtrace configured but not crashing in dev
- Documentation explains production enablement
- Commit with message: "Add Datadog APM and log forwarding"