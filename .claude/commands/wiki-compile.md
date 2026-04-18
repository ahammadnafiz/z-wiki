---
description: Rebuild wiki/index.md from the filesystem.
allowed-tools: Read, Write, Bash, Glob
---

# Wiki Compile

Read `CLAUDE.md` for conventions. Follow the COMPILE operation exactly as specified there.

1. Enumerate every file in `wiki/sources/`, `wiki/concepts/`, `wiki/entities/`, `wiki/syntheses/`, `wiki/outputs/`.
2. Pull the `title` and `summary` from each file's frontmatter.
3. Regenerate `wiki/index.md` in sectioned order: Overview counts → Sources → Concepts → Entities → Syntheses → Outputs → Recently Added (last 10 by `date_modified`).
4. Append one `compile` entry to `wiki/log.md` with the counts.
5. Do not touch any page body.

Report: counts per section, and the list of files that lacked a usable `title` or `summary` (these are lint targets).
