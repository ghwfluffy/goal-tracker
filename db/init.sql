-- Bootstrap-only setup. App schema is managed by SQL migrations in
-- api/alembic and applied by the Python layer. The PostgreSQL image
-- creates the configured user and database from environment variables,
-- so this file only handles bootstrap-safe database extensions.
CREATE EXTENSION IF NOT EXISTS pgcrypto;
