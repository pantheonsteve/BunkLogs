"""Custom Datadog metrics via DogStatsD UDP.

Sends counters to the Datadog Agent on DD_AGENT_HOST:DD_DOGSTATSD_PORT.
Silently no-ops when no agent is reachable, so local dev is unaffected.

Usage:
    from bunk_logs.utils.metrics import reflection_submitted, user_logged_in
    reflection_submitted(tenant="crane-lake")
    user_logged_in()
"""

import logging
import os
import socket

logger = logging.getLogger(__name__)


def _send(metric: str, value: int = 1, tags: dict | None = None) -> None:
    host = os.environ.get("DD_AGENT_HOST", "localhost")
    port = int(os.environ.get("DD_DOGSTATSD_PORT", "8125"))
    base_tags = [
        f"env:{os.environ.get('DD_ENV', 'development')}",
        f"service:{os.environ.get('DD_SERVICE', 'bunklogs')}",
    ]
    extra = [f"{k}:{v}" for k, v in (tags or {}).items()]
    payload = f"{metric}:{value}|c|#{','.join(base_tags + extra)}".encode()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(payload, (host, port))
    except OSError:
        pass


def reflection_submitted(tenant: str = "unknown") -> None:
    """Increment bunklogs.reflections.submitted counter."""
    _send("bunklogs.reflections.submitted", tags={"tenant": tenant})


def user_logged_in(method: str = "password") -> None:
    """Increment bunklogs.users.logged_in counter."""
    _send("bunklogs.users.logged_in", tags={"method": method})
