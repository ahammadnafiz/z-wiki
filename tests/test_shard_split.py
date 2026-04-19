#!/usr/bin/env python3
"""Tests for shard_index.render_type_index.

review.md P2: shard split is only exercised by real vault data that
is always far under SHARD_CHAR_BUDGET. This test drives synthetic
entries large enough to force the A-H / I-P / Q-Z split and asserts:

    - single parent _index.md with pointer links (no row lines)
    - three shard files (_index-a-h.md, _index-i-p.md, _index-q-z.md)
    - each entry lands in exactly one shard
    - digit-leading titles route to the q-z bucket

Run standalone: python3 tests/test_shard_split.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from shard_index import (  # noqa: E402
    SHARD_CHAR_BUDGET,
    render_type_index,
)


def _check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _padding(n_chars: int) -> str:
    return ("lorem ipsum dolor sit amet consectetur " * 40)[:n_chars]


def test_single_file_when_under_budget(tmp_vault: Path) -> None:
    entries = [
        {"slug": f"concept-{i}", "title": f"Concept {i}", "summary": "short"}
        for i in range(5)
    ]
    outs = render_type_index("concepts", entries, tmp_vault)
    _check(len(outs) == 1, f"expected single _index.md, got {[str(p) for p, _ in outs]}")
    path, body = outs[0]
    _check(path.name == "_index.md", f"unexpected path: {path}")
    for e in entries:
        _check(f"[[{e['slug']}|" in body, f"{e['slug']} missing from body")


def test_shards_into_three_alphabetical_buckets(tmp_vault: Path) -> None:
    # Use big per-entry padding so the combined body exceeds the 40K
    # char budget with a manageable entry count.
    padding = _padding(800)
    buckets_seed = {
        "a-h": ["Alpha", "Bravo", "Charlie", "Delta", "Echo", "Foxtrot", "Golf", "Hotel"],
        "i-p": ["India", "Juliet", "Kilo", "Lima", "Mike", "November", "Oscar", "Papa"],
        "q-z": ["Quebec", "Romeo", "Sierra", "Tango", "Uniform", "Victor", "Whiskey",
                "X-ray", "Yankee", "Zulu", "9-lives"],
    }

    entries: list[dict] = []
    slug_to_bucket: dict[str, str] = {}
    counter = 0
    # Repeat the alphabet bucket list enough times to clear the budget.
    # Each row is ~850 chars and SHARD_CHAR_BUDGET is 40_000, so ~55
    # entries is the floor. Three full passes = 81 entries, safely over.
    for _ in range(3):
        for bucket, titles in buckets_seed.items():
            for t in titles:
                slug = f"entry-{counter}"
                entries.append({"slug": slug, "title": f"{t} {counter}", "summary": padding})
                slug_to_bucket[slug] = bucket
                counter += 1

    rough_size = sum(
        len(e["summary"]) + len(e["title"]) + len(e["slug"]) + 20 for e in entries
    )
    _check(
        rough_size > SHARD_CHAR_BUDGET,
        f"synthetic fixture too small to force split: {rough_size} <= {SHARD_CHAR_BUDGET}",
    )

    outs = render_type_index("concepts", entries, tmp_vault)
    by_name = {p.name: body for p, body in outs}
    _check(
        set(by_name) == {"_index.md", "_index-a-h.md", "_index-i-p.md", "_index-q-z.md"},
        f"unexpected shard file set: {sorted(by_name)}",
    )

    parent = by_name["_index.md"]
    _check("_index-a-h.md" in parent, "parent _index.md missing a-h pointer")
    _check("_index-i-p.md" in parent, "parent _index.md missing i-p pointer")
    _check("_index-q-z.md" in parent, "parent _index.md missing q-z pointer")
    _check(
        "[[entry-0|" not in parent,
        "parent _index.md leaked an entry row; should only link to shards",
    )

    # Match on the wikilink form `[[slug|...]]` so that e.g. entry-1 does
    # not falsely match entry-10 by substring.
    def _has(slug: str, body: str) -> bool:
        return f"[[{slug}|" in body or f"[[{slug}]]" in body

    for slug, bucket in slug_to_bucket.items():
        expected_shard = f"_index-{bucket}.md"
        _check(
            _has(slug, by_name[expected_shard]),
            f"{slug} should land in {expected_shard} (title bucket {bucket})",
        )
        other_shards = [
            n for n in by_name if n.startswith("_index-") and n != expected_shard
        ]
        for other in other_shards:
            _check(
                not _has(slug, by_name[other]),
                f"{slug} leaked into {other} (should be only in {expected_shard})",
            )


def test_digit_prefixed_title_routes_to_q_z(tmp_vault: Path) -> None:
    padding = _padding(800)
    entries: list[dict] = [{"slug": "n-one", "title": "9-entry", "summary": padding}]
    entries += [
        {"slug": f"alpha-{i}", "title": f"Alpha-{i}", "summary": padding}
        for i in range(40)
    ]
    entries += [
        {"slug": f"mike-{i}", "title": f"Mike-{i}", "summary": padding}
        for i in range(40)
    ]
    outs = render_type_index("concepts", entries, tmp_vault)
    by_name = {p.name: body for p, body in outs}
    _check("_index-q-z.md" in by_name, "q-z shard must exist in split output")
    _check(
        "[[n-one|" in by_name["_index-q-z.md"],
        "digit-prefixed title should land in q-z bucket",
    )


def main() -> int:
    tmp_vault = Path("/tmp/zwiki-shard-test")
    tests = [
        test_single_file_when_under_budget,
        test_shards_into_three_alphabetical_buckets,
        test_digit_prefixed_title_routes_to_q_z,
    ]
    failed = 0
    for t in tests:
        try:
            t(tmp_vault)
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    if failed:
        print(f"{failed}/{len(tests)} shard tests failed")
        return 1
    print(f"all {len(tests)} shard tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
