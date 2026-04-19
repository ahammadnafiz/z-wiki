#!/usr/bin/env python3
"""Build wiki/.meta/{backlinks.json,sources.json,search-index.tsv}.

Pure Python stdlib. Idempotent. Safe to run any time.

Usage:
    python3 scripts/build_meta.py              # full rebuild
    python3 scripts/build_meta.py --only PATH  # incremental: refresh one page's outbound links
    python3 scripts/build_meta.py --check      # no writes; exit 1 if sidecar is stale

The sidecar is derived data. Source of truth stays in markdown
frontmatter + wikilinks. LINT reconciles drift.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------
# Parsing helpers
# --------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
LIST_HEAD_RE = re.compile(r"^(\w[\w-]*):\s*$")
LIST_ITEM_RE = re.compile(r"^\s+-\s+(.+?)\s*$")
SIMPLE_KV_RE = re.compile(r"^(\w[\w-]*):\s*(.+?)\s*$")


def parse_frontmatter(text: str) -> dict:
    """Return the YAML-ish frontmatter as a dict. Lightweight parser;
    handles the subset z-wiki uses (scalars + list-of-scalars).

    Multi-line list keys (any `key:` followed by indented `- item` lines)
    are parsed as list-of-string — required for `tags:`, `related:`,
    `authors:`, `sources_cited:`, and any other list-valued field the
    schema grows."""
    if text.startswith("\ufeff"):
        text = text[1:]
    text = text.lstrip("\n\r")
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    body = m.group(1)
    out: dict = {}
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        m_head = LIST_HEAD_RE.match(line)
        if m_head:
            key = m_head.group(1)
            items: list[str] = []
            i += 1
            while i < len(lines):
                m2 = LIST_ITEM_RE.match(lines[i])
                if not m2:
                    break
                items.append(_unquote(m2.group(1)))
                i += 1
            out[key] = items
            continue
        m_kv = SIMPLE_KV_RE.match(line)
        if m_kv:
            key, val = m_kv.group(1), m_kv.group(2)
            val = val.strip()
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                items = [_unquote(s.strip()) for s in inner.split(",")] if inner else []
                out[key] = items
            else:
                out[key] = _unquote(val)
        i += 1
    return out


def _unquote(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in {'"', "'"}:
        return s[1:-1]
    return s


def body_wikilinks(text: str) -> list[str]:
    """Return every [[target]] in the body (not frontmatter), deduped, in order."""
    if text.startswith("\ufeff"):
        text = text[1:]
    text = text.lstrip("\n\r")
    m = FRONTMATTER_RE.match(text)
    body = text[m.end():] if m else text
    seen: dict[str, None] = {}
    for match in WIKILINK_RE.finditer(body):
        target = match.group(1).strip()
        if target and target not in seen:
            seen[target] = None
    return list(seen)


# --------------------------------------------------------------------------
# Filesystem walk
# --------------------------------------------------------------------------

PAGE_DIRS = ["sources", "concepts", "entities", "syntheses", "outputs"]


def all_pages(vault: Path) -> list[Path]:
    pages: list[Path] = []
    for d in PAGE_DIRS:
        root = vault / "wiki" / d
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.md")):
            if p.name.startswith("_index"):
                continue
            pages.append(p)
    return pages


def slug_of(path: Path) -> str:
    return path.stem


# --------------------------------------------------------------------------
# Builders
# --------------------------------------------------------------------------

def build(vault: Path) -> dict:
    pages = all_pages(vault)
    # Detect slug collisions up-front. The global-slug-uniqueness invariant
    # is load-bearing: wikilinks resolve by stem, and a collision silently
    # corrupts the backlinks graph (last-write-wins in the dict). Fail loud.
    page_by_slug: dict[str, Path] = {}
    collisions: dict[str, list[Path]] = defaultdict(list)
    for p in pages:
        slug = slug_of(p)
        if slug in page_by_slug:
            collisions[slug].append(p)
            # First winner already recorded; remember the earlier path too.
            if page_by_slug[slug] not in collisions[slug]:
                collisions[slug].insert(0, page_by_slug[slug])
        else:
            page_by_slug[slug] = p
    if collisions:
        msg_lines = ["slug collision: wikilinks resolve by filename stem and must be globally unique"]
        for slug, paths in sorted(collisions.items()):
            rels = ", ".join(str(p.relative_to(vault)) for p in paths)
            msg_lines.append(f"  {slug}: {rels}")
        raise SystemExit("\n".join(msg_lines))

    # Resolve wikilinks by slug (globally unique filename invariant).
    outbound: dict[str, list[str]] = {}
    outbound_sources_only: dict[str, list[str]] = {}
    page_fm: dict[str, dict] = {}

    for p in pages:
        text = p.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        page_fm[slug_of(p)] = fm
        links = [l for l in body_wikilinks(text) if l in page_by_slug]
        outbound[slug_of(p)] = links

    # Inverse: backlinks.
    # Three axes are tracked:
    #   inbound_all       — every inbound wikilink (used by LINT, graph views).
    #   inbound_sources   — inbound only from wiki/sources/ (authoritative signal).
    #   inbound_primary   — inbound from sources+concepts+entities (promotion signal).
    # Outputs and syntheses are Claude-written downstream artifacts; counting
    # them for promotion would let the system bootstrap its own importance.
    PRIMARY_TYPES = {"sources", "concepts", "entities"}
    inbound_all: dict[str, list[str]] = defaultdict(list)
    inbound_sources: dict[str, list[str]] = defaultdict(list)
    inbound_primary: dict[str, list[str]] = defaultdict(list)
    for src_slug, targets in outbound.items():
        src_path = page_by_slug[src_slug]
        src_type = src_path.parent.name
        is_source = src_type == "sources"
        is_primary = src_type in PRIMARY_TYPES
        for t in targets:
            inbound_all[t].append(src_slug)
            if is_source:
                inbound_sources[t].append(src_slug)
            if is_primary:
                inbound_primary[t].append(src_slug)

    # backlinks.json
    backlinks_nodes: dict[str, dict] = {}
    for slug, path in sorted(page_by_slug.items()):
        ia = sorted(set(inbound_all.get(slug, [])))
        isc = sorted(set(inbound_sources.get(slug, [])))
        ip = sorted(set(inbound_primary.get(slug, [])))
        backlinks_nodes[slug] = {
            "path": str(path.relative_to(vault)).replace(os.sep, "/"),
            "type": path.parent.name,
            "inbound_sources": isc,
            "inbound_primary": ip,
            "inbound_all": ia,
            "source_count": len(isc),
            "inbound_refs": len(ia),
            "inbound_refs_primary": len(ip),
        }
    backlinks = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "nodes": backlinks_nodes,
    }

    # sources.json
    source_entries: list[dict] = []
    for slug, path in sorted(page_by_slug.items()):
        if path.parent.name != "sources":
            continue
        fm = page_fm.get(slug, {})
        source_entries.append({
            "slug": slug,
            "path": str(path.relative_to(vault)).replace(os.sep, "/"),
            "source_path": fm.get("source_path", ""),
            "title": fm.get("title", slug),
            "summary": fm.get("summary", ""),
            "tags": fm.get("tags", []) if isinstance(fm.get("tags"), list) else [],
            "date_modified": fm.get("date_modified", ""),
            "last_seen": fm.get("last_seen", ""),
            "source_type": fm.get("source_type", ""),
        })
    sources = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sources": source_entries,
    }

    # search-index.tsv  (one line per page, tab-separated, grep-friendly)
    #
    # SHARED CONTRACT with scripts/wiki_search.py — keep aligned.
    # Column order (5 fields, tab-separated):   path \t title \t tags \t concepts \t summary
    # We intentionally do NOT tokenize here. Tokenization is query-time in
    # wiki_search.tokenize() using TOKEN_RE = r"[a-z0-9][a-z0-9-]*"; the chars
    # we emit below must remain matchable by that regex after .lower():
    #   - tags are space-joined raw frontmatter strings (slashes allowed, e.g. "domain/ml"
    #     — the regex will split on the slash, which is fine for retrieval)
    #   - concepts are emitted as "[[slug]] [[slug2]]"; the brackets are dropped
    #     by the regex and the slugs are preserved as tokens
    #   - summary only strips \t and \n so the TSV stays one-line-per-page
    # If you change the field set, the separator, or start pre-tokenizing here,
    # update wiki_search.parse_line() (fixed column count) and tokenize() in lock-step.
    search_lines: list[str] = []
    for slug, path in sorted(page_by_slug.items()):
        fm = page_fm.get(slug, {})
        title = fm.get("title", slug)
        tags = " ".join(fm.get("tags", []) or [])
        concepts = " ".join(f"[[{t}]]" for t in outbound.get(slug, []))
        summary = (fm.get("summary", "") or "").replace("\t", " ").replace("\n", " ")
        rel = str(path.relative_to(vault)).replace(os.sep, "/")
        search_lines.append(
            f"{rel}\t{title}\t{tags}\t{concepts}\t{summary}"
        )

    return {
        "backlinks": backlinks,
        "sources": sources,
        "search_lines": search_lines,
        "page_fm": page_fm,
        "page_by_slug": page_by_slug,
    }


def write_meta(vault: Path, built: dict) -> None:
    meta = vault / "wiki" / ".meta"
    meta.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(meta / "backlinks.json", built["backlinks"])
    _atomic_write_json(meta / "sources.json", built["sources"])
    _atomic_write_text(
        meta / "search-index.tsv",
        "\n".join(built["search_lines"]) + ("\n" if built["search_lines"] else ""),
    )


def _atomic_write_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _atomic_write_text(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


# --------------------------------------------------------------------------
# Drift check (for LINT / CI)
# --------------------------------------------------------------------------

def check_drift(vault: Path, built: dict) -> list[str]:
    """Return a list of human-readable drift messages. Empty list = clean."""
    drifts: list[str] = []
    nodes = built["backlinks"]["nodes"]
    for slug, node in nodes.items():
        if node["type"] not in {"concepts", "entities"}:
            continue
        fm = built["page_fm"].get(slug, {})
        fm_sc = fm.get("source_count")
        try:
            fm_sc_int = int(fm_sc) if fm_sc not in (None, "") else None
        except ValueError:
            fm_sc_int = None
        if fm_sc_int is not None and fm_sc_int != node["source_count"]:
            drifts.append(
                f"{node['path']}: source_count frontmatter={fm_sc_int} "
                f"actual={node['source_count']}"
            )
    return drifts


# --------------------------------------------------------------------------
# Embeddings (incremental)
# --------------------------------------------------------------------------

def _text_for_embedding(page_path: Path, fm: dict) -> str:
    """Return the text that represents this page for embedding purposes.

    Concatenates title, summary, tags, and the body (sans frontmatter),
    truncated to ~8000 chars. The sentence-transformer model will
    truncate further at its token limit; this cap keeps memory bounded
    on very long paper summaries.
    """
    import hashlib  # noqa
    try:
        raw = page_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    m = FRONTMATTER_RE.match(raw)
    body = raw[m.end():] if m else raw
    title = fm.get("title", "") or ""
    summary = fm.get("summary", "") or ""
    tags = fm.get("tags", []) or []
    tag_str = " ".join(tags) if isinstance(tags, list) else str(tags)
    combined = f"{title}\n{summary}\n{tag_str}\n\n{body}"
    return combined[:8000]


def _sha256(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_manifest(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            while len(parts) < 3:
                parts.append("")
            rows.append({"slug": parts[0], "path": parts[1], "sha256": parts[2]})
    return rows


def _write_manifest(path: Path, rows: list[dict]) -> None:
    lines = [f"{r['slug']}\t{r['path']}\t{r['sha256']}" for r in rows]
    _atomic_write_text(path, "\n".join(lines) + ("\n" if lines else ""))


def embed_pages(vault: Path, built: dict) -> tuple[int, int, int]:
    """Incremental embed of every page in built['page_by_slug'].

    Returns (total, reused, embedded). Requires numpy +
    sentence-transformers at call time.
    """
    try:
        import numpy as np
    except ImportError:
        raise ImportError("numpy not installed. Run: pip install numpy")

    sys.path.insert(0, str(vault / "scripts"))
    try:
        import semantic  # local
    except ImportError as e:
        raise ImportError(f"failed to import scripts/semantic.py: {e}")

    SentenceTransformer = semantic._import_st()  # raises with install hint if missing

    meta = vault / "wiki" / ".meta"
    meta.mkdir(parents=True, exist_ok=True)
    mat_path = meta / "embeddings.npy"
    man_path = meta / "embeddings-manifest.tsv"

    old_rows = _read_manifest(man_path)
    old_sha = {r["slug"]: r["sha256"] for r in old_rows}
    # allow_pickle=False: refuse arbitrary-object deserialization when
    # loading the embedding matrix during an unattended sidecar rebuild.
    old_matrix = np.load(mat_path, allow_pickle=False) if mat_path.exists() else None
    old_slug_to_idx = {r["slug"]: i for i, r in enumerate(old_rows)}

    page_fm = built["page_fm"]
    page_by_slug = built["page_by_slug"]

    new_rows: list[dict] = []
    reuse_idx: list[int] = []        # indices into old_matrix to reuse
    to_embed_texts: list[str] = []   # texts we need to embed fresh
    to_embed_rows: list[dict] = []   # manifest rows for the texts above

    for slug, path in sorted(page_by_slug.items()):
        fm = page_fm.get(slug, {})
        rel = str(path.relative_to(vault)).replace(os.sep, "/")
        text = _text_for_embedding(path, fm)
        sha = _sha256(text)
        row = {"slug": slug, "path": rel, "sha256": sha}
        if slug in old_sha and old_sha[slug] == sha and old_matrix is not None:
            reuse_idx.append(old_slug_to_idx[slug])
            new_rows.append(row)
        else:
            to_embed_rows.append(row)
            to_embed_texts.append(text)
            new_rows.append(row)

    # Compute fresh embeddings in one batch.
    model_name = os.environ.get("ZWIKI_EMBED_MODEL", semantic.DEFAULT_MODEL)
    model = SentenceTransformer(model_name)
    dim = model.get_sentence_embedding_dimension()

    if to_embed_texts:
        fresh = model.encode(
            to_embed_texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        ).astype(np.float32)
    else:
        fresh = np.zeros((0, dim), dtype=np.float32)

    # Assemble final matrix in the order of new_rows.
    matrix = np.zeros((len(new_rows), dim), dtype=np.float32)
    fresh_cursor = 0
    reuse_cursor = 0
    for i, row in enumerate(new_rows):
        if row["sha256"] == old_sha.get(row["slug"]) and old_matrix is not None:
            matrix[i] = old_matrix[old_slug_to_idx[row["slug"]]]
            reuse_cursor += 1
        else:
            matrix[i] = fresh[fresh_cursor]
            fresh_cursor += 1

    # Atomic writes. Use a binary handle so np.save does not auto-append
    # ".npy" to the tmp path (which would break the replace below).
    tmp = mat_path.with_suffix(mat_path.suffix + ".tmp")
    with open(tmp, "wb") as fh:
        np.save(fh, matrix)
    tmp.replace(mat_path)
    _write_manifest(man_path, new_rows)

    return len(new_rows), reuse_cursor, fresh_cursor


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=".", help="repo root containing wiki/")
    ap.add_argument("--check", action="store_true",
                    help="only report drift; do not write")
    ap.add_argument("--only", help="(reserved) incremental update for one page")
    ap.add_argument("--embed", action="store_true",
                    help="also compute/refresh embeddings (incremental)")
    ap.add_argument("--embed-if-enabled", action="store_true",
                    help="embed only if wiki/.meta/embeddings-manifest.tsv exists "
                         "(silent no-op otherwise). Used by commands so embeddings "
                         "stay fresh automatically once the user has opted in.")
    args = ap.parse_args()

    vault = Path(args.vault).resolve()
    if not (vault / "wiki").is_dir():
        print(f"error: no wiki/ under {vault}", file=sys.stderr)
        return 2

    built = build(vault)

    if args.check:
        drifts = check_drift(vault, built)
        if drifts:
            for d in drifts:
                print(d)
            print(f"\n{len(drifts)} drift(s)", file=sys.stderr)
            return 1
        print("clean")
        return 0

    write_meta(vault, built)
    pages = len(built["backlinks"]["nodes"])
    sources = len(built["sources"]["sources"])
    print(f"wrote wiki/.meta/: {pages} pages indexed, {sources} sources")

    manifest_exists = (vault / "wiki" / ".meta" / "embeddings-manifest.tsv").exists()
    do_embed = args.embed or (args.embed_if_enabled and manifest_exists)

    if do_embed:
        try:
            total, reused, fresh = embed_pages(vault, built)
            print(f"embeddings: {total} pages ({reused} reused, {fresh} re-embedded)")
        except ImportError as e:
            if args.embed:
                print(f"\nskipping --embed: {e}", file=sys.stderr)
                return 1
            # --embed-if-enabled: user opted in but deps vanished. Warn, keep going.
            print(f"\nwarning: embeddings enabled but {e.__class__.__name__}: {e}",
                  file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
