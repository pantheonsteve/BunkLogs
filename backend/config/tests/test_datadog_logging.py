from config.datadog_logging import DATADOG_LOG_FORMAT
from config.datadog_logging import apply_log_injection


def test_datadog_log_format_includes_correlation_fields():
    for field in ("dd.trace_id", "dd.span_id", "dd.service", "dd.env", "dd.version"):
        assert field in DATADOG_LOG_FORMAT


def test_apply_log_injection_sets_console_formatter():
    logging_config = {
        "version": 1,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "verbose",
            },
        },
        "formatters": {
            "verbose": {"format": "%(message)s"},
        },
    }

    apply_log_injection(logging_config)

    assert "datadog" in logging_config["formatters"]
    assert logging_config["handlers"]["console"]["formatter"] == "datadog"
    assert "bunk_logs" in logging_config["loggers"]
    assert "ddtrace" in logging_config["loggers"]
