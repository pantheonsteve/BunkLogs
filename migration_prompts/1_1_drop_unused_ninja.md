The file `requirements/base.txt` includes `django-ninja` but it's never imported anywhere in the codebase. Remove it.

Tasks:
1. Verify django-ninja is not imported anywhere: search the entire codebase (.py files only) for `import ninja`, `from ninja`, and `django_ninja`. Confirm zero matches.
2. Remove `django-ninja` from `requirements/base.txt`.
3. Run `pip-compile` (or equivalent) if there are pinned requirements files generated from base.txt.
4. Rebuild the Podman dev container and verify the app still starts.
5. Run the test suite: `pytest`. All previously-passing tests should still pass.

Acceptance criteria:
- `grep -r "ninja" --include="*.py" .` returns no Python imports
- `requirements/base.txt` does not contain django-ninja
- App starts cleanly
- All tests pass
- Commit with message: "Remove unused django-ninja dependency"