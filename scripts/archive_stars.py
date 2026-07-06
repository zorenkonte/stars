#!/usr/bin/env python3
"""Append-only archive of GitHub starred repositories.

This is intentionally NOT a stateless "fetch and overwrite" tool. GitHub's
starred API only ever returns repositories that currently exist and are still
starred. The moment a repo is deleted, taken private, renamed, or unstarred it
vanishes from that API forever. So the source of truth here is a persistent
JSON file (``stars.json``) that is only ever ADDED to and FLAGGED -- never
rebuilt from the live API. The human-readable Markdown (``STARS.md`` and
``TODAY.md``) is rendered FROM that JSON, not from GitHub directly.

Python standard library only (urllib, json, os, datetime, time) so the workflow
needs no ``pip install`` step.
"""

import datetime
import json
import os
import time
import urllib.error
import urllib.request

API_ROOT = "https://api.github.com"
USER_AGENT = "zorenkonte-stars-archiver"

# File locations (relative to the working directory / repo root).
STARS_JSON = os.environ.get("STARS_JSON", "stars.json")
STARS_MD = os.environ.get("STARS_MD", "STARS.md")
TODAY_MD = os.environ.get("TODAY_MD", "TODAY.md")


# --------------------------------------------------------------------------- #
# Time helpers -- everything is UTC ISO-8601.
# --------------------------------------------------------------------------- #
def now_iso(dt=None):
    """Return a UTC ISO-8601 timestamp like ``2026-07-06T16:21:00Z``."""
    if dt is None:
        dt = datetime.datetime.now(datetime.timezone.utc)
    return dt.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _date_part(iso_ts):
    """Return the ``YYYY-MM-DD`` portion of an ISO timestamp (or "")."""
    return (iso_ts or "")[:10]


# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
def config_from_env():
    """Build the run configuration from environment variables."""
    return {
        "username": os.environ.get("STARS_USERNAME", "zorenkonte"),
        # GH_TOKEN is the built-in GITHUB_TOKEN in CI; STARS_TOKEN is the
        # documented fallback for a personal access token (private stars).
        "token": os.environ.get("GH_TOKEN") or os.environ.get("STARS_TOKEN") or "",
        "use_auth_user": os.environ.get("USE_AUTH_USER", "").strip().lower() == "true",
        "daily_count": int(os.environ.get("DAILY_COUNT", "10")),
    }


# --------------------------------------------------------------------------- #
# Fetch
# --------------------------------------------------------------------------- #
def _http_get_json(url, token):
    """GET a URL and return decoded JSON. Fails loudly on any non-2xx."""
    req = urllib.request.Request(url, method="GET")
    # The star+json media type makes each item {"starred_at":..,"repo":{..}}.
    req.add_header("Accept", "application/vnd.github.star+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", USER_AGENT)
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.getcode()
            body = resp.read()
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")
        except Exception:  # pragma: no cover - best-effort error detail
            pass
        raise SystemExit(
            f"GitHub API returned HTTP {exc.code} for {url}\n{detail}"
        )
    except urllib.error.URLError as exc:
        raise SystemExit(f"Network error fetching {url}: {exc.reason}")

    if not (200 <= status < 300):
        raise SystemExit(f"GitHub API returned HTTP {status} for {url}")

    return json.loads(body.decode("utf-8"))


def _normalize(repo, starred_at):
    """Pull the fields we care about out of a GitHub repo object."""
    return {
        "full_name": repo["full_name"],
        "html_url": repo["html_url"],
        "description": repo.get("description"),
        "language": repo.get("language"),
        "stars": repo.get("stargazers_count", 0),
        "topics": list(repo.get("topics") or []),
        "starred_at": starred_at,
    }


def fetch_stars(config):
    """Fetch every starred repo for the configured user.

    Paginates ``per_page=100`` until an empty page is returned. Returns a list
    of normalized repo dicts. Monkeypatched in the self-test so no network is
    touched there.
    """
    if config["use_auth_user"]:
        # /user/starred uses the authenticated identity and includes stars on
        # private repos (requires a PAT with `repo` scope in GH_TOKEN).
        path = "/user/starred"
    else:
        path = f"/users/{config['username']}/starred"

    results = []
    page = 1
    while True:
        url = f"{API_ROOT}{path}?per_page=100&page={page}"
        items = _http_get_json(url, config["token"])
        if not items:
            break
        for item in items:
            # With the star+json Accept header each item wraps the repo.
            repo = item["repo"]
            starred_at = item.get("starred_at")
            results.append(_normalize(repo, starred_at))
        page += 1
        time.sleep(0.2)  # be polite between pages
    return results


# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #
def load_archive(path=STARS_JSON):
    """Load the persistent archive, or return an empty one."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict) or "repos" not in data:
            data = {"repos": {}}
        if not isinstance(data.get("repos"), dict):
            data["repos"] = {}
        return data
    return {"repos": {}}


def save_archive(archive, path=STARS_JSON):
    """Write the archive with sorted keys for stable, reviewable diffs."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(archive, fh, indent=2, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


# --------------------------------------------------------------------------- #
# Merge (append-only)
# --------------------------------------------------------------------------- #
def merge_stars(archive, live, now):
    """Merge the live star list into the archive. Never deletes an entry.

    * New repo         -> add with first_seen/last_seen=now, status="active".
    * Existing repo    -> refresh mutable fields + last_seen; reactivate;
                          PRESERVE first_seen, starred_at, reviewed_at.
    * Missing + active -> flag status="gone" with gone_since=now.
    """
    repos = archive["repos"]
    live_names = set()

    for entry in live:
        name = entry["full_name"]
        live_names.add(name)
        existing = repos.get(name)
        if existing is not None:
            # Refresh the fields that can legitimately change over time.
            existing["description"] = entry["description"]
            existing["language"] = entry["language"]
            existing["stars"] = entry["stars"]
            existing["topics"] = entry["topics"]
            existing["html_url"] = entry["html_url"]
            existing["last_seen"] = now
            existing["status"] = "active"
            existing["gone_since"] = None
            # PRESERVE: first_seen, starred_at, reviewed_at.
        else:
            repos[name] = {
                "full_name": name,
                "html_url": entry["html_url"],
                "description": entry["description"],
                "language": entry["language"],
                "stars": entry["stars"],
                "topics": entry["topics"],
                "starred_at": entry["starred_at"],
                "first_seen": now,
                "last_seen": now,
                "status": "active",
                "gone_since": None,
                "reviewed_at": None,
            }

    # Anything currently active but absent from the live list has vanished.
    for name, existing in repos.items():
        if name not in live_names and existing.get("status") == "active":
            existing["status"] = "gone"
            existing["gone_since"] = now

    return archive


# --------------------------------------------------------------------------- #
# Rendering
# --------------------------------------------------------------------------- #
def _clean(text):
    """Collapse a description onto a single, trimmed line."""
    if not text:
        return ""
    return " ".join(text.split())


def _anchor(text):
    """GitHub-style heading anchor (lowercase, spaces->dashes, drop punct)."""
    out = []
    for ch in text.lower():
        if ch.isalnum() or ch in "-_":
            out.append(ch)
        elif ch == " ":
            out.append("-")
        # everything else is dropped
    return "".join(out)


def render_stars_md(archive, now):
    """Render the full archive to Markdown."""
    repos = list(archive["repos"].values())
    active = [r for r in repos if r.get("status") == "active"]
    gone = [r for r in repos if r.get("status") == "gone"]

    # Group active repos by language (null -> "Other").
    by_lang = {}
    for r in active:
        lang = r.get("language") or "Other"
        by_lang.setdefault(lang, []).append(r)

    # Languages ordered by descending count, then name.
    lang_order = sorted(by_lang, key=lambda l: (-len(by_lang[l]), l))

    lines = []
    lines.append("# ⭐ Starred Repositories Archive")
    lines.append("")
    lines.append(
        f"_Last updated {_date_part(now)} — "
        f"{len(active)} active · {len(gone)} archived._"
    )
    lines.append("")
    lines.append(
        "> Append-only archive. Repositories that leave GitHub (deleted, "
        "made private, renamed, or unstarred) are kept below under "
        "**Archived**, never removed."
    )
    lines.append("")

    # Languages table of contents with counts.
    lines.append("## Languages")
    lines.append("")
    for lang in lang_order:
        lines.append(f"- [{lang}](#{_anchor(lang)}) ({len(by_lang[lang])})")
    if not lang_order:
        lines.append("_No active repositories yet._")
    lines.append("")

    # One section per language.
    for lang in lang_order:
        lines.append(f"## {lang}")
        lines.append("")
        section = sorted(by_lang[lang], key=lambda r: (-r.get("stars", 0), r["full_name"]))
        for r in section:
            lines.append(
                f"- **[{r['full_name']}]({r['html_url']})** — {_clean(r.get('description'))}"
            )
        lines.append("")

    # Archived section.
    lines.append("## Archived (no longer on GitHub)")
    lines.append("")
    if gone:
        for r in sorted(gone, key=lambda r: r["full_name"]):
            lines.append(
                f"- **{r['full_name']}** — {_clean(r.get('description'))} "
                f"_(gone since {_date_part(r.get('gone_since'))}, "
                f"last known {r.get('stars', 0)}★)_"
            )
    else:
        lines.append("_None yet._")
    lines.append("")

    return "\n".join(lines) + "\n"


def render_today_md(archive, now, daily_count):
    """Pick a daily rotation of repos to review and render it.

    Mutates ``reviewed_at`` on the picked repos, so the archive MUST be saved
    after this runs or the rotation will not persist.
    """
    active = [r for r in archive["repos"].values() if r.get("status") == "active"]

    unreviewed = sorted(
        (r for r in active if r.get("reviewed_at") is None),
        key=lambda r: (r.get("first_seen") or "", r["full_name"]),
    )
    picks = unreviewed[:daily_count]

    if len(picks) < daily_count:
        reviewed = sorted(
            (r for r in active if r.get("reviewed_at") is not None),
            key=lambda r: (r.get("reviewed_at") or "", r["full_name"]),
        )
        picks += reviewed[: daily_count - len(picks)]

    # Stamp every picked repo as reviewed now (drives the rotation).
    for r in picks:
        r["reviewed_at"] = now

    lines = []
    lines.append("# 📅 Today's Repos to Review")
    lines.append("")
    lines.append(f"_{_date_part(now)} — {len(picks)} repositories_")
    lines.append("")
    if picks:
        for r in picks:
            lines.append(
                f"- **[{r['full_name']}]({r['html_url']})** — {_clean(r.get('description'))}"
            )
    else:
        lines.append("_No active repositories to review yet._")
    lines.append("")

    return "\n".join(lines) + "\n"


def _write(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def run(config, now=None, paths=None):
    """Full pipeline: fetch -> load -> merge -> render -> render -> save.

    NOTE the ordering: STARS.md is rendered before TODAY.md, and stars.json is
    saved LAST because rendering TODAY.md mutates reviewed_at.
    """
    now = now or now_iso()
    paths = paths or {}
    stars_json = paths.get("stars_json", STARS_JSON)
    stars_md = paths.get("stars_md", STARS_MD)
    today_md = paths.get("today_md", TODAY_MD)

    live = fetch_stars(config)          # 1. fetch (fails loudly on error)
    archive = load_archive(stars_json)  # 2. load persistent state
    merge_stars(archive, live, now)     # 3. append-only merge

    _write(stars_md, render_stars_md(archive, now))                 # 4. STARS.md
    _write(today_md, render_today_md(archive, now, config["daily_count"]))  # 5. TODAY.md

    save_archive(archive, stars_json)   # 6. save AFTER TODAY.md (rotation!)

    active = sum(1 for r in archive["repos"].values() if r.get("status") == "active")
    gone = sum(1 for r in archive["repos"].values() if r.get("status") == "gone")
    print(f"Archive updated: {active} active, {gone} archived (fetched {len(live)} live).")
    return archive


def main():
    run(config_from_env())


if __name__ == "__main__":
    main()
