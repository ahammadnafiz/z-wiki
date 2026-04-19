#!/usr/bin/env bash
# If embeddings exist, verify they are consistent with the vault:
#   - manifest row count matches .npy row count
#   - every manifest slug exists in wiki/.meta/backlinks.json
#   - every backlinks slug appears in the manifest (no missing pages)
#   - vectors are L2-normalized (norms close to 1.0)
#
# If no embeddings exist, this test passes silently — semantic search
# is optional.
set -u
cd "$(dirname "$0")/.."

MAT=wiki/.meta/embeddings.npy
MAN=wiki/.meta/embeddings-manifest.tsv
BL=wiki/.meta/backlinks.json

if [ ! -f "$MAT" ] && [ ! -f "$MAN" ]; then
  exit 0
fi

if [ ! -f "$MAT" ] || [ ! -f "$MAN" ]; then
  echo "inconsistent: one of $MAT / $MAN is present, the other is not"
  echo "run: python3 scripts/build_meta.py --embed"
  exit 1
fi

python3 - <<'PY' || exit 1
import json, sys
from pathlib import Path

vault = Path(".")
mat_path = vault / "wiki/.meta/embeddings.npy"
man_path = vault / "wiki/.meta/embeddings-manifest.tsv"
bl_path = vault / "wiki/.meta/backlinks.json"

try:
    import numpy as np
except ImportError:
    # numpy not installed but embeddings exist → cannot verify shape.
    # Treat as a warning, not failure — lets the test pass on systems
    # without the optional deps.
    print("warning: numpy missing; cannot verify embedding shape (skipping)")
    sys.exit(0)

matrix = np.load(mat_path)

manifest_slugs = []
with man_path.open() as f:
    for line in f:
        line = line.rstrip("\n")
        if not line:
            continue
        parts = line.split("\t")
        manifest_slugs.append(parts[0])

fail = False

if matrix.shape[0] != len(manifest_slugs):
    print(f"row mismatch: .npy has {matrix.shape[0]} rows, manifest has {len(manifest_slugs)}")
    fail = True

if not bl_path.exists():
    print("missing wiki/.meta/backlinks.json — run python3 scripts/build_meta.py")
    sys.exit(1)

backlinks = json.load(bl_path.open())
bl_slugs = set(backlinks.get("nodes", {}).keys())
man_set = set(manifest_slugs)

missing_from_manifest = bl_slugs - man_set
extra_in_manifest = man_set - bl_slugs
if missing_from_manifest:
    print(f"{len(missing_from_manifest)} page(s) missing from embeddings manifest:")
    for s in sorted(missing_from_manifest)[:5]:
        print(f"  {s}")
    fail = True
if extra_in_manifest:
    print(f"{len(extra_in_manifest)} stale slug(s) in embeddings manifest:")
    for s in sorted(extra_in_manifest)[:5]:
        print(f"  {s}")
    fail = True

# Norm check on a sample (checking all would be slow on large vaults).
if matrix.shape[0] > 0:
    sample = matrix if matrix.shape[0] <= 100 else matrix[:100]
    norms = np.linalg.norm(sample, axis=1)
    bad = ((norms < 0.99) | (norms > 1.01)).sum()
    if bad > 0:
        print(f"{int(bad)} sampled vectors are not L2-normalized (expected ~1.0)")
        fail = True

if fail:
    print("\nrun: python3 scripts/build_meta.py --embed")
    sys.exit(1)
PY
