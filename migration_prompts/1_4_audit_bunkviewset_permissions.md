`BunkViewSet` is currently configured with `AllowAny` permissions. Determine whether this is intentional and either document why or lock it down.

Tasks:
1. Locate BunkViewSet and confirm its current permission configuration.
2. Check git blame to understand when AllowAny was added and why.
3. Find all callers of the bunk list endpoint:
   a) Frontend: search the React codebase
   b) Any external scripts or integrations
4. Determine whether unauthenticated access is required:
   - If yes: document the reason in a docstring; consider exposing a separate read-only public endpoint instead
   - If no: change to IsAuthenticated and update any callers
5. Add a test that verifies the chosen permission behavior.

Acceptance criteria:
- Permission decision documented with rationale
- If locked down: authenticated callers still work, unauthenticated receive 401/403
- If kept open: docstring explains why
- Tests verify the behavior
- Commit with message: "Audit and document BunkViewSet permissions"