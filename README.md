# ⭐ Stars Archive

An **append-only** archive of [@zorenkonte](https://github.com/zorenkonte)'s
starred repositories, rendered to Markdown by a scheduled GitHub Action.

- **[`STARS.md`](STARS.md)** — the full archive, grouped by language, with an
  `Archived` section for repos that have left GitHub.
- **[`TODAY.md`](TODAY.md)** — a small daily rotation of repos to (re)review.
- **`stars.json`** — the machine-readable **source of truth**. Everything else
  is rendered *from* this file. It also carries your GitHub **star lists**
  (the curated groups at `github.com/stars/<user>/lists`) and which lists each
  repo belongs to.

> These three files are generated on the first workflow run — don't hand-author
> them.

## Web reader

A browsable view of the archive, deployed to Cloudflare Workers:

**➡️ https://stars-archive.muffintoppings36.workers.dev**

It lives in [`web/`](web/) as a Nuxt 4 app. The archive is bundled into the
Worker at build time and the heavy lifting runs on the server:

- **Server-side search and filtering** — `GET /api/repos` runs the search
  (name, description, topics, language, list names), the language / star-list /
  status filters, all four sort modes (most recently starred, stars, most
  recently added, name) and the language/status grouping on the Worker, and
  returns one page (60 repos) plus the total, the group spans and faceted counts
  for the sidebar. `GET /api/meta` returns the archive totals.
- **Virtual scrolling** — the grid renders only the shelves on screen
  (`@tanstack/vue-virtual`) and fetches pages on demand as you scroll, so the
  full archive never lands in the DOM at once.
- **Shopping-style UI** — filters in a sticky left sidebar (a drawer on
  phones), product tiles with language stickers and star "price tags", gone
  repos greyed with a "gone since" stamp, sort and group in the toolbar, filter
  state in the URL. Follows your system light/dark preference.

**Deploys** through Cloudflare **Workers Builds**, which is connected to this
repository: every push to `main` — including the daily archive commit —
rebuilds and redeploys the Worker. No tokens live in GitHub. Build settings
(Cloudflare dashboard → Workers & Pages → `stars-archive` → Settings → Build):
root directory `web`, build command `pnpm build`, deploy command
`npx wrangler deploy`, branch `main`. Node is pinned by `web/.nvmrc` and pnpm by
`packageManager` in `web/package.json`.

Locally (Node 22.19+):

```sh
cd web
pnpm install
pnpm dev        # Nuxt dev server with Cloudflare bindings emulated
pnpm build      # nuxt build (cloudflare_module preset)
pnpm preview    # wrangler dev against the built Worker
pnpm deploy     # build + wrangler deploy by hand
```

## Why append-only?

GitHub's "starred" API only ever returns repositories that **currently exist
and are still starred**. The moment a repo is deleted, made private, renamed, or
unstarred, it disappears from that API *forever*. A naive "fetch the stars and
overwrite a file" tool would therefore silently lose history every time a repo
went away.

This project instead treats `stars.json` as a durable ledger:

| Situation | What happens |
| --- | --- |
| A newly starred repo | Added with `first_seen`, `status: "active"`. |
| A repo still in the live list | Mutable fields (`description`, `language`, `stars`, `topics`, `html_url`) are refreshed; `last_seen` updated. `first_seen`, `starred_at`, and `reviewed_at` are **preserved**. |
| A repo that vanished from the live list | Flagged `status: "gone"` with a `gone_since` date. **Its entry — and last-known metadata — is never deleted.** |
| A "gone" repo that reappears | Re-activated (`status: "active"`, `gone_since: null`). |
| Star lists fetched OK | Every active repo's `lists` is replaced with its live membership; gone repos keep their last-known `lists`. The top-level `lists` catalog is refreshed (a deleted list is kept only while a gone repo still references it). |
| Star lists could **not** be fetched | Nothing list-related changes. A failed fetch is "unknown", never "no lists". |

The Markdown is always rendered from this JSON, so nothing that was ever
captured can be lost by a later API response.

### Entry shape

Each entry in `stars.json` (keyed by `full_name`) looks like:

```json
{
  "full_name": "owner/repo",
  "html_url": "https://github.com/owner/repo",
  "description": "…",
  "language": "Python",
  "stars": 1234,
  "topics": ["cli", "productivity"],
  "starred_at": "2025-03-01T00:00:00Z",
  "first_seen": "2026-07-06T06:17:00Z",
  "last_seen":  "2026-07-06T06:17:00Z",
  "status": "active",
  "gone_since": null,
  "reviewed_at": null,
  "lists": ["selfhost", "shell"]
}
```

`lists` holds the **slugs** of the star lists the repo is in (sorted). The
top-level `lists` object maps each slug to its display name and description:

```json
"lists": {
  "selfhost": { "slug": "selfhost", "name": "Selfhost", "description": null },
  "shell":    { "slug": "shell",    "name": "Shell",    "description": "CLI tools" }
}
```

## How it works

`scripts/archive_stars.py` (Python **standard library only** — no
`pip install`) runs this pipeline:

1. **Fetch** every page of the starred API (`per_page=100`, until an empty page)
   using the `application/vnd.github.star+json` media type so it also captures
   `starred_at`.
2. **Fetch star lists** via the GraphQL API (`viewer.lists` → `items`, paged
   100 at a time). Lists have no REST endpoint and GitHub only shows them to
   their **owner**: the built-in `GITHUB_TOKEN` gets `totalCount: 0`, so this
   step uses the `STARS_TOKEN` personal access token (see
   [Archiving star lists](#archiving-star-lists)). It is **non-fatal**: without
   a PAT, or on any GraphQL error, it logs a message and the previous list data
   is kept.
3. **Load** the existing `stars.json`.
4. **Merge** the live list into it (append-only, per the table above), then
   refresh list membership for active repos.
5. **Render** `STARS.md`.
6. **Render** `TODAY.md` (this stamps `reviewed_at` on the repos it surfaces).
7. **Save** `stars.json` — *after* step 6, so the daily rotation persists.

`TODAY.md` picks `DAILY_COUNT` (default **10**) active repos: unreviewed ones
first (oldest `first_seen` first), then — if there aren't enough — the
least-recently-reviewed ones. Every picked repo gets `reviewed_at = now`, so the
selection rotates through your whole list over time.

## Setup

Nothing to configure for **public** stars — the workflow uses the built-in
`GITHUB_TOKEN`.

1. Merge this repo's `.github/workflows/archive-stars.yml`.
2. Ensure **Settings → Actions → General → Workflow permissions** allows
   *Read and write permissions* (the workflow also requests
   `permissions: contents: write` explicitly).
3. Wait for the daily schedule, or trigger it manually from the **Actions** tab
   (**Run workflow** → `workflow_dispatch`).

The workflow commits the regenerated files back to the repo only when something
actually changed (`git diff --cached --quiet` guard).

### Archiving star lists

Star lists are only visible to the account that owns them, so the workflow
needs a token that *is* you:

1. Create a **classic** personal access token with the `read:user` scope
   (add `repo` too if you also want private stars, below).
2. Save it as the repository secret **`STARS_TOKEN`**.
3. Run *Archive Stars* (Actions → Run workflow). The log line
   `Archive updated: … N lists` confirms it; the web reader's **List** filter
   and badges appear on the next deploy.

Without the secret the run logs `Star lists: 0 visible to this token …` and
keeps whatever list data was archived before.

### Archiving private starred repos

The public starred endpoint can't see stars on private repos. To include them:

1. Create a personal access token with the `repo` scope (classic) — or a
   fine-grained token that can read the repos you've starred.
2. Save it as a repository secret named **`STARS_TOKEN`**.
3. In `archive-stars.yml`, switch the step's env to use it:

   ```yaml
   env:
     STARS_USERNAME: zorenkonte
     GH_TOKEN: ${{ secrets.STARS_TOKEN }}
     USE_AUTH_USER: "true"
   ```

   `USE_AUTH_USER=true` makes the script query `/user/starred` (the
   authenticated user's stars, private included) instead of the public
   `/users/{username}/starred`. (Star lists already use `STARS_TOKEN` on their
   own; you don't need this switch for them.)

### Configuration reference

| Env var | Default | Meaning |
| --- | --- | --- |
| `STARS_USERNAME` | `zorenkonte` | User whose public stars are archived. |
| `GH_TOKEN` | *(none)* | Token for auth. `GITHUB_TOKEN` in CI; a PAT for private stars. Falls back to `STARS_TOKEN` if set. |
| `STARS_TOKEN` | *(none)* | Owner's PAT (`read:user`) used to fetch **star lists** as `viewer`. Unset → lists are skipped and previous list data kept. |
| `USE_AUTH_USER` | `false` | If `true`, query `/user/starred` (needs a PAT). |
| `DAILY_COUNT` | `10` | How many repos `TODAY.md` surfaces per run. |
| `STARS_JSON` / `STARS_MD` / `TODAY_MD` | `stars.json` / `STARS.md` / `TODAY.md` | Output paths. |

## Running / testing locally

```bash
# Generate the files against a live account (public stars):
STARS_USERNAME=zorenkonte python scripts/archive_stars.py

# Offline self-test — no network, proves the append-only guarantees:
python scripts/test_archive_stars.py
```

## Honest limitations

- **"Gone" is ambiguous.** The starred API can't tell you *why* a repo left the
  list. Deleted, made private, renamed, **or simply unstarred by you** all look
  identical, so they all land in the `Archived` section. This is a fundamental
  limit of the API, not a bug.
- **Renames create a duplicate.** GitHub reports a renamed repo under its new
  `full_name`. Since entries are keyed by `full_name`, the old name is flagged
  `gone` and the new name is added as if brand new. There's no reliable,
  token-free way to follow a rename.
- **`stars.json` is the only source of truth.** If you delete or rewrite it, the
  history of gone repos is lost — there is no way to recover it from GitHub. Keep
  it in version control (that's the whole point) and don't rebuild it from the
  live API.
- **First-seen ≠ first-starred (for pre-existing repos).** `starred_at` comes
  straight from GitHub and is accurate. `first_seen` is when *this archive* first
  observed the repo, so for stars you made before adopting this tool it will be
  the archive's first run, not the actual star date.
- **Metadata is a snapshot.** For active repos, `description`/`language`/`stars`
  reflect the last successful fetch. For gone repos they're frozen at their
  last-known values.
- **Scheduled runs only fire on the default branch.** The cron trigger won't run
  from a feature branch or a fork's PR.
- **Public rate limits are low.** Unauthenticated requests are capped at 60/hour;
  the workflow always sends a token (5,000/hour), so this only matters for
  ad-hoc local runs without `GH_TOKEN`.
- **Star lists need the owner's PAT.** GitHub exposes star lists only to their
  owner (verified: the Actions token sees `totalCount: 0`, and the lists page
  is a 404 when anonymous), so without `STARS_TOKEN` lists are skipped and
  whatever was archived before is kept. List badges appear on the web reader
  after the first archive run that fetches lists successfully.
