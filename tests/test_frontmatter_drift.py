#!/usr/bin/env python3
"""Drift test: z-wiki's hand-rolled parse_frontmatter() vs PyYAML.

review.md P2: "Add an invariant test that every frontmatter parses
identically under this parser and yaml.safe_load."

For every real page in wiki/{sources,concepts,entities,syntheses,outputs}
this test reads the frontmatter with both parsers and asserts no silent
data loss:

    - same set of keys
    - per key: same normalized value (see _normalize)

PyYAML is an *optional* tooling dep (not in requirements.txt core); the
test self-skips with exit 0 when it is unavailable so contributors on a
zero-dep machine don't trip check_invariants.sh.

Run standalone: python3 tests/test_frontmatter_drift.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

try:
    import yaml  # type: ignore
except ModuleNotFoundError:
    print("SKIP: PyYAML not installed (drift test is advisory, not a core dep)")
    sys.exit(0)

from build_meta import FRONTMATTER_RE, parse_frontmatter  # noqa: E402

PAGE_DIRS = ("sources", "concepts", "entities", "syntheses", "outputs")


def _extract_fm_text(text: str) -> str | None:
    """Return the raw frontmatter body, or None if the page has none.

    Mirrors parse_frontmatter's BOM / leading-whitespace trimming so the
    two parsers see identical bytes.
    """
    if text.startswith("\ufeff"):
        text = text[1:]
    text = text.lstrip("\n\r")
    m = FRONTMATTER_RE.match(text)
    return m.group(1) if m else None


def _normalize(v: Any) -> Any:
    """Collapse PyYAML's typed values to the string/list-of-string shape
    parse_frontmatter emits. Type coercion is where legitimate drift
    happens; *value* drift is the bug this test hunts for."""
    if isinstance(v, list):
        return [_normalize(x) for x in v]
    if isinstance(v, bool):
        # PyYAML parses `yes`/`no`/`true` as bool; parser keeps the word.
        return str(v).lower()
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        return str(v)
    return str(v)


def _diff(page: Path, mine: dict, ref: dict) -> list[str]:
    errs: list[str] = []
    if set(mine) != set(ref):
        only_mine = sorted(set(mine) - set(ref))
        only_ref = sorted(set(ref) - set(mine))
        if only_mine:
            errs.append(f"{page}: keys only in parse_frontmatter: {only_mine}")
        if only_ref:
            errs.append(f"{page}: keys only in yaml.safe_load: {only_ref}")
    for k in sorted(set(mine) & set(ref)):
        a = _normalize(mine[k])
        b = _normalize(ref[k])
        if a != b:
            errs.append(f"{page}: key {k!r}: mine={a!r} yaml={b!r}")
    return errs


def main() -> int:
    vault = ROOT
    pages: list[Path] = []
    for d in PAGE_DIRS:
        root = vault / "wiki" / d
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.md")):
            if p.name.startswith("_index"):
                continue
            pages.append(p)

    failures: list[str] = []
    checked = 0
    for p in pages:
        text = p.read_text(encoding="utf-8")
        fm_text = _extract_fm_text(text)
        if fm_text is None:
            continue
        mine = parse_frontmatter(text)
        try:
            ref_raw = yaml.safe_load(fm_text)
        except yaml.YAMLError as e:
            failures.append(f"{p}: yaml.safe_load raised {type(e).__name__}: {e}")
            continue
        ref = ref_raw if isinstance(ref_raw, dict) else {}
        failures.extend(_diff(p.relative_to(vault), mine, ref))
        checked += 1

    if failures:
        for f in failures[:50]:  # cap output volume
            print(f"FAIL {f}")
        if len(failures) > 50:
            print(f"... ({len(failures) - 50} more)")
        print(f"{len(failures)} drift(s) across {checked} page(s)")
        return 1
    print(f"no drift across {checked} page(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
