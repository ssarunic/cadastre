#!/usr/bin/env python3
"""Cut a release: bump every version string, finalize CHANGELOG.md, commit, tag.

The monorepo shares one version number. It is written in seven places (four
``pyproject.toml`` files, two ``__version__`` constants and the MCP server's
``server_version``); this script keeps them identical and creates the annotated
tag ``vX.Y.Z`` that marks the release. The process is described in
specs/release-process.md.

Usage:
    scripts/release.py X.Y.Z             # bump, finalize changelog, commit, tag
    scripts/release.py X.Y.Z --dry-run   # show what would change, touch nothing
    scripts/release.py --check           # versions in sync and changelog entry present
    scripts/release.py --notes X.Y.Z     # print the changelog section (release notes)

Nothing is pushed. After a successful run the script prints the push command.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CHANGELOG = REPO_ROOT / "CHANGELOG.md"
REPO_URL = "https://github.com/ssarunic/cadastre"
RELEASE_BRANCH = "main"

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")

# (path relative to the repo root, regex whose group "v" is the version string)
VERSION_FILES: list[tuple[str, re.Pattern[str]]] = [
    ("pyproject.toml", re.compile(r'^version = "(?P<v>[^"]+)"$', re.M)),
    ("api/pyproject.toml", re.compile(r'^version = "(?P<v>[^"]+)"$', re.M)),
    ("cli/pyproject.toml", re.compile(r'^version = "(?P<v>[^"]+)"$', re.M)),
    ("mcp/pyproject.toml", re.compile(r'^version = "(?P<v>[^"]+)"$', re.M)),
    (
        "api/src/cadastral_api/__init__.py",
        re.compile(r'^__version__ = "(?P<v>[^"]+)"$', re.M),
    ),
    (
        "cli/src/cadastral_cli/__init__.py",
        re.compile(r'^__version__ = "(?P<v>[^"]+)"$', re.M),
    ),
    (
        "mcp/src/cadastral_mcp/config.py",
        re.compile(r'^(?P<indent>\s*)server_version: str = "(?P<v>[^"]+)"$', re.M),
    ),
]

RELEASE_HEADING = re.compile(r"^## \[(?P<v>\d+\.\d+\.\d+)\] - (?P<date>\d{4}-\d{2}-\d{2})$", re.M)
UNRELEASED_HEADING = "## [Unreleased]"


class ReleaseError(Exception):
    """A precondition failed; the message is printed and the script exits 1."""


# --------------------------------------------------------------------------- #
# Version strings
# --------------------------------------------------------------------------- #


def read_versions() -> dict[str, str]:
    """Return {relative path: version string} for every versioned file."""
    found: dict[str, str] = {}
    for rel, pattern in VERSION_FILES:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        matches = list(pattern.finditer(text))
        if len(matches) != 1:
            raise ReleaseError(f"{rel}: expected exactly one version string, found {len(matches)}")
        found[rel] = matches[0].group("v")
    return found


def write_versions(new: str) -> list[str]:
    """Rewrite every version string to ``new``; return the files that changed."""
    changed: list[str] = []
    for rel, pattern in VERSION_FILES:
        path = REPO_ROOT / rel
        text = path.read_text(encoding="utf-8")

        def replace(match: re.Match[str]) -> str:
            return match.group(0).replace(match.group("v"), new, 1)

        updated, count = pattern.subn(replace, text)
        if count != 1:
            raise ReleaseError(f"{rel}: expected exactly one version string, found {count}")
        if updated != text:
            path.write_text(updated, encoding="utf-8")
            changed.append(rel)
    return changed


def current_version() -> str:
    versions = read_versions()
    distinct = set(versions.values())
    if len(distinct) != 1:
        lines = "\n".join(f"  {v:10}  {rel}" for rel, v in versions.items())
        raise ReleaseError(f"version strings disagree:\n{lines}")
    return distinct.pop()


# --------------------------------------------------------------------------- #
# Changelog
# --------------------------------------------------------------------------- #


def changelog_sections(text: str) -> dict[str, str]:
    """Split CHANGELOG.md into {section title: body} for every ``## `` heading."""
    sections: dict[str, str] = {}
    current: str | None = None
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(body).strip()
            current = line[3:].strip()
            body = []
        elif current is not None:
            body.append(line)
    if current is not None:
        sections[current] = "\n".join(body).strip()
    return sections


def release_notes(version: str) -> str:
    """The body of the ``## [version] - date`` section, without link references."""
    text = CHANGELOG.read_text(encoding="utf-8")
    for title, body in changelog_sections(text).items():
        if title.startswith(f"[{version}]"):
            # Drop the trailing "[x.y.z]: url" reference lines that live after the last section.
            lines = [ln for ln in body.splitlines() if not re.match(r"^\[[^\]]+\]: \S+$", ln)]
            return "\n".join(lines).strip()
    raise ReleaseError(f"CHANGELOG.md has no section for {version}")


def latest_changelog_version() -> str | None:
    match = RELEASE_HEADING.search(CHANGELOG.read_text(encoding="utf-8"))
    return match.group("v") if match else None


def finalize_changelog(version: str, date: str, dry_run: bool) -> bool:
    """Turn the ``[Unreleased]`` section into ``[version] - date``.

    Returns True when the file was (or would be) modified, False when the
    section already existed. Raises when there is nothing to release.
    """
    text = CHANGELOG.read_text(encoding="utf-8")
    sections = changelog_sections(text)
    if any(title.startswith(f"[{version}]") for title in sections):
        return False
    unreleased = sections.get("[Unreleased]", "")
    unreleased_body = "\n".join(
        ln for ln in unreleased.splitlines() if not re.match(r"^\[[^\]]+\]: \S+$", ln)
    ).strip()
    if not unreleased_body:
        raise ReleaseError(
            "CHANGELOG.md: the [Unreleased] section is empty; describe the release first"
        )
    previous = latest_changelog_version()

    new_heading = f"## [{version}] - {date}"
    if UNRELEASED_HEADING not in text:
        raise ReleaseError("CHANGELOG.md: missing '## [Unreleased]' heading")
    text = text.replace(UNRELEASED_HEADING, f"{UNRELEASED_HEADING}\n\n{new_heading}", 1)

    # Link references at the bottom of the file.
    unreleased_ref = re.compile(r"^\[Unreleased\]: \S+$", re.M)
    compare = f"[Unreleased]: {REPO_URL}/compare/v{version}...HEAD"
    if previous:
        release_ref = f"[{version}]: {REPO_URL}/compare/v{previous}...v{version}"
    else:
        release_ref = f"[{version}]: {REPO_URL}/releases/tag/v{version}"
    if unreleased_ref.search(text):
        text = unreleased_ref.sub(f"{compare}\n{release_ref}", text, count=1)
    else:
        text = text.rstrip("\n") + f"\n\n{compare}\n{release_ref}\n"

    if not dry_run:
        CHANGELOG.write_text(text, encoding="utf-8")
    return True


# --------------------------------------------------------------------------- #
# Git
# --------------------------------------------------------------------------- #


#: What scripts/build_docs.py rewrites: the generated pages of both editions
#: and the documentation catalogs.
GENERATED_DOC_PATHS = ("docs/en/cli", "docs/hr/cli", "po/docs.pot", "po/docs-hr.po")


def rebuild_docs() -> list[str]:
    """Regenerate the CLI documentation after the version bump.

    Every generated page carries the version in its banner ("Generated from
    `cadastral X.Y.Z`"), so pages built before the bump fail the documentation
    gate on the release commit. Returns the generated paths to add.
    """
    build = REPO_ROOT / "scripts" / "build_docs.py"
    subprocess.run([sys.executable, str(build)], check=True, cwd=REPO_ROOT)
    return list(GENERATED_DOC_PATHS)


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=False
    )
    if check and result.returncode != 0:
        raise ReleaseError(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout.strip()


def check_git_preconditions(version: str, allow_branch: str | None) -> None:
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    expected = allow_branch or RELEASE_BRANCH
    if branch != expected:
        raise ReleaseError(
            f"on branch {branch!r}; releases are cut from {expected!r} "
            "(use --allow-branch to override)"
        )
    if git("status", "--porcelain"):
        raise ReleaseError("working tree is not clean; commit or stash first")
    if git("tag", "-l", f"v{version}"):
        raise ReleaseError(f"tag v{version} already exists")
    old = current_version()
    if tuple(map(int, version.split("."))) <= tuple(map(int, old.split("."))):
        raise ReleaseError(f"new version {version} must be greater than current {old}")


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #


def cmd_check() -> int:
    """Exit 0 when version strings agree and CHANGELOG.md documents that version."""
    version = current_version()
    if not SEMVER.match(version):
        raise ReleaseError(f"version {version!r} is not X.Y.Z")
    if not release_notes(version):  # raises when the section is missing
        raise ReleaseError(f"CHANGELOG.md: section for {version} is empty")
    print(f"ok: version {version} is consistent across {len(VERSION_FILES)} files")
    return 0


def cmd_notes(version: str) -> int:
    print(release_notes(version))
    return 0


def cmd_release(version: str, date: str, dry_run: bool, allow_branch: str | None) -> int:
    if not SEMVER.match(version):
        raise ReleaseError(f"version {version!r} is not X.Y.Z")
    check_git_preconditions(version, allow_branch)

    prefix = "[dry-run] " if dry_run else ""
    old = current_version()
    print(f"{prefix}bump {old} -> {version}")

    if finalize_changelog(version, date, dry_run):
        print(f"{prefix}CHANGELOG.md: [Unreleased] -> [{version}] - {date}")
    else:
        print(f"{prefix}CHANGELOG.md: section [{version}] already present")

    if dry_run:
        for rel, _pattern in VERSION_FILES:
            print(f"{prefix}update {rel}")
        print(f"{prefix}rebuild the generated CLI documentation (scripts/build_docs.py)")
        print(f"{prefix}git commit -m 'Release v{version}'")
        print(f"{prefix}git tag -a v{version}")
        return 0

    changed = write_versions(version)
    cmd_check()
    docs_changed = rebuild_docs()

    git("add", "CHANGELOG.md", *changed, *docs_changed)
    git("commit", "-m", f"Release v{version}")
    tag_message = f"Release v{version}\n\n{release_notes(version)}\n"
    git("tag", "-a", f"v{version}", "-m", tag_message)

    print(f"created commit and tag v{version}")
    print(f"next: review with `git show v{version}`, then publish with")
    print(f"  git push origin {allow_branch or RELEASE_BRANCH} v{version}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("version", nargs="?", help="new version, X.Y.Z")
    parser.add_argument("--check", action="store_true", help="verify consistency and exit")
    parser.add_argument(
        "--notes", action="store_true", help="print the changelog section for VERSION"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="report what would happen, change nothing"
    )
    parser.add_argument(
        "--date", default=dt.date.today().isoformat(), help="release date (default: today)"
    )
    parser.add_argument(
        "--allow-branch", metavar="BRANCH", help=f"release from BRANCH instead of {RELEASE_BRANCH}"
    )
    args = parser.parse_args(argv)

    try:
        if args.check:
            return cmd_check()
        if not args.version:
            parser.error("VERSION is required (or use --check)")
        if args.notes:
            return cmd_notes(args.version)
        return cmd_release(args.version, args.date, args.dry_run, args.allow_branch)
    except ReleaseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
