#!/usr/bin/env python3
"""Offline self-test for the star archiver (no network, standard library only).

Proves the two properties the archive exists to guarantee:

1. A repo that drops out of the live starred list is NOT deleted -- it stays in
   stars.json flagged status="gone" with a gone_since date and its description
   intact.
2. A repo picked into TODAY.md has its reviewed_at persisted to stars.json
   (because the pipeline saves AFTER rendering TODAY.md).

Run with:  python scripts/test_archive_stars.py
"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import archive_stars  # noqa: E402


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
    archive_stars.fetch_stars = lambda cfg: run1_live  # monkeypatch: no network
    archive_stars.run(config, now=RUN1, paths=paths)

    state1 = _load(paths["stars_json"])
    repos1 = state1["repos"]
    assert set(repos1) == {"octocat/alpha", "octocat/beta", "octocat/gamma"}, repos1.keys()
    assert all(repos1[n]["status"] == "active" for n in repos1), "all should be active after run 1"

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
    archive_stars.fetch_stars = lambda cfg: run2_live
    archive_stars.run(config, now=RUN2, paths=paths)

    state2 = _load(paths["stars_json"])
    repos2 = state2["repos"]

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

    print("\nALL SELF-TESTS PASSED")


if __name__ == "__main__":
    main()
