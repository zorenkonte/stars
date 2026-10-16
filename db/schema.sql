-- Stars Archive — Postgres mirror of the append-only ledger.
-- Applied automatically by the postgres container on first start
-- (docker-entrypoint-initdb.d) and re-applied idempotently by
-- scripts/sync_to_postgres.py on every sync.

CREATE TABLE IF NOT EXISTS lists (
  slug        text PRIMARY KEY,
  name        text NOT NULL,
  description text NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS repos (
  full_name   text PRIMARY KEY,
  html_url    text NOT NULL DEFAULT '',
  description text NOT NULL DEFAULT '',
  language    text,
  stars       integer NOT NULL DEFAULT 0,
  topics      text[] NOT NULL DEFAULT '{}',
  lists       text[] NOT NULL DEFAULT '{}',
  starred_at  timestamptz,
  first_seen  timestamptz,
  last_seen   timestamptz,
  gone_since  timestamptz,
  reviewed_at timestamptz,
  status      text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'gone'))
);

CREATE INDEX IF NOT EXISTS repos_status_idx   ON repos (status);
CREATE INDEX IF NOT EXISTS repos_language_idx ON repos (language);

-- Single-row bookkeeping: when the mirror was last refreshed.
CREATE TABLE IF NOT EXISTS sync_state (
  id         boolean PRIMARY KEY DEFAULT true CHECK (id),
  synced_at  timestamptz NOT NULL,
  repo_count integer NOT NULL
);
