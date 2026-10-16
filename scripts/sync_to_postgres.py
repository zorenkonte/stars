#!/usr/bin/env python3
"""Mirror stars.json into Postgres.

The JSON file stays the append-only source of truth (archive_stars.py owns its
semantics and tests); this script makes the database an exact copy of it after
every archive run so the web reader can query it. Everything happens in one
transaction: upsert every repo and list, delete rows that are no longer in the
file (the file never drops entries, so in practice nothing is deleted), and
stamp sync_state.

Environment:
  DATABASE_URL  postgres://user:pass@host:5432/dbname   (required)
  STARS_JSON    path to the archive, default ./stars.json
  SCHEMA_SQL    path to db/schema.sql, applied idempotently if present
"""

import json
import os
import sys
from datetime import datetime, timezone

import psycopg

STARS_JSON = os.environ.get("STARS_JSON", "stars.json")
SCHEMA_SQL = os.environ.get(
    "SCHEMA_SQL", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "db", "schema.sql")
)


def _ts(value):
    """Return an ISO-8601 string or None; Postgres parses the string."""
    return value if isinstance(value, str) and value else None


def _strs(value):
    return [v for v in value if isinstance(v, str) and v] if isinstance(value, list) else []


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    repos = data.get("repos") if isinstance(data, dict) else None
    lists = data.get("lists") if isinstance(data, dict) else None
    return (repos if isinstance(repos, dict) else {}), (lists if isinstance(lists, dict) else {})


def sync(conn, repos, lists):
    with conn.cursor() as cur:
        if os.path.exists(SCHEMA_SQL):
            with open(SCHEMA_SQL, "r", encoding="utf-8") as fh:
                cur.execute(fh.read())

        cur.executemany(
            """
            INSERT INTO lists (slug, name, description)
            VALUES (%s, %s, %s)
            ON CONFLICT (slug) DO UPDATE
              SET name = EXCLUDED.name, description = EXCLUDED.description
            """,
            [
                (slug, (l or {}).get("name") or slug, (l or {}).get("description") or "")
                for slug, l in lists.items()
            ],
        )
        cur.execute("DELETE FROM lists WHERE NOT (slug = ANY(%s))", ([*lists.keys()],))

        rows = []
        for key, r in repos.items():
            r = r or {}
            rows.append(
                (
                    r.get("full_name") or key,
                    r.get("html_url") or "",
                    r.get("description") or "",
                    r.get("language") or None,
                    int(r.get("stars") or 0),
                    _strs(r.get("topics")),
                    _strs(r.get("lists")),
                    _ts(r.get("starred_at")),
                    _ts(r.get("first_seen")),
                    _ts(r.get("last_seen")),
                    _ts(r.get("gone_since")),
                    _ts(r.get("reviewed_at")),
                    "gone" if r.get("status") == "gone" else "active",
                )
            )
        cur.executemany(
            """
            INSERT INTO repos (full_name, html_url, description, language, stars, topics, lists,
                               starred_at, first_seen, last_seen, gone_since, reviewed_at, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (full_name) DO UPDATE SET
              html_url = EXCLUDED.html_url, description = EXCLUDED.description,
              language = EXCLUDED.language, stars = EXCLUDED.stars, topics = EXCLUDED.topics,
              lists = EXCLUDED.lists, starred_at = EXCLUDED.starred_at,
              first_seen = EXCLUDED.first_seen, last_seen = EXCLUDED.last_seen,
              gone_since = EXCLUDED.gone_since, reviewed_at = EXCLUDED.reviewed_at,
              status = EXCLUDED.status
            """,
            rows,
        )
        cur.execute("DELETE FROM repos WHERE NOT (full_name = ANY(%s))", ([row[0] for row in rows],))

        cur.execute(
            """
            INSERT INTO sync_state (id, synced_at, repo_count) VALUES (true, %s, %s)
            ON CONFLICT (id) DO UPDATE SET synced_at = EXCLUDED.synced_at, repo_count = EXCLUDED.repo_count
            """,
            (datetime.now(timezone.utc), len(rows)),
        )
    conn.commit()
    return len(rows), len(lists)


def main():
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2
    if not os.path.exists(STARS_JSON):
        print(f"{STARS_JSON} does not exist; nothing to sync", file=sys.stderr)
        return 1
    repos, lists = load(STARS_JSON)
    with psycopg.connect(url) as conn:
        n_repos, n_lists = sync(conn, repos, lists)
    print(f"Synced {n_repos} repos and {n_lists} lists to Postgres.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
