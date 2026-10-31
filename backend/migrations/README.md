# Database migrations

Schema changes are stored as ordered, immutable `NNN_description.sql` files. The backend applies pending files during startup in one PostgreSQL transaction while holding advisory transaction lock `424242`. A `schema_migrations` row records each filename, SHA-256 checksum, and application time. Startup stops if an already-applied file has changed.

`001_initial_schema.sql` is the current idempotent baseline. It uses `CREATE TABLE/INDEX IF NOT EXISTS` and safe additive DDL so it can initialize an empty database or bring a database created by the former startup DDL under migration tracking. It is intentionally forward-only; recovery requires restoring a verified backup or applying a reviewed forward fix. Never edit an applied migration: add the next numbered file. Migration execution must target an explicitly confirmed non-production database until an approved deployment process exists.

The migration ledger is created before the baseline. The ledger creation and each migration application are transactional; a failed migration rolls back its schema changes and ledger row. Bootstrap settings/admin seeding occurs after the migrations and remains separate from schema history.
