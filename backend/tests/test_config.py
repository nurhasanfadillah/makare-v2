import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from config import database_ssl_mode, migration_database_url, parse_cors_origins  # noqa: E402


@pytest.mark.parametrize("value", [None, "", "  "])
def test_cors_requires_explicit_origins(value):
    with pytest.raises(RuntimeError, match="explicit frontend origins"):
        parse_cors_origins(value)


@pytest.mark.parametrize("value", ["*", "https://*.example.com", "https://user:pass@example.com",
                                    "https://example.com/path", "https://example.com?x=1",
                                    "https://example.com?", "https://example.com#", "https://example.com///",
                                    "ftp://example.com", "https://example.com:bad"])
def test_cors_rejects_wildcards_and_non_origins(value):
    with pytest.raises(RuntimeError):
        parse_cors_origins(value)


def test_cors_parses_multiple_exact_origins_and_removes_duplicate_trailing_slashes():
    assert parse_cors_origins("http://localhost:3000/, https://app.example.com,https://app.example.com") == [
        "http://localhost:3000", "https://app.example.com"
    ]


def test_cors_rejects_empty_item_between_commas():
    with pytest.raises(RuntimeError, match="empty origin"):
        parse_cors_origins("https://app.example.com,")


@pytest.mark.parametrize("mode", [None, "require", "verify-ca", "verify-full"])
def test_database_ssl_defaults_to_tls_and_allows_secure_modes(mode):
    assert database_ssl_mode(mode, "production") == (mode or "require")


@pytest.mark.parametrize("app_env", [None, "production", "staging"])
def test_database_ssl_disable_is_rejected_outside_local_environments(app_env):
    with pytest.raises(RuntimeError, match="only for local/development/test"):
        database_ssl_mode("disable", app_env)


@pytest.mark.parametrize("app_env", ["local", "development", "test"])
def test_database_ssl_disable_is_allowed_for_isolated_local_environments(app_env):
    assert database_ssl_mode("disable", app_env) == "disable"


def test_database_ssl_rejects_unknown_modes():
    with pytest.raises(RuntimeError, match="DATABASE_SSL_MODE"):
        database_ssl_mode("allow", "development")


NEON_POOLED = "postgresql://app:secret@ep-blue-pooler.region.aws.neon.tech/neondb?sslmode=require"
NEON_DIRECT = "postgresql://migrator:secret@ep-blue.region.aws.neon.tech/neondb?sslmode=require"


def test_neon_runtime_url_is_reused_until_dedicated_migration_url_is_configured():
    assert migration_database_url(NEON_POOLED, None) == NEON_POOLED
    assert migration_database_url(NEON_POOLED, NEON_POOLED) == NEON_POOLED


def test_neon_migrations_use_direct_endpoint_for_same_branch_and_database():
    assert migration_database_url(NEON_POOLED, NEON_DIRECT) == NEON_DIRECT


@pytest.mark.parametrize("migration_url", [
    "postgresql://app:secret@ep-green.region.aws.neon.tech/neondb",
    "postgresql://app:secret@ep-blue.region.aws.neon.tech/otherdb",
    "postgresql://app:secret@ep-blue-pooler.region.aws.neon.tech/neondb",
])
def test_neon_migration_url_rejects_wrong_branch_database_or_pooler(migration_url):
    with pytest.raises(RuntimeError):
        migration_database_url(NEON_POOLED, migration_url)


def test_non_neon_runtime_can_reuse_database_url_for_migrations():
    local = "postgresql://app:secret@localhost:5432/makare"
    assert migration_database_url(local, None) == local
