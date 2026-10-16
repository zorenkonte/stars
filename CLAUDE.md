# Stars Archive

Append-only archive of the owner's GitHub stars, self-hosted on a Raspberry Pi 5
with Docker Compose. Private by design: **never publish this to a public host**
(a Cloudflare Worker and GitHub Pages were tried and removed for that reason).

## Layout

- `stars.json` — the ledger. Repos keyed by `full_name`; entries are added or
  flagged `gone`, never deleted. In production the live copy is in the
  `archive` Docker volume (`/data/stars.json`); the one in git is a snapshot
  used only to seed a fresh volume.
- `scripts/archive_stars.py` — fetch + append-only merge + Markdown render.
  Stdlib only. Owns the ledger semantics; change with care.
- `scripts/test_archive_stars.py` — offline self-test. Run:
  `cd scripts && python3 test_archive_stars.py`. Must print `ALL SELF-TESTS PASSED`.
- `scripts/sync_to_postgres.py` — mirrors `stars.json` into Postgres (full
  upsert in one transaction). The DB is disposable; the JSON is the truth.
- `scripts/archiver_loop.py` — container entrypoint: seed, run once, then daily
  at `ARCHIVE_AT`.
- `db/schema.sql` — Postgres schema, idempotent.
- `web/` — Nuxt 4 reader (Nitro node-server). `server/api/{repos,meta,health}.get.ts`,
  `server/utils/archive.ts` (loads the mirror into memory, refreshes when
  `sync_state.synced_at` changes), `server/utils/query.ts` (search, filters,
  sort, group, facets — in-process over ~1.5k rows). UI in `app/`.
- `docker-compose.yml` — `db` (postgres:17), `archiver`, `web` (:3000).
  Config via `.env` (git-ignored), template in `.env.example`.

## Commands

```sh
docker compose up -d --build        # run the stack
docker compose logs -f archiver     # watch a run
docker compose down -v              # remove everything incl. volumes

cd web && pnpm install && pnpm typecheck && pnpm build   # Node 22.19+, pnpm 10
DATABASE_URL=postgres://stars:pw@localhost:5432/stars pnpm dev
```

## Rules

- Keep the ledger append-only. Don't rewrite `stars.json` by hand or from the DB.
- Don't add hosting, analytics, CDNs, or external fonts. LAN-only app.
- API shapes live in `web/shared/types.ts`; the UI depends on them.
- The archiver seeds from `./stars.json` only when the volume is empty.
