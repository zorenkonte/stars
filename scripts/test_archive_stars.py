#!/usr/bin/env python3
"""Offline self-test for the star archiver (no network, standard library only).

Proves the two properties the archive exists to guarantee:

1. A repo that drops out of the live starred list is NOT deleted -- it stays in
   stars.json flagged status="gone" with a gone_since date and its description
   intact.
2. A repo picked into TODAY.md has its reviewed_at persisted to stars.json
   (because the pipeline saves AFTER rendering TODAY.md).
3. Star-list membership is refreshed for active repos, frozen for gone repos,
   and left untouched when the lists fetch is unavailable. The GraphQL list
   fetcher is exercised against canned, paginated responses (no network).

Run with:  python scripts/test_archive_stars.py
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive_stars  # noqa: E402

# main() monkeypatches archive_stars.fetch_lists; keep the real one for its own test.
REAL_FETCH_LISTS = archive_stars.fetch_lists


def _repo(full_name, description, language="Python", stars=1, starred_at="2026-01-01T00:00:00Z"):
    """Build a normalized live-repo dict, as fetch_stars would return."""
    return {
        "full_name": full_name,
        "html_url": f"https://github.com/{full_name}",
        "description": description,
        "language": language,
        "stars": stars,
        "topics": ["demo"],
        "starred_at": starred_at,
    }


def _load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _today_picks(today_md_path):
    """Return the full_names TODAY.md actually rendered, in order."""
    picks = []
    with open(today_md_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("- **[") and "](" in line:
                picks.append(line[len("- **["):line.index("](")])
    return picks


def main():
    tmp = tempfile.mkdtemp(prefix="stars-selftest-")
    paths = {
        "stars_json": os.path.join(tmp, "stars.json"),
        "stars_md": os.path.join(tmp, "STARS.md"),
        "today_md": os.path.join(tmp, "TODAY.md"),
    }
    config = {"username": "zorenkonte", "token": "", "use_auth_user": False, "daily_count": 10}
    RUN1 = "2026-07-01T06:17:00Z"
    RUN2 = "2026-07-02T06:17:00Z"

    # --- Run 1: three repos are starred -------------------------------------
    run1_live = [
        _repo("octocat/alpha", "Alpha description"),
        _repo("octocat/beta", "Beta description — keep me forever"),
        _repo("octocat/gamma", "Gamma description"),
    ]
    run1_lists = {
        "shell": {"slug": "shell", "name": "Shell", "description": "CLI tools",
                  "repos": ["octocat/alpha", "octocat/beta"]},
        "selfhost": {"slug": "selfhost", "name": "Selfhost", "description": None,
                     "repos": ["octocat/beta"]},
    }
    archive_stars.fetch_stars = lambda cfg: run1_live  # monkeypatch: no network
    archive_stars.fetch_lists = lambda cfg: run1_lists
    archive_stars.run(config, now=RUN1, paths=paths)

    state1 = _load(paths["stars_json"])
    repos1 = state1["repos"]
    assert set(repos1) == {"octocat/alpha", "octocat/beta", "octocat/gamma"}, repos1.keys()
    assert all(repos1[n]["status"] == "active" for n in repos1), "all should be active after run 1"

    # Property 3: list membership + catalog persisted.
    assert repos1["octocat/alpha"]["lists"] == ["shell"], repos1["octocat/alpha"]["lists"]
    assert repos1["octocat/beta"]["lists"] == ["selfhost", "shell"], "sorted slugs expected"
    assert repos1["octocat/gamma"]["lists"] == [], "repo in no list gets an empty list, not a missing key"
    assert set(state1["lists"]) == {"shell", "selfhost"}
    assert state1["lists"]["shell"] == {"slug": "shell", "name": "Shell", "description": "CLI tools"}
    print("[ok] run 1: star lists persisted (catalog + per-repo membership)")

    # Property 2: EVERY repo actually rendered into TODAY.md must have its
    # reviewed_at persisted to stars.json (proves the save happens AFTER the
    # daily render, and that stamping covers the whole picked set -- not just
    # a subset). We assert the spec direction directly: {TODAY.md picks} must
    # all appear on disk with reviewed_at == this run's timestamp.
    picks1 = _today_picks(paths["today_md"])
    assert picks1, "run 1 should have rendered repos into TODAY.md"
    for name in picks1:
        assert name in repos1, f"{name} is in TODAY.md but missing from stars.json"
        assert repos1[name]["reviewed_at"] == RUN1, (
            f"{name} was rendered into TODAY.md but its reviewed_at was not "
            f"persisted (got {repos1[name]['reviewed_at']!r})"
        )
    # Exact correspondence: nothing was stamped that wasn't picked, and nothing
    # picked was left unstamped.
    persisted = {n for n, r in repos1.items() if r["reviewed_at"] == RUN1}
    assert set(picks1) == persisted, (sorted(picks1), sorted(persisted))
    print(f"[ok] run 1: {len(repos1)} repos archived; all {len(picks1)} "
          "TODAY.md picks have reviewed_at persisted to disk")

    # --- Run 2: beta disappears from the live list --------------------------
    run2_live = [
        _repo("octocat/alpha", "Alpha description (updated)", stars=42),
        _repo("octocat/gamma", "Gamma description"),
    ]
    run2_lists = {
        # Renamed, alpha dropped out; "selfhost" was deleted on GitHub.
        "shell": {"slug": "shell", "name": "Shell & CLI", "description": None,
                  "repos": ["octocat/gamma"]},
    }
    archive_stars.fetch_stars = lambda cfg: run2_live
    archive_stars.fetch_lists = lambda cfg: run2_lists
    archive_stars.run(config, now=RUN2, paths=paths)

    state2 = _load(paths["stars_json"])
    repos2 = state2["repos"]

    # Lists: active repos refreshed, the gone repo frozen, catalog follows.
    assert repos2["octocat/alpha"]["lists"] == [], "alpha left every list"
    assert repos2["octocat/gamma"]["lists"] == ["shell"], "gamma joined shell"
    assert repos2["octocat/beta"]["lists"] == ["selfhost", "shell"], "gone repo keeps last-known lists"
    assert state2["lists"]["shell"]["name"] == "Shell & CLI", "catalog refreshes list names"
    assert "selfhost" in state2["lists"], "deleted list kept while a gone repo still references it"
    print("[ok] run 2: list membership refreshed for active repos, frozen for octocat/beta")

    # Property 1: beta is STILL here, flagged gone, with metadata intact.
    assert "octocat/beta" in repos2, "gone repo must never be deleted"
    beta = repos2["octocat/beta"]
    assert beta["status"] == "gone", f"expected gone, got {beta['status']}"
    assert beta["gone_since"] == RUN2, beta["gone_since"]
    assert beta["description"] == "Beta description — keep me forever", beta["description"]
    assert beta["first_seen"] == RUN1, "first_seen must be preserved"
    assert beta["starred_at"] == "2026-01-01T00:00:00Z", "starred_at must be preserved"

    # Still-live repos stay active; mutable fields refresh; first_seen preserved.
    alpha = repos2["octocat/alpha"]
    assert alpha["status"] == "active" and alpha["gone_since"] is None
    assert alpha["stars"] == 42, "stars should refresh for active repos"
    assert alpha["first_seen"] == RUN1, "first_seen must be preserved on refresh"

    # The archived section of STARS.md shows beta with its frozen description.
    with open(paths["stars_md"], "r", encoding="utf-8") as fh:
        stars_md = fh.read()
    assert "Archived (no longer on GitHub)" in stars_md
    assert "octocat/beta" in stars_md.split("Archived (no longer on GitHub)")[1]

    print("[ok] run 2: octocat/beta preserved as gone with description + dates intact")
    print("[ok] run 2: octocat/alpha stayed active, stars refreshed 1 -> 42, first_seen preserved")

    # --- Run 3: the lists fetch fails (no token / GraphQL error) --------------
    RUN3 = "2026-07-03T06:17:00Z"
    archive_stars.fetch_stars = lambda cfg: run2_live
    archive_stars.fetch_lists = lambda cfg: None
    archive_stars.run(config, now=RUN3, paths=paths)
    state3 = _load(paths["stars_json"])
    assert state3["lists"] == state2["lists"], "a failed lists fetch must not wipe the catalog"
    assert {n: r["lists"] for n, r in state3["repos"].items()} == \
        {n: r["lists"] for n, r in state2["repos"].items()}, "membership must survive a failed fetch"
    print("[ok] run 3: unavailable lists fetch leaves list data untouched")

    # --- GraphQL fetcher against canned, paginated responses ------------------
    _test_fetch_lists_pagination()

    print("\nALL SELF-TESTS PASSED")


def _test_fetch_lists_pagination():
    """Drive fetch_lists through two list pages and a >100-item list."""
    calls = []

    def fake_graphql(query, variables, token):
        calls.append((query.strip().splitlines()[0], dict(variables)))
        if "node(id: $id)" in query:
            # Second (and last) page of items for the big list.
            assert variables == {"id": "L1", "after": "items-cursor-1"}, variables
            return {"node": {"items": {
                "pageInfo": {"hasNextPage": False, "endCursor": None},
                "nodes": [{"nameWithOwner": "octocat/c"}, {"nameWithOwner": "octocat/a"}],
            }}}
        assert "user(login: $login)" in query, "public mode must query user(login:)"
        assert variables["login"] == "zorenkonte"
        if variables["after"] is None:
            return {"user": {"lists": {
                "pageInfo": {"hasNextPage": True, "endCursor": "lists-cursor-1"},
                "nodes": [{
                    "id": "L1", "name": "Selfhost", "slug": "selfhost",
                    "description": "Home lab", "isPrivate": False,
                    "items": {
                        "pageInfo": {"hasNextPage": True, "endCursor": "items-cursor-1"},
                        "nodes": [{"nameWithOwner": "octocat/b"}, {"nameWithOwner": "octocat/a"}, None],
                    },
                }],
            }}}
        assert variables["after"] == "lists-cursor-1", variables
        return {"user": {"lists": {
            "pageInfo": {"hasNextPage": False, "endCursor": None},
            "nodes": [{
                "id": "L2", "name": "Vue", "slug": "vue", "description": None, "isPrivate": False,
                "items": {"pageInfo": {"hasNextPage": False, "endCursor": None}, "nodes": []},
            }],
        }}}

    real_graphql, real_sleep = archive_stars._graphql, archive_stars.time.sleep
    archive_stars._graphql = fake_graphql
    archive_stars.time.sleep = lambda s: None
    try:
        cfg = {"username": "zorenkonte", "token": "t0k", "use_auth_user": False}
        got = REAL_FETCH_LISTS(cfg)
        assert got == {
            "selfhost": {"slug": "selfhost", "name": "Selfhost", "description": "Home lab",
                         "repos": ["octocat/a", "octocat/b", "octocat/c"]},
            "vue": {"slug": "vue", "name": "Vue", "description": None, "repos": []},
        }, got
        assert len(calls) == 3, calls

        # No token -> None (skipped), no request made.
        calls.clear()
        assert REAL_FETCH_LISTS({"username": "x", "token": "", "use_auth_user": False}) is None
        assert calls == []

        # A GraphQL failure -> None, never an exception.
        def boom(query, variables, token):
            raise RuntimeError("GraphQL errors: field 'lists' doesn't exist")
        archive_stars._graphql = boom
        assert REAL_FETCH_LISTS(cfg) is None

        # With the Actions token (user(login:) mode) GitHub reports 0 lists for
        # a user who does have them: must be treated as unknown -> None.
        def zero_lists(query, variables, token):
            return {"user": {"lists": {"pageInfo": {"hasNextPage": False}, "nodes": []}}}
        archive_stars._graphql = zero_lists
        assert REAL_FETCH_LISTS(cfg) is None, "0 lists via user(login:) must not wipe membership"

        # A PAT (STARS_TOKEN) queries viewer, with that token, and 0 lists is then real.
        seen = {}
        def viewer_only(query, variables, token):
            seen["token"] = token
            assert "viewer {" in query and "login" not in variables, (query[:60], variables)
            return {"viewer": {"lists": {"pageInfo": {"hasNextPage": False}, "nodes": []}}}
        archive_stars._graphql = viewer_only
        assert REAL_FETCH_LISTS({"username": "x", "token": "actions", "lists_token": "pat",
                                 "lists_as_viewer": True, "use_auth_user": False}) == {}
        assert seen["token"] == "pat", "lists must be fetched with STARS_TOKEN, not GH_TOKEN"
        assert REAL_FETCH_LISTS({"username": "x", "token": "t", "use_auth_user": True}) == {}
    finally:
        archive_stars._graphql, archive_stars.time.sleep = real_graphql, real_sleep
    print("[ok] fetch_lists: paginates lists and >100-item lists, skips without token, "
          "survives GraphQL errors, treats 0 lists via user(login:) as unknown, "
          "uses viewer + STARS_TOKEN for a PAT")


if __name__ == "__main__":
    main()
