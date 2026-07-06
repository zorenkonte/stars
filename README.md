# ⭐ Stars Archive

An **append-only** archive of [@zorenkonte](https://github.com/zorenkonte)'s
starred repositories, rendered to Markdown by a scheduled GitHub Action.

- **[`STARS.md`](STARS.md)** — the full archive, grouped by language, with an
  `Archived` section for repos that have left GitHub.
- **[`TODAY.md`](TODAY.md)** — a small daily rotation of repos to (re)review.
- **`stars.json`** — the machine-readable **source of truth**. Everything else
  is rendered *from* this file.

> These three files are generated on the first workflow run — don't hand-author
> them.

## Web reader

A static, browsable view of the archive is published to GitHub Pages:

**➡️ https://zorenkonte.github.io/stars/**

It's a single self-contained page (`docs/index.html` — vanilla HTML/CSS/JS, no
build step, no frameworks, no CDNs) that reads `stars.json` in your browser and
gives you live search (across name, description, topics, language), a language
filter with counts, an active/gone/all toggle, and sorting by stars, most
recently starred, most recently added, or name. Gone repos are shown muted with
a "gone since" badge. It follows your system light/dark preference.

The [`pages.yml`](.github/workflows/pages.yml) workflow deploys it on every push
to `main` that touches `stars.json` or `docs/**`, so the site refreshes right
after each daily archive commit. It bundles a copy of `stars.json` next to
`index.html` at deploy time (Pages can't serve a root-level `../stars.json`), and
the page fetches `./stars.json` from its own directory.

**One-time setup:** in **Settings → Pages → Source**, select **"GitHub
Actions"**. (Then run the *Deploy Pages* workflow once, or wait for the next push
to `main`.)

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
  "reviewed_at": null
}
```

## How it works

`scripts/archive_stars.py` (Python **standard library only** — no
`pip install`) runs this pipeline:

1. **Fetch** every page of the starred API (`per_page=100`, until an empty page)
   using the `application/vnd.github.star+json` media type so it also captures
   `starred_at`.
2. **Load** the existing `stars.json`.
3. **Merge** the live list into it (append-only, per the table above).
4. **Render** `STARS.md`.
5. **Render** `TODAY.md` (this stamps `reviewed_at` on the repos it surfaces).
6. **Save** `stars.json` — *after* step 5, so the daily rotation persists.

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
   `/users/{username}/starred`.

### Configuration reference

| Env var | Default | Meaning |
| --- | --- | --- |
| `STARS_USERNAME` | `zorenkonte` | User whose public stars are archived. |
| `GH_TOKEN` | *(none)* | Token for auth. `GITHUB_TOKEN` in CI; a PAT for private stars. Falls back to `STARS_TOKEN` if set. |
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
