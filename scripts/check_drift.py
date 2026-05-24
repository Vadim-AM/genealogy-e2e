#!/usr/bin/env python3
"""Lint test files for drift from CLAUDE.md suite rules.

Catches violations of:
- **Rule #5** (no hardcoded timeouts / fixed sleeps):
  - `page.wait_for_timeout(N)` — use `expect()` or `expect_response`
  - `time.sleep(N)` with literal — use `time.sleep(TIMEOUTS.polling_interval)`
  - `timeout=N` literal — use `TIMEOUTS.api_*` / `TIMEOUTS.pw_*`
- **Rule #8** (no raw `.json()` in tests):
  - `.json()` in test files — use `.schema(Model)` or typed API helper
- **Rule #9** (no raw URL strings):
  - `'/api/...'` literal — use `API.*` from `tests/api_paths.py`

Whitelist a single line by appending `# noqa: drift`.

Usage:
    python scripts/check_drift.py
    python scripts/check_drift.py --root /path/to/repo

Exits 1 on any violation, 0 otherwise. Intended for `pre-commit` and CI.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Files that DEFINE the constants / are pure infrastructure are exempt.
EXEMPT_RELPATHS = {
    "conftest.py",
    "tests/test_api_coverage.py",
}

EXEMPT_PREFIXES = (
    "api/",
    "config/",
    "framework/",
    "models/",
    "fixtures/",
    "test_data/",
    "src/",
)

NOQA_RE = re.compile(r"#\s*noqa:\s*drift\b")

# Rule 8: raw .json() without typed wrapper (test files only)
_RAW_JSON_RE = re.compile(r"\.json\(\)")

RULES = (
    # (regex, hint)
    (
        re.compile(r"\.wait_for_timeout\s*\("),
        "Rule #5: page.wait_for_timeout() — use expect()/expect_response auto-wait",
    ),
    (
        re.compile(r"\btime\.sleep\s*\(\s*\d"),
        "Rule #5: hardcoded time.sleep — use time.sleep(TIMEOUTS.polling_interval)",
    ),
    (
        re.compile(r"\btimeout\s*=\s*\d"),
        "Rule #5: hardcoded `timeout=N` — use TIMEOUTS.api_* or TIMEOUTS.pw_*",
    ),
    (
        # `"/api/..."` literal after `(` `,` `=` `[` `{` (call/assign context).
        # Avoids matching `/api/...` mentioned in docstrings/comments mid-line.
        re.compile(r"[(\[{=,]\s*[fb]?['\"]/api/[a-z_]"),
        "Rule #9: raw '/api/...' URL string — use routes.* from api/routes.py",
    ),
)


def is_exempt(rel: str) -> bool:
    if rel in EXEMPT_RELPATHS:
        return True
    return any(rel.startswith(prefix) for prefix in EXEMPT_PREFIXES)


def scan_file(path: Path, root: Path) -> list[tuple[Path, int, str, str]]:
    """Return [(path, lineno, rule_hint, raw_line)] for every violation."""
    violations: list[tuple[Path, int, str, str]] = []
    rel = path.relative_to(root)
    rel_str = str(rel)
    is_test_file = rel_str.startswith("tests/") and path.name != "test_api_coverage.py"
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    in_docstring = False
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        # Track triple-quoted strings (skip docstrings / multi-line strings).
        if '"""' in stripped or "'''" in stripped:
            count = stripped.count('"""') + stripped.count("'''")
            if count % 2 == 1:  # odd number = toggling state
                in_docstring = not in_docstring
            if in_docstring:
                continue
        if in_docstring:
            continue
        if NOQA_RE.search(line):
            continue
        # Skip pure-comment lines.
        if stripped.startswith("#"):
            continue
        for rule_re, hint in RULES:
            if rule_re.search(line):
                violations.append((rel, lineno, hint, line.rstrip()))
        # Rule 8: raw .json() in test files only (not test_api_coverage.py)
        if is_test_file and _RAW_JSON_RE.search(line):
            violations.append(
                (
                    rel,
                    lineno,
                    "Rule #8: raw .json() — use .schema(Model) or typed API helper",
                    line.rstrip(),
                )
            )
    return violations


def collect_targets(root: Path) -> list[Path]:
    scan_dirs = ["tests", "pages", "helpers"]
    targets = []
    for d in scan_dirs:
        scan_root = root / d
        if scan_root.exists():
            targets.extend(p for p in scan_root.rglob("*.py") if not is_exempt(str(p.relative_to(root))))
    return targets


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root (default: parent of scripts/)",
    )
    args = parser.parse_args(argv)

    root: Path = args.root.resolve()
    targets = collect_targets(root)

    all_violations: list[tuple[Path, int, str, str]] = []
    for p in targets:
        all_violations.extend(scan_file(p, root))

    if not all_violations:
        print(f"check_drift: {len(targets)} files OK")
        return 0

    print(f"check_drift: {len(all_violations)} violation(s) across {len(targets)} files\n")
    for rel, lineno, hint, raw in all_violations:
        print(f"  {rel}:{lineno}")
        print(f"    → {hint}")
        print(f"    | {raw.strip()}")
        print()
    print(
        "Append `# noqa: drift` on a line to whitelist a single legitimate use\n"
        "(e.g. parametrize fixtures for router-level routes that have no helper)."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
