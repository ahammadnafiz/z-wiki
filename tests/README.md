# tests/ — invariant suite

Shell scripts that enforce filesystem invariants. Each script exits
zero on pass, non-zero on fail, and prints a one-line diagnostic per
violation.

Run the whole suite:

```bash
bash scripts/check_invariants.sh
```

Or a single test:

```bash
bash tests/test-unique-slugs.sh
```

## What is tested

| Test | Invariant |
|---|---|
| `test-wikilinks-resolve.sh` | Every `[[target]]` in page bodies resolves to a file in `wiki/`. |
| `test-unique-slugs.sh` | No two pages share a filename (Obsidian wikilink resolution requires this). |
| `test-kebab-case.sh` | Filenames are lowercase kebab-case ASCII. |
| `test-frontmatter.sh` | Every page starts with a YAML frontmatter block with required fields. |
| `test-source-path-unique.sh` | No two `wiki/sources/*.md` share the same `source_path:`. |
| `test-source-count.sh` | `source_count` in frontmatter matches the sidecar cache (drift check). |
| `test-index-size.sh` | `wiki/index.md` stays under the 10K-token threshold (forces sharding). |
| `test-meta-consistent.sh` | `wiki/.meta/*` is up-to-date with the filesystem. |

## Exit codes

- `0` — pass
- `1` — invariant violated
- `2` — test infrastructure error (missing `rg`, corrupt repo, etc.)

## Why shell, not pytest

Zero dependencies. These must run on any machine that has the vault
cloned. No venv, no install step. Python is used only for JSON
parsing via `python3 -c` one-liners, and `rg` is the grep
substrate — both are already required by the rest of the pipeline.
