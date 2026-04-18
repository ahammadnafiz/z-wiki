# obsidian-skills — provenance

This repo ships the official Obsidian Agent Skills from Steph Ango (kepano, Obsidian's CEO), vendored under `.claude/skills/` so every Claude Code session in this vault auto-discovers them.

## Source

- **Upstream:** https://github.com/kepano/obsidian-skills
- **Vendored version:** 1.0.1 (matches `.claude-plugin/plugin.json` in the source tree at time of copy)
- **License:** MIT (upstream)
- **Vendored on:** 2026-04-18

## What was copied and where

| Upstream path | Vendored path |
|---|---|
| `skills/obsidian-markdown/` | `.claude/skills/obsidian-markdown/` |
| `skills/obsidian-bases/` | `.claude/skills/obsidian-bases/` |
| `skills/json-canvas/` | `.claude/skills/json-canvas/` |
| `skills/obsidian-cli/` | `.claude/skills/obsidian-cli/` |
| `skills/defuddle/` | `.claude/skills/defuddle/` |

Only the `skills/` subtree is vendored. The upstream `.claude-plugin/`, marketplace wiring, and README are not — they're Obsidian marketplace plumbing that doesn't apply to a plain-skills-folder install.

## Why vendored instead of installed via plugin marketplace

- **Version-pinned.** Upstream updates can't silently change our workflow. If we want the next version, we re-copy deliberately.
- **Offline.** No marketplace dependency at session start.
- **Reviewable.** Every skill file is in our git history; any change to Claude's behaviour is reviewable via normal diff workflow.

## How to update

1. Clone upstream: `git clone https://github.com/kepano/obsidian-skills.git /tmp/obsidian-skills`
2. Diff against our vendored copy: `diff -r /tmp/obsidian-skills/skills .claude/skills`
3. Review changes. Cherry-pick or replace wholesale.
4. Bump the "Vendored version" field above.
5. Commit.

## How these skills interact with `CLAUDE.md`

`CLAUDE.md` was updated when these were vendored to:
- Lift the blanket ban on Canvas / Bases.
- Introduce scoped rules: plain markdown in the core wiki tree, Bases allowed in `wiki/views/`, Canvas allowed in `wiki/canvases/`.
- Prefer `defuddle` over `WebFetch` for standard web pages (WebFetch still right for GitHub, arXiv HTML, raw markdown URLs).

See `CLAUDE.md` → "Skill references" and "Things you must not do" for current rules.
