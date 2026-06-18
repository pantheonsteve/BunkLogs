import json
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest


@pytest.mark.django_db
def test_health_check_reports_redis_error(rf, monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://redis:6379/0")

    mock_conn = MagicMock()
    mock_conn.ping.side_effect = ConnectionError("connection refused")

    with patch("django_redis.get_redis_connection", return_value=mock_conn):
        from config.views import health_check

        response = health_check(rf.get("/health/"))

    assert response.status_code == 200
    payload = json.loads(response.content)
    assert payload["status"] == "healthy"
    assert "connection refused" in payload["checks"]["cache"]
