#!/usr/bin/env bash
# Wraps every Render process command with ddtrace-run and tags traces with the
# deployed commit, which is what lets Datadog resolve source code links.
# Render injects RENDER_GIT_COMMIT (full 40-char SHA) at runtime; when it is
# absent (local runs) the tags are simply omitted.
set -o errexit

export DD_GIT_REPOSITORY_URL="https://github.com/pantheonsteve/BunkLogs"

if [ -n "${RENDER_GIT_COMMIT:-}" ]; then
  export DD_GIT_COMMIT_SHA="$RENDER_GIT_COMMIT"
  export DD_VERSION="$RENDER_GIT_COMMIT"
fi

exec ddtrace-run "$@"
