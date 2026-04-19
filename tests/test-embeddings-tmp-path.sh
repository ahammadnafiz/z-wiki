#!/usr/bin/env bash
# Regression: np.save must write to the exact tmp path we gave it.
#
# Bug fixed in 12c341a: np.save auto-appends .npy when passed a Path whose
# suffix is not already .npy. Passing Path("embeddings.npy.tmp") created
# embeddings.npy.tmp.npy on disk, so the subsequent tmp.replace(mat_path)
# found nothing to rename and silently lost the refresh.
#
# This test exercises the embed path (if sentence-transformers is available)
# and asserts no stray .npy.tmp* files remain in wiki/.meta/.
set -u
cd "$(dirname "$0")/.."

# Skip silently if optional deps (numpy / sentence-transformers) aren't installed.
python3 - <<'PY' 2>/dev/null || { exit 0; }
import numpy  # noqa
import sentence_transformers  # noqa
PY

python3 scripts/build_meta.py --embed-if-enabled >/dev/null 2>&1 || {
  echo "build_meta --embed-if-enabled failed"
  exit 1
}

strays=$(find wiki/.meta -maxdepth 1 -name 'embeddings.npy.tmp*' 2>/dev/null || true)
if [ -n "$strays" ]; then
  echo "stray tmp files left after embed rebuild (np.save tmp-path regression):"
  echo "$strays"
  exit 1
fi
exit 0
