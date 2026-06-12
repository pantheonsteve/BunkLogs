"""Datadog log-trace correlation for Django LOGGING.

When ``DD_LOGS_INJECTION=true`` and the app runs under ``ddtrace-run``, ddtrace
patches ``logging`` and adds ``dd.trace_id``, ``dd.span_id``, etc. to each
LogRecord. The formatter must emit those fields so Render's log drain (or any
collector) can correlate logs with APM traces.

See: https://docs.datadoghq.com/tracing/other_telemetry/connect_logs_and_traces/python/
"""

DATADOG_LOG_FORMAT = (
    "%(levelname)s %(asctime)s %(name)s "
    "[dd.service=%(dd.service)s dd.env=%(dd.env)s dd.version=%(dd.version)s "
    "dd.trace_id=%(dd.trace_id)s dd.span_id=%(dd.span_id)s] "
    "%(message)s"
)


def apply_log_injection(logging_config: dict) -> None:
    """Augment a Django LOGGING dict in place for Datadog trace correlation."""
    formatters = logging_config.setdefault("formatters", {})
    formatters["datadog"] = {"format": DATADOG_LOG_FORMAT}

    handlers = logging_config.setdefault("handlers", {})
    console = handlers.setdefault(
        "console",
        {
            "level": "INFO",
            "class": "logging.StreamHandler",
        },
    )
    console["formatter"] = "datadog"

    loggers = logging_config.setdefault("loggers", {})
    loggers.setdefault(
        "ddtrace",
        {
            "handlers": ["console"],
            "level": "WARNING",
        },
    )
    loggers.setdefault(
        "bunk_logs",
        {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    )
