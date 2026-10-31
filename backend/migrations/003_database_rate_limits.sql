CREATE TABLE IF NOT EXISTS api_rate_limits (
  bucket_hash TEXT PRIMARY KEY CHECK (length(bucket_hash) = 64),
  window_started_at TIMESTAMPTZ NOT NULL,
  hits INTEGER NOT NULL CHECK (hits > 0),
  expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS api_rate_limits_expiry ON api_rate_limits(expires_at);
