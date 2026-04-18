---
description: Scaffold or repair the Fiz-Wiki file tree.
allowed-tools: Read, Write, Bash, Glob
---

# Wiki Init

Read `CLAUDE.md`. Verify the full directory tree listed there exists:

- `raw/{articles,papers,transcripts,assets}/`
- `wiki/{sources,concepts,entities,syntheses,outputs,attachments/images}/`
- `templates/`
- `docs/`

For any missing directory, create it with a `.gitkeep` file.
For any missing `_index.md`, create it from the template shown in `CLAUDE.md`.
For any missing template in `templates/` (expected: `source-summary.md`, `paper-summary.md`, `concept.md`, `entity.md`, `synthesis.md`, `output.md`, `stub.md`), tell me — do not invent one.

Do not touch `.obsidian/`, `.git/`, or `.claude/`.

Report:
- Directories created: N
- Index files created: N
- Templates missing (flag for me): list
