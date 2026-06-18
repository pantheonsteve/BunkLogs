import ssl

from config.settings.base import build_redis_cache_options


def test_redis_cache_options_plain_tcp():
    opts = build_redis_cache_options(ignore_exceptions=True)
    assert opts["CLIENT_CLASS"] == "django_redis.client.DefaultClient"
    assert opts["IGNORE_EXCEPTIONS"] is True
    assert "CONNECTION_POOL_KWARGS" not in opts


def test_redis_cache_options_tls(monkeypatch):
    monkeypatch.setattr(
        "config.settings.base.REDIS_SSL",
        True,
        raising=False,
    )
    opts = build_redis_cache_options()
    assert opts["CONNECTION_POOL_KWARGS"]["ssl_cert_reqs"] == ssl.CERT_NONE
