"""Environment configuration validation for backend startup."""
from urllib.parse import urlsplit


def parse_cors_origins(value: str | None) -> list[str]:
    if not value or not value.strip():
        raise RuntimeError("CORS_ORIGINS must list one or more explicit frontend origins")

    entries = [entry.strip() for entry in value.split(",")]
    if any(not entry for entry in entries):
        raise RuntimeError("CORS_ORIGINS contains an empty origin")

    origins = []
    for entry in entries:
        origin = entry[:-1] if entry.endswith("/") and not entry.endswith("//") else entry
        try:
            parsed = urlsplit(origin)
            hostname = parsed.hostname
            # Accessing port validates malformed port numbers.
            parsed.port
        except ValueError as exc:
            raise RuntimeError(f"Invalid CORS origin: {entry}") from exc
        if (
            origin == "*"
            or parsed.scheme not in ("http", "https")
            or not parsed.netloc
            or not hostname
            or "*" in hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path
            or parsed.query
            or parsed.fragment
            or "?" in entry
            or "#" in entry
        ):
            raise RuntimeError(f"CORS origin must be an exact HTTP(S) origin: {entry}")
        if origin not in origins:
            origins.append(origin)
    return origins


def database_ssl_mode(value: str | None, app_env: str | None) -> str:
    """Resolve asyncpg SSL policy; plaintext DB transport is local/test only."""
    mode = (value or "require").strip().lower()
    if mode not in {"require", "verify-ca", "verify-full", "disable"}:
        raise RuntimeError("DATABASE_SSL_MODE must be require, verify-ca, verify-full, or disable")
    if mode == "disable" and (app_env or "").strip().lower() not in {"local", "development", "test"}:
        raise RuntimeError("DATABASE_SSL_MODE=disable is allowed only for local/development/test environments")
    return mode


def migration_database_url(runtime_url: str, migration_url: str | None) -> str:
    """Use the configured migration endpoint, or the owner-selected runtime URL."""
    runtime = urlsplit(runtime_url)
    runtime_host = runtime.hostname or ""
    if migration_url and migration_url.strip():
        direct = urlsplit(migration_url.strip())
        direct_host = direct.hostname or ""
        # The current owner-directed setup intentionally reuses the existing
        # Neon URL until a dedicated migration endpoint is supplied later.
        if migration_url.strip() == runtime_url:
            return runtime_url
        if "-pooler." in direct_host:
            raise RuntimeError("DATABASE_MIGRATION_URL must use a direct (non-pooled) endpoint")
        if "-pooler." in runtime_host and (
            direct_host != runtime_host.replace("-pooler.", ".") or direct.path != runtime.path
        ):
            raise RuntimeError("DATABASE_MIGRATION_URL must target the same Neon branch and database")
        return migration_url.strip()
    # Interim configuration reuses DATABASE_URL for Neon migrations as requested.
    # Neon recommends direct endpoints for migrations; set DATABASE_MIGRATION_URL
    # to a matching direct endpoint once one is available and validated.
    return runtime_url
