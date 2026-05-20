# Step 7_17: Performance Pass

**Goal:** Hit performance targets specified in story acceptance criteria, particularly dashboard FCP, search responsiveness, and virtualized list scrolling.

**Depends on:** Steps 7_1 through 7_15.

**Scope of this step:**

1. Frontend: dashboard FCP targets per acceptance criteria:
   1. Counselor dashboard (Story 2 criterion 6): under 2s on mid-tier Android 4G
   2. Kitchen Staff dashboard (Story 37 criterion 7): under 2s
   3. Admin dashboard (Story 54 criterion 8): under 2s with sections loading independently
   4. Madrich dashboard (Story 61 criterion 8): under 2s
2. Frontend: verify virtualized list performance:
   1. Specialist camper picker (Story 25 criterion 4): responsive at 1,500 active campers
   2. Maintenance queue (Story 30 criterion 8): responsive at 500+ tickets backlog
   3. Camper Care caseload tree: responsive at 50+ bunks
3. Backend: Global search performance (Story 59 / A10): sub-2-second for typical org (5 years of camp data simulating ~50K reflections, ~10K notes, ~5K orders/tickets).
4. Backend: dashboard query optimization. Profile each role's dashboard endpoint and apply select_related/prefetch_related to eliminate N+1 queries.
5. Backend: translation pipeline backpressure. Verify under simulated load (100 reflections submitted in 10 minutes) the Celery queue handles fan-out without backing up.
6. Backend: cache strategy. Cache dashboard payloads for 30 seconds per Story 6 with invalidation on relevant content changes. Verify cache hit rate via Datadog metrics.
7. Frontend: code splitting. Each role's dashboard should code-split such that a Counselor doesn't download the Admin bundle.
8. Frontend: image upload optimization. Maintenance ticket photos and any other uploads should resize on the client to a reasonable bound before upload.
9. Documentation: `docs/performance_targets.md` with measured baseline numbers and pass/fail per criterion.

**Commit scope: `perf(7_17_performance_pass): ...`. PR title prefix: `7_17`.**
