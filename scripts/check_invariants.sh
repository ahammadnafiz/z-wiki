#!/usr/bin/env bash
# Run every test in tests/*.sh. Exits non-zero on the first failure.
# Zero deps beyond bash + rg + python3.

set -u  # undefined vars are errors, but do NOT exit on test failure (we count them)

cd "$(dirname "$0")/.."

pass=0
fail=0
failures=()

for t in tests/*.sh; do
  [ -f "$t" ] || continue
  name=$(basename "$t" .sh)
  printf "%-40s " "$name"
  if bash "$t" >/tmp/z-wiki-$$.out 2>&1; then
    echo "PASS"
    pass=$((pass + 1))
  else
    echo "FAIL"
    failures+=("$name")
    echo "---"
    sed 's/^/    /' /tmp/z-wiki-$$.out
    echo "---"
    fail=$((fail + 1))
  fi
done

rm -f /tmp/z-wiki-$$.out

echo
echo "passed: $pass  failed: $fail"

if [ "$fail" -gt 0 ]; then
  echo "failed tests: ${failures[*]}"
  exit 1
fi
exit 0
