---
description: Health-check the wiki.
allowed-tools: Read, Write, Edit, Bash, Glob, Grep
---

# Wiki Lint

Read `CLAUDE.md` for conventions. Follow the LINT operation exactly as specified there.

## Auto-fix without asking
- Missing or malformed frontmatter (add required fields, preserve existing values).
- Broken `[[wikilinks]]` → create stubs from `templates/stub.md`.
- Filenames not in kebab-case → rename the file and update every inbound reference.
- Two pages describing the same subject under different names → merge, keeping the more common name.
- `source_count` on concept/entity pages → recount as the number of `wiki/sources/*.md` files that link to the page; update in-place.
- `wiki/views/**/*.base` YAML validity (per `.claude/skills/obsidian-bases/SKILL.md`): valid YAML; every `formula.X` referenced in `order`/`properties` is defined in `formulas`; filter-quoting rules observed; Duration math uses `.days`/`.hours` before arithmetic.
- `wiki/canvases/**/*.canvas` JSON validity (per `.claude/skills/json-canvas/SKILL.md`): parseable JSON; unique IDs across nodes+edges; every `fromNode`/`toNode` resolves to an existing node; required per-type fields present; valid `type`/`fromSide`/`toSide`/`fromEnd`/`toEnd` values.

## Do not auto-fix — report instead
- Contradictions between pages (list both sides).
- Orphan pages (no inbound `[[wikilinks]]` after checking every file).
- Stale content (source > 6 months old, no updates since).
- Concepts referenced ≥3 times across the wiki but lacking a dedicated page.

## Output
- `wiki/outputs/lint-report-{today}.md` from `templates/output.md` (type: output), with sections: Auto-fixed / Needs my attention / Suggested next sources / Suggested next questions.
- Update `wiki/index.md` and append to `wiki/log.md`.
