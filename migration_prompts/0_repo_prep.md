Set up the repository for productive agentic development.

Tasks:
1. Create a CLAUDE.md (or AGENTS.md) at repo root containing:
   - Project overview and stack
   - Local dev setup instructions (Podman commands, env vars, common gotchas)
   - How to run tests (backend pytest, frontend Vitest)
   - How to run linters (ruff for Python, eslint for JS)
   - Project conventions (naming, file organization, where new code goes)
   - The multi-tenant migration context (link to this prompt sequence document)

2. Create a docs/ directory if it doesn't exist. Move any existing documentation into it.

3. Create a .env.example with all required environment variables (with placeholder values).

4. Verify the test suite runs cleanly from a fresh clone: pytest && cd frontend && npm test.

5. Verify the linter passes: ruff check && cd frontend && npm run lint.

6. Document any known failing tests or lint issues in docs/known-issues.md so they don't get re-flagged.

Acceptance criteria:
- CLAUDE.md exists and is comprehensive
- .env.example covers all required vars
- Tests and linters either pass or have documented exceptions
- Commit with message: "Add agentic development setup documentation"