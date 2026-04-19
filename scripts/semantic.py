#!/usr/bin/env python3
"""Local semantic search over wiki/.meta/embeddings.npy.

Loads a precomputed float32 embedding matrix + a manifest TSV and
returns ranked results by cosine similarity. Vectors are L2-normalized
at write time (see build_meta.py --embed), so ranking is a dot product.

Designed to be invoked from wiki_search.py's --semantic path. Also
usable standalone for debugging.

Requires sentence-transformers at query time (to embed the query
itself). If the library is missing, search() raises ImportError with
an install hint; wiki_search.py catches this and falls back to
keyword search.

Storage:
    wiki/.meta/embeddings.npy             float32 [N, 384]  L2-normalized
    wiki/.meta/embeddings-manifest.tsv    slug \\t path \\t text_sha256

Model:
    sentence-transformers/all-MiniLM-L6-v2  (default; 384-dim, ~90MB)

Environment overrides:
    ZWIKI_EMBED_MODEL — model name (default: all-MiniLM-L6-v2)
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _import_np():
    try:
        import numpy as np  # noqa
        return np
    except ImportError as e:
        raise ImportError(
            "numpy required. Install with: pip install numpy"
        ) from e


def _import_st():
    try:
        from sentence_transformers import SentenceTransformer  # noqa
        return SentenceTransformer
    except ImportError as e:
        raise ImportError(
            "sentence-transformers not installed. "
            "Install: pip install sentence-transformers\n"
            "(or skip semantic search; keyword search remains available)"
        ) from e


_MODEL_CACHE: dict = {}


def get_model(model_name: str | None = None):
    name = model_name or os.environ.get("ZWIKI_EMBED_MODEL", DEFAULT_MODEL)
    if name not in _MODEL_CACHE:
        SentenceTransformer = _import_st()
        _MODEL_CACHE[name] = SentenceTransformer(name)
    return _MODEL_CACHE[name]


def load_index(vault: Path):
    """Return (matrix, manifest_rows) or (None, []) if missing."""
    np = _import_np()
    meta = vault / "wiki" / ".meta"
    mat_path = meta / "embeddings.npy"
    man_path = meta / "embeddings-manifest.tsv"
    if not mat_path.exists() or not man_path.exists():
        return None, []
    matrix = np.load(mat_path)
    rows: list[dict] = []
    with man_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            while len(parts) < 3:
                parts.append("")
            rows.append({
                "slug": parts[0],
                "path": parts[1],
                "sha256": parts[2],
            })
    if matrix.shape[0] != len(rows):
        raise RuntimeError(
            f"embedding matrix ({matrix.shape[0]}) does not match "
            f"manifest rows ({len(rows)}); run `python3 scripts/build_meta.py --embed`"
        )
    return matrix, rows


def embed_query(text: str, model_name: str | None = None):
    """Return a L2-normalized float32 vector for the query text."""
    np = _import_np()
    model = get_model(model_name)
    vec = model.encode([text], normalize_embeddings=True, convert_to_numpy=True)
    return vec[0].astype(np.float32)


def search(
    query: str,
    *,
    vault: Path,
    limit: int = 10,
    type_filter: str | None = None,
    tag_filter: str | None = None,
) -> list[dict]:
    """Return a ranked list of {path, title, tags, score, summary}.

    Caller passes raw query text; this function embeds it, dot-products
    against the stored matrix, and filters/ranks. type_filter and
    tag_filter are honored by post-filtering against the TSV search
    index (same convention as wiki_search.py keyword path).
    """
    np = _import_np()
    matrix, rows = load_index(vault)
    if matrix is None:
        return []

    q = embed_query(query)
    scores = matrix @ q  # cosine (both L2-normalized)

    # Join against wiki/.meta/search-index.tsv to pull titles / tags / summaries.
    tsv = vault / "wiki" / ".meta" / "search-index.tsv"
    meta_by_path: dict[str, dict] = {}
    if tsv.exists():
        with tsv.open("r", encoding="utf-8") as f:
            for line in f:
                parts = line.rstrip("\n").split("\t")
                while len(parts) < 5:
                    parts.append("")
                meta_by_path[parts[0]] = {
                    "title": parts[1],
                    "tags": parts[2],
                    "summary": parts[4],
                }

    hits: list[tuple[float, dict]] = []
    for i, row in enumerate(rows):
        path = row["path"]
        if type_filter and f"/{type_filter}/" not in path:
            continue
        meta = meta_by_path.get(path, {})
        if tag_filter:
            tag_tokens = set(meta.get("tags", "").lower().split())
            if tag_filter.lower() not in tag_tokens:
                continue
        hits.append((
            float(scores[i]),
            {
                "path": path,
                "slug": row["slug"],
                "title": meta.get("title", row["slug"]),
                "tags": [t for t in meta.get("tags", "").split() if t],
                "summary": meta.get("summary", ""),
            },
        ))

    hits.sort(key=lambda x: (-x[0], x[1]["path"]))
    out: list[dict] = []
    for s, h in hits[:limit]:
        out.append({**h, "score": round(s, 4)})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("query", nargs="+")
    ap.add_argument("--vault", default=".")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--type", dest="type_filter")
    ap.add_argument("--tag", dest="tag_filter")
    args = ap.parse_args()

    vault = Path(args.vault).resolve()
    try:
        results = search(
            " ".join(args.query),
            vault=vault,
            limit=args.limit,
            type_filter=args.type_filter,
            tag_filter=args.tag_filter,
        )
    except ImportError as e:
        print(str(e), file=sys.stderr)
        return 2

    if not results:
        print("no matches (or embeddings not built — run `python3 scripts/build_meta.py --embed`)")
        return 0
    for r in results:
        tag_str = " ".join(f"#{t}" for t in r["tags"]) if r["tags"] else ""
        summary = (r.get("summary", "") or "")
        if len(summary) > 140:
            summary = summary[:137] + "..."
        print(f"{r['score']:>6.3f}  {r['path']}")
        print(f"         {r['title']}  {tag_str}".rstrip())
        if summary:
            print(f"         {summary}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
