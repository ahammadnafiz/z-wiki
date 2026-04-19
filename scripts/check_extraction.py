#!/usr/bin/env python3
"""Heuristic check: does extracted markdown look like valid prose?

Invoked by INGEST after markitdown on binary sources (PDF, DOCX,
PPTX, EPUB, HTML). Catches the common failure mode where markitdown
silently produces garbled output on scanned / image-only documents.

Checks (exit 1 on any violation):
    1. Minimum size:           >= 200 characters of non-whitespace.
    2. Alphabetic ratio:       >= 40% of non-whitespace chars are
                               letters (a-z, A-Z). Guards against
                               base64, binary junk, symbol soup.
    3. Whitespace density:     no single run of non-whitespace
                               longer than 500 chars (binary dumps
                               come through as one giant line).
    4. Word formation:         at least 50 distinct 3+ letter words.
    5. Token sanity:           average word length <= 15 (catches
                               concatenated streams, broken encoding).

Usage:
    python3 scripts/check_extraction.py /tmp/extracted.md
    # exit 0: looks like prose, proceed with INGEST
    # exit 1: likely gibberish, refuse and log why
    # exit 2: missing file or argument error

Design notes:
    All thresholds are deliberately conservative. A well-formed
    200-word article summary clears every gate. The target false
    positive rate is low; the target false negative rate is lower
    still (gibberish masquerading as prose causes silent
    downstream corruption).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MIN_CHARS = 200
MIN_ALPHA_RATIO = 0.40
MAX_NONWHITESPACE_RUN = 500
MIN_DISTINCT_WORDS = 50
MAX_AVG_WORD_LEN = 15

ALPHA_RE = re.compile(r"[A-Za-z]")
WORD_RE = re.compile(r"[A-Za-z]{3,}")


def check(text: str) -> list[str]:
    """Return a list of failure reasons. Empty = looks clean."""
    failures: list[str] = []
    nonws = "".join(text.split())

    if len(nonws) < MIN_CHARS:
        failures.append(
            f"too short: {len(nonws)} non-whitespace chars (minimum {MIN_CHARS})"
        )

    alpha = len(ALPHA_RE.findall(nonws))
    if nonws and alpha / len(nonws) < MIN_ALPHA_RATIO:
        ratio = alpha / max(len(nonws), 1)
        failures.append(
            f"low alphabetic ratio: {ratio:.1%} "
            f"(minimum {MIN_ALPHA_RATIO:.0%}); probably base64, binary, or symbol soup"
        )

    longest_run = max(
        (len(chunk) for chunk in text.split()),
        default=0,
    )
    if longest_run > MAX_NONWHITESPACE_RUN:
        failures.append(
            f"unbroken run of {longest_run} non-whitespace chars "
            f"(cap {MAX_NONWHITESPACE_RUN}); extraction lost line breaks"
        )

    words = WORD_RE.findall(text)
    distinct = len(set(w.lower() for w in words))
    if distinct < MIN_DISTINCT_WORDS:
        failures.append(
            f"only {distinct} distinct 3+-letter words "
            f"(minimum {MIN_DISTINCT_WORDS}); likely empty/template-only output"
        )

    if words:
        avg_len = sum(len(w) for w in words) / len(words)
        if avg_len > MAX_AVG_WORD_LEN:
            failures.append(
                f"average word length {avg_len:.1f} exceeds {MAX_AVG_WORD_LEN}; "
                f"likely concatenated tokens or broken encoding"
            )

    return failures


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_extraction.py <path-to-markdown>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"file not found: {path}", file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8", errors="replace")
    failures = check(text)
    if failures:
        print(f"GIBBERISH DETECTED in {path}:", file=sys.stderr)
        for f in failures:
            print(f"  - {f}", file=sys.stderr)
        print(
            "\nRecommended: fall back to visual / rasterized read of the "
            "original, or refuse this source and tell the user.",
            file=sys.stderr,
        )
        return 1
    print(f"ok: {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
