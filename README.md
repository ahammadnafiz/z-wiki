# z-wiki

A zero-content starter for building a personal, LLM-maintained knowledge wiki with Claude Code.

Clone → open as an Obsidian vault → drop sources into `raw/` → run `/wiki-ingest`. Ask questions with `/wiki-query`; every answer is filed back, so the wiki compounds with use.

## What this is

A three-layer pattern on disk:

| Layer | What's in it | Who owns it |
|---|---|---|
| `raw/` | Source material you drop in (articles, papers, transcripts) | **You** — immutable once placed |
| `wiki/` | LLM-authored pages (summaries, concepts, entities, syntheses, outputs) | **Claude Code** |
| `CLAUDE.md` | The spec that tells Claude how to write and maintain `wiki/` | **Both** — co-evolved |

Four operations cycle continuously:

1. **`/wiki-ingest`** — you drop a source; Claude writes a summary and updates concept/entity pages.
2. **`/wiki-query`** — you ask a question; Claude searches the wiki and files the answer back.
3. **`/wiki-lint`** — Claude audits the wiki for broken links, orphans, drift.
4. **`/wiki-compile`** — Claude regenerates `wiki/index.md` from the filesystem.

The **filing loop** is the point: every answer becomes a new wiki page that future queries can cite. Knowledge compounds.

## What this is not

- **Not a pre-built knowledge base.** This repo ships with zero content. You bring the sources; the agent compiles them into your wiki.
- **Not a search engine.** No embeddings, no vector store at the default scale. Navigation is by a single `wiki/index.md` plus wikilinks. Designed for ~tens-to-hundreds of sources; scaling paths are documented.
- **Not a replacement for reading.** The wiki is a compounding synthesis of what you've already read — it's how the agent remembers your reading so future work builds on it.

## Prerequisites

- [Obsidian](https://obsidian.md) ≥ 1.4 — reading/editing surface (MathJax, Properties, graph view)
- [Claude Code](https://claude.ai/download) — the agent that runs the slash commands listed below
- `git` — history; nothing works without it
- Optional: `defuddle` (`npm install -g defuddle`) — clean web-page extraction

macOS and Linux paths are assumed. Windows should work via WSL.

## Quickstart

```bash
git clone <this-repo-url> my-wiki
cd my-wiki
```

1. Open the folder as an Obsidian vault (File → Open folder as vault).
2. Start a Claude Code session in the vault directory: `claude`.
3. Run `/wiki-init`. The first time you run it, Claude asks about your topic conversationally and writes it into `CLAUDE.md` → Overview. Every subsequent run just verifies/repairs the directory tree.
4. Add a source:
   - **From a URL:** `/wiki-add https://some.url/article` — Claude fetches it, writes to `raw/articles/`, and offers to ingest immediately.
   - **From disk:** `/wiki-add /path/to/file.pdf` — Claude copies it to the right `raw/` subfolder.
   - **Manually:** drop a markdown file into `raw/articles/`, `raw/papers/`, or `raw/transcripts/` and run `/wiki-ingest`.
5. Ask a question: `/wiki-query What's the key claim in this source?` — Claude answers with wikilink citations and files the answer under `wiki/outputs/`.
6. Repeat. Add more sources. Ask more questions. Run `/wiki-status` any time for a quick vault summary. Weekly or so, run `/wiki-lint` to keep the wiki healthy.

## Slash commands

| Command | What it does |
|---|---|
| `/wiki-init` | First-run: asks about your topic, writes it into CLAUDE.md. Re-runs: verifies/repairs directory structure. |
| `/wiki-add <url-or-path>` | Fetches a URL (or copies a file) into the right `raw/` subfolder and offers to ingest. |
| `/wiki-ingest [path]` | Compiles `raw/` into wiki pages (summaries, concepts, entities, stubs). |
| `/wiki-query <question>` | Answers using only the compiled wiki; files the answer under `wiki/outputs/`. |
| `/wiki-status` | One-screen vault summary — counts, stubs-near-promotion, recent activity. |
| `/wiki-lint` | Weekly health check — auto-fixes what's fixable, reports the rest. |
| `/wiki-compile` | Regenerates `wiki/index.md` from the filesystem. |
| `/wiki-new-template <name>` | Scaffolds a new template for a new kind of source, wires it into CLAUDE.md. |

## Learn more

- **[docs/GUIDE.md](docs/GUIDE.md)** — step-by-step walkthroughs for every operation, file conventions, troubleshooting.
- **`CLAUDE.md`** — the operating spec. Claude loads this on every session.
- **`.claude/commands/`** — the eight slash commands above.
- **`templates/`** — the page templates Claude follows when creating wiki pages.

## Background and credit

The pattern is adapted from two sources:

- **Andrej Karpathy** — ["LLM knowledge bases"](https://x.com/karpathy/). The original raw-sources → compiled-wiki → query → file-back architecture.
- **Shann Holmberg** — ["The AI Knowledge Layer"](https://x.com/shannholmberg/). The framing as agent infrastructure and the two-layer (knowledge base + brand foundation) extension.

This repo is the minimal template — schema, templates, slash commands, scaffolding — so anyone can clone and run it without inheriting someone else's content.

## License

MIT. See [LICENSE](LICENSE).

The vendored Obsidian skills under `.claude/skills/` are from [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills), also MIT-licensed. See [docs/obsidian-skills-provenance.md](docs/obsidian-skills-provenance.md) for provenance.
