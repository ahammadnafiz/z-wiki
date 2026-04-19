<div align="center">

<img src="assets/hero.png" alt="z-wiki" width="600">

# z-wiki

**A personal, LLM-maintained knowledge wiki template for Claude Code.**

*Clone → drop sources → ask questions → watch knowledge compound.*

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Claude Code](https://img.shields.io/badge/powered_by-Claude_Code-8A2BE2.svg)](https://claude.ai/code)
[![Obsidian](https://img.shields.io/badge/vault-Obsidian-7C3AED.svg)](https://obsidian.md)
[![Status: beta](https://img.shields.io/badge/status-beta-orange.svg)](#status)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contributing)

</div>

---

## Why

Most notes rot. You read, you highlight, you forget. RAG systems over raw documents re-derive answers from scratch every query; nothing persists, nothing compounds.

**z-wiki flips that.** An LLM agent (Claude Code) reads your sources once, compiles them into a cross-referenced markdown wiki, and saves every answered question back as a new page. The next query has strictly more to work with. The vault appreciates with use, not just with ingestion.

Inspired by [Andrej Karpathy's LLM knowledge bases](https://x.com/karpathy/) and [Shann Holmberg's AI knowledge layer](https://x.com/shannholmberg/). Zero content bundled — you bring the sources.

---

## How it works

```
                  ┌──────────────────────────────┐
                  │   CLAUDE.md  (operating spec)│
                  └──────────────┬───────────────┘
                                 │  loaded every session
        ┌───────────────┐        ▼        ┌────────────────┐
        │     raw/      │    ┌───────┐    │     wiki/      │
        │ articles,     │───▶│Claude │───▶│ sources,       │
        │ papers,       │    │ Code  │    │ concepts,      │
        │ transcripts   │    └───┬───┘    │ entities,      │
        │ (you own)     │        │        │ outputs        │
        └───────────────┘        │        │ (Claude owns)  │
               ▲                 │        └────────┬───────┘
               │                 │                 │
               │ /wiki-add       │ /wiki-query     │ filing loop
               │                 ▼                 │
               │         ┌───────────────┐         │
               └─────────│ your question │◀────────┘
                         └───────────────┘
```

**Three layers, six core operations:**

| Layer | Contents | Owner |
|---|---|---|
| `raw/` | Source material you drop in (articles, papers, transcripts) | **You** — immutable once placed |
| `wiki/` | LLM-authored summaries, concepts, entities, outputs + generated sidecar (`.meta/`) and index shards (`indexes/`) | **Claude Code** |
| `CLAUDE.md` | The spec that controls how Claude writes `wiki/` | **Both** — co-evolved |

- **`/wiki-ingest`** — compile raw into wiki pages with cross-referenced wikilinks
- **`/wiki-query`** — answer questions from the wiki; file the answer back as a new page
- **`/wiki-lint`** — audit the wiki for broken links, drift, promotion candidates
- **`/wiki-compile`** — rebuild the master index and sidecar cache from the filesystem
- **`/wiki-promote`** — graduate stubs that crossed promotion thresholds (user-gated)
- **`/wiki-search`** — grep-first (or hybrid) ranked search; read-only browse primitive

The **filing loop** — every answered query saved back as a citable page — is what makes knowledge compound. The **sidecar cache + sharded index** keep every operation's cost bounded regardless of vault size. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the system design.

---

## Quickstart

```bash
git clone https://github.com/<your-username>/z-wiki.git my-wiki
cd my-wiki
claude
```

Then, inside Claude Code:

```
/wiki-init                                    # 1. Interactive topic setup
/wiki-add https://some.url/article            # 2. Fetch + place a source
/wiki-ingest                                  # 3. Compile into wiki pages
/wiki-query what does source X argue?         # 4. Ask a question, get a cited answer
/wiki-status                                  # 5. Quick vault summary
```

Open the folder as an Obsidian vault to browse the graph and read pages.

---

## Example session

After ingesting a single paper (e.g., Ongaro 2014's Raft paper), this is what `/wiki-query` produces:

```
> /wiki-query what does Raft solve that Paxos struggled with?

Reading wiki/index.md... shortlisting candidates
Reading wiki/sources/ongaro-2014-raft.md
Reading wiki/concepts/paxos.md
Reading wiki/concepts/leader-election.md

Short answer:
Not correctness, not efficiency — implementability. Paxos and Raft
produce equivalent guarantees at comparable cost. What Raft solves
is that Paxos's presentation left too many corner cases, so
implementations consistently diverged from the published algorithm.
Raft's decomposition and structural constraints collapse that space.

Sources: [[ongaro-2014-raft]], [[paxos]], [[leader-election]]
→ Filed as wiki/outputs/what-does-raft-solve-that-paxos-struggled-with.md
```

The filed answer joins the wiki. The next related query cites it.

---

## Features

- 🗂  **Plain-markdown substrate.** Core storage is `.md` + YAML frontmatter. Renders on GitHub, portable forever.
- 🔗 **Cross-referenced wikilinks.** Every concept and entity gets its own page; Obsidian's graph view shows the emergent structure.
- 🧠 **Compiled, not retrieved.** Sources are read once and compiled into summaries + concept + entity pages. Queries run against the compiled wiki, not raw documents.
- ♾  **Filing loop.** Every answered query is saved as a wiki page the next query can cite. Knowledge compounds with use.
- 🔍 **Grep-first search, hybrid-optional.** Lexical BM25 always available (zero deps). `/wiki-enable-semantic` flips on local embeddings + hybrid search with Reciprocal Rank Fusion in one command. Never a vector DB, never a hosted service.
- ⚡ **Sidecar cache + sharded index.** `wiki/.meta/` and `wiki/indexes/` keep per-query cost bounded regardless of vault size. Scales to thousands of pages on a laptop.
- 🧵 **Subagent dispatch for batch ingest.** Batches of 3+ sources fan out one subagent per source. Parent context stays thin; ingest scales without context rot.
- 🛡 **11 invariant tests.** Broken links, drifted counts, kebab-case, bounded index size, fabrication in outputs, embedding consistency, idempotent ingest. Shell-only, zero-deps.
- 🎯 **User-gated stub promotion.** `/wiki-promote` graduates stubs on explicit command — cost of LLM-generated full pages stays visible.
- ⚠️  **Contradiction callouts.** When sources disagree, Claude inserts an inline `> [!warning]` callout citing both sides. Never silently reconciles.
- 🕐 **`last_seen` freshness.** Every page tracks the last date any operation substantively read, cited, or wrote it. Stale content surfaces in lint reports.
- 🔌 **Six vendored skills.** Five Obsidian (`obsidian-markdown`, `obsidian-bases`, `json-canvas`, `obsidian-cli`, `defuddle`) + one project-local (`context-engineering`). Auto-discovered by Claude Code.
- 🧩 **Extensible.** `/wiki-new-template` scaffolds new source-type templates and wires them in. Swap embedding model via `ZWIKI_EMBED_MODEL`. Graduate to faiss when numpy gets slow (swap path documented).

---

## What this is NOT

Setting expectations explicitly:

- **Not a pre-built knowledge base.** Zero content bundled. You bring the sources.
- **Not a hosted service.** Runs locally against your Claude Code subscription. Your data never leaves your disk unless you push it.
- **Not a vector DB.** Core retrieval is grep-first lexical; semantic is opt-in, local-only (numpy dot-product over ≤90MB sentence-transformers model). No Postgres, no pgvector, no cloud.
- **Not a replacement for reading.** It compounds what you've *already read* — doesn't let you skip reading.
- **Not a chat interface.** Every query produces a filed, cited, durable answer — not ephemeral conversation.
- **Not tuned for 100,000+ pages.** The numpy dot-product ceiling sits around ~50K pages on a laptop. Past that, swap to faiss (path documented in [`docs/DEFERRED.md`](docs/DEFERRED.md)).

---

## Slash commands

**Core lifecycle** (the six canonical operations):

| Command | What it does |
|---|---|
| `/wiki-ingest [path]` | Compile new files from `raw/` into wiki pages |
| `/wiki-query <question>` | Answer a question from the compiled wiki, file the answer back |
| `/wiki-lint` | Audit the wiki; auto-fix what's fixable, report the rest |
| `/wiki-compile` | Regenerate sidecar cache + sharded index from the filesystem |
| `/wiki-promote [slug\|--list\|--all]` | Graduate stubs that crossed promotion thresholds (user-gated) |
| `/wiki-search <query>` | Grep-first ranked search; read-only browse primitive |

**Helpers** (quality-of-life commands):

| Command | What it does |
|---|---|
| `/wiki-init` | First-run: topic-setup wizard + directory scaffold. Re-runs: verification only. |
| `/wiki-add <url-or-path>` | Fetch a URL or copy a file into `raw/`; optionally ingest immediately |
| `/wiki-status` | Read-only vault summary — counts, stubs near promotion, recent activity |
| `/wiki-enable-semantic` | One-shot opt-in for local hybrid retrieval (installs deps, builds embeddings, verifies) |
| `/wiki-new-template <name>` | Scaffold a new template and wire it into the ingest pipeline |

All 11 commands read `CLAUDE.md` first. None of them touch `raw/` existing files. Only `/wiki-init`, `/wiki-add`, and `/wiki-new-template` may write to `CLAUDE.md` or create new files in `raw/`.

---

## Installation

**Prerequisites:**

| Tool | Version | Purpose |
|---|---|---|
| [Claude Code](https://claude.ai/code) | any recent | Runs the slash commands |
| [Obsidian](https://obsidian.md) | ≥ 1.4 | Reading surface (MathJax, graph view, Properties) |
| Python 3 | ≥ 3.10 | `scripts/*.py` — pre-installed on macOS/Linux |
| `git` | any | History and multi-machine sync |
| `defuddle` *(optional)* | any | Clean web-page extraction; `npm install -g defuddle` |
| `markitdown` *(optional)* | any | PDF/DOCX/PPTX extraction; `pip install 'markitdown[all]'` |
| `numpy` + `sentence-transformers` *(optional)* | latest | Local hybrid retrieval; installed by `/wiki-enable-semantic` |

**Install:**

```bash
git clone https://github.com/<your-username>/z-wiki.git my-wiki
cd my-wiki
```

Open the folder in Obsidian (**File → Open folder as vault**). Start a Claude Code session in the vault root (`claude`). Run `/wiki-init`.

macOS and Linux paths are assumed. Windows works via WSL.

---

## Documentation

- **[docs/GUIDE.md](docs/GUIDE.md)** — step-by-step walkthroughs, file conventions, troubleshooting, graduation discipline
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — system design: sidecar cache, sharded index, retrieval ladder, context engineering, extension points
- **[docs/DEFERRED.md](docs/DEFERRED.md)** — deliberately-deferred work with trigger conditions (batched markitdown, faiss swap, chapter splitter, etc.)
- **[CLAUDE.md](CLAUDE.md)** — the operating spec (loaded into every Claude Code session)
- **[.claude/commands/](.claude/commands/)** — the 11 slash commands
- **[.claude/skills/context-engineering/](.claude/skills/context-engineering/SKILL.md)** — project-local skill: subagent dispatch, `/rewind` vs `/compact` vs `/clear`, prompt-cache structure
- **[scripts/README.md](scripts/README.md)** — tooling reference (build_meta, shard_index, wiki_search, semantic, check_extraction)
- **[tests/README.md](tests/README.md)** — 11 invariants and what each guards
- **[templates/](templates/)** — the seven page templates Claude follows when creating wiki pages
- **[docs/obsidian-skills-provenance.md](docs/obsidian-skills-provenance.md)** — provenance of the five vendored Obsidian skills

---

## Status

**Beta.** The six core operations (ingest / query / lint / compile / promote / search) and five helpers are implemented. Scripts layer has 11 invariant tests passing; synthetic fixture tests confirm the sidecar + sharding + hybrid-search paths work end-to-end. First real-world dogfooding of the scaled architecture is in progress — surfaces will bite before they don't.

Known limits:

- **numpy dot-product ceiling** around ~50K pages. Queries become noticeably slow past that point; swap path to faiss documented in [`docs/DEFERRED.md`](docs/DEFERRED.md).
- **Subagent-based INGEST** benefits from Claude Code's Agent tool being reliable. Heavy batches (>20 sources) should be split into multiple commands until the subagent pattern is stress-tested at scale.
- **markitdown subprocess overhead** (~200–500 ms per file) is noticeable past ~30 sources per batch. Parallelization pattern documented in [`docs/DEFERRED.md`](docs/DEFERRED.md).
- **Windows is WSL-only.** Path handling assumes POSIX.

If you hit an edge case, [open an issue](../../issues). If a template doesn't fit your source type, use `/wiki-new-template` or propose one via a PR.

---

## Roadmap

Shipped in the scale-architecture pass (see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)):

- [x] **Sharded index** — `wiki/index.md` stays <1K tokens; per-type and per-tag shards auto-split at 10K-token cap
- [x] **Sidecar cache** — `wiki/.meta/` kills O(N²) post-pass recomputation
- [x] **Hybrid search** — lexical (BM25) + local semantic (sentence-transformers) merged via RRF; opt-in via `/wiki-enable-semantic`
- [x] **Subagent INGEST dispatch** — parent context stays thin at batch scale
- [x] **Invariant test suite** — 11 shell tests; fabrication, drift, idempotency, embedding consistency

Deferred with documented trigger conditions ([`docs/DEFERRED.md`](docs/DEFERRED.md)):

- [ ] **Batched markitdown extraction** — unlock when batch ingest feels slow before LLM work starts
- [ ] **Automated chapter splitter for >200K-token books** — unlock when 3+ books have gone through the manual flow
- [ ] **Operation-semantics LLM round-trip tests** — unlock when vault has >20 real sources and a production regression bites
- [ ] **faiss swap for numpy dot-product** — unlock when `scripts/semantic.py` consistently takes >100ms
- [ ] **Query expansion (Haiku → 2 alt phrasings → RRF merge)** — unlock when semantic recall feels weak on natural-language queries
- [ ] **Confidence scoring / supersession** — unlock when ≥5 pages have open contradictions > 2 weeks
- [ ] **Knowledge-graph layer** — unlock when ≥3 queries/week need typed-edge graph traversal

---

## Contributing

Contributions welcome — especially from people running z-wiki on their own vault and hitting sharp edges.

**Good first PRs:**
- New templates for source types not covered (voice memos, meeting minutes, research interviews)
- Troubleshooting entries in `docs/GUIDE.md` §12
- Documentation fixes or clarifications
- Bug fixes to slash-command behavior

**Before you PR:**

1. Open an issue first for anything larger than a doc/typo fix — lets us align on scope before you spend time.
2. Run the changed commands against a scratch vault (not your real one). End-to-end smoke test at minimum: `/wiki-init` → `/wiki-add` → `/wiki-ingest` → `/wiki-query` → `/wiki-status`.
3. Don't expand `CLAUDE.md` without clear motivation — every line is loaded into every session. Token discipline matters.
4. Don't add retrieval infrastructure (embeddings, vector stores) without hitting the graduation trigger in `docs/GUIDE.md` §15. Premature optimization is the main failure mode for this architecture.

**Not in scope:**

- Bundling content (sources, concept pages). The template stays zero-content by design.
- Alternative storage backends. Plain markdown is non-negotiable.
- Features that only work in proprietary clients. Everything must degrade gracefully to `cat wiki/*.md`.

---

## FAQ

**Do I need a Claude subscription?**
Yes. The template is designed for [Claude Code](https://claude.ai/code). Any plan that includes Claude Code works.

**Can I use a different LLM / agent?**
In principle, any markdown-aware agent that can read `CLAUDE.md` and execute bash + file I/O. In practice, the slash commands are specific to Claude Code's runtime. Porting would require adapting the command format.

**Can I keep my wiki private?**
Yes — it's just a git repo. Use a private GitHub repo, or never push. Everything lives on your disk.

**Does Obsidian call home?**
Obsidian is local-first and doesn't send content anywhere by default. Claude Code sends the pages it loads to Anthropic for inference; that's the standard API flow.

**How is this different from Notion AI / Mem / Reflect?**
Those are hosted services with proprietary storage. z-wiki is plain markdown files on your disk, readable by any tool, versioned by git, and the compilation is deterministic given the spec.

**Can I run this on mobile?**
Obsidian works on iOS/Android for *reading* the vault. Claude Code is desktop-only at time of writing, so ingest/query requires a laptop.

---

## Acknowledgments

- **Andrej Karpathy** — ["LLM knowledge bases"](https://x.com/karpathy/). The original raw-sources → compiled-wiki → query → file-back architecture.
- **Shann Holmberg** — ["The AI Knowledge Layer"](https://x.com/shannholmberg/). The framing as agent infrastructure and the two-layer extension.
- **Steph Ango (kepano)** — [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills). The five vendored skills that teach Claude to write idiomatic Obsidian markdown, Bases, and Canvas files.
- **Anthropic** — [Claude Code](https://claude.ai/code). The runtime this template is built around.

---

## License

[MIT](LICENSE). Vendored skills under `.claude/skills/` are MIT from [kepano/obsidian-skills](https://github.com/kepano/obsidian-skills); see [docs/obsidian-skills-provenance.md](docs/obsidian-skills-provenance.md) for provenance.

---

<div align="center">

**[⭐ Star this repo](../../stargazers)** if z-wiki is useful to you — helps others find it.

Found a bug or want to suggest something? [Open an issue](../../issues).

</div>
