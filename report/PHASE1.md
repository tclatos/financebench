# FinanceBench Phase 1 — Document Graph + Agentic Search Diagnostic

**Date:** 2026-08-22
**Target document:** `AMD_2022_10K` (AMD 10-K, FY2022) — auto-selected as the single `doc_name` with the most questions (7) in the 150-row FinanceBench open-source split.
**Agent LLM:** `deepseek_v4flash@openrouter` · **Judge LLM:** `deepseek_v4flash@openrouter`
**Stack:** `genai-tk` + `genai-graph` (Document Graph on Ladybug/Kuzu, vectorless agentic search, DeepAgents SDK).

## TL;DR

| Metric | Result |
|---|---|
| Questions | 7 |
| **Accuracy (strict correct)** | **6/7 = 85.7%** |
| Groundedness | **7/7 = 100%** (zero hallucinations) |
| Numeric match | 1/2 = 50% |
| Avg tool calls / question | 6.4 |
| Avg tokens (in / out) | 74,254 / 1,801 |
| Agent errors | 0 |

The Document Graph + agentic search approach is validated: the agent navigated
the 10-K's heading hierarchy and financial-statement tables, grounded every
answer in source sections, and got 6/7 right. The single failure is a
**numerical-reasoning error** (wrong quick-asset formula), not a retrieval
failure — exactly the known FinanceBench weakness and a clear Phase-2 target.

## What was built (Phase 1)

1. **Dataset** — `financebench/bench/load_dataset.py`: loads
   `PatronusAI/financebench` from Hugging Face, caches to parquet, auto-selects
   the richest single doc, writes `data/financebench/questions.jsonl`.
2. **PDF fetch** — `financebench/bench/fetch_pdf.py`: downloads
   `<doc_name>.pdf` from the FinanceBench GitHub repo.
3. **OCR → graph** — `financebench/bench/build_graph.py`: Mistral OCR
   (`mistral-ocr-latest` batch API) → `<doc>_pdf.md` (OneDrive mirror +
   `data/markdown/`) → `Folder → Document → MarkdownSection` graph in Ladybug
   (259 sections, 83k tokens). Calls the OCR processor and ingestor directly
   (no Prefect server dependency).
4. **Agent + skill** — `config/agents.yaml` `docgraph` deep profile +
   `skills/custom/financebench-qa/SKILL.md` (financial-statement targeting,
   units/rounding, citation, never-invent rules).
5. **Runner** — `financebench/bench/run_questions.py`: runs each question via
   `create_docgraph_agent` + harness streaming, captures the per-question
   trajectory (tool calls, results, tokens, answer).
6. **Grader** — `financebench/bench/grade.py`: LLM-as-judge
   (correctness / numeric_match / groundedness / rationale) → `scores.jsonl`.
7. **Trajectories** — every run is also recorded in the global `TrajectoryStore`
   (8 runs, `cli trajectory list/show/export`).

## Per-question results

| financebench_id | Type | Reasoning | Verdict | Numeric | Ground | Tool calls |
|---|---|---|---|---|---|---|
| _00222 | domain-relevant | Logical/numerical | **incorrect** | False | grounded | 7 |
| _00563 | novel-generated | — | correct | — | grounded | 5 |
| _00757 | novel-generated | — | correct | True | grounded | 7 |
| _00917 | domain-relevant | Logical/numerical | correct | — | grounded | 7 |
| _00995 | domain-relevant | Info extraction | correct | — | grounded | 7 |
| _01198 | domain-relevant | Numerical | correct | — | grounded | 6 |
| _01279 | domain-relevant | Numerical | correct | — | grounded | 6 |

### Failure detail — `_00222` (quick ratio)

- **Question:** Does AMD have a reasonably healthy liquidity profile based on
  its quick ratio for FY22?
- **Gold:** Yes. Quick ratio = **1.57** = (cash + ST investments + AR + related
  receivables) / current liabilities.
- **Agent:** Quick ratio = **1.77** — it computed
  (current assets − inventories) / current liabilities instead of the gold's
  explicit quick-asset sum, picking a different (looser) numerator.
- **Diagnosis:** Retrieval was correct (it read the Consolidated Balance Sheets
  and cited `[f391da52bf0af1c2::137]`); the error is in **which line items
  belong in the quick-asset numerator** — a financial-definition / numerical-
  reasoning mistake, not a graph-navigation failure.
- **Non-determinism note:** an earlier smoke-test run of the same question
  produced 1.57 (correct). The agent runs at the model's default sampling, so
  numeric questions are unstable run-to-run.

## Trajectory analysis

**Tool frequency (7 questions):** `get_section_content` 11, `search_sections`
9, `get_folder_toc` 5, `get_document_toc` 5, `list_documents` 2 (plus 13
`read_file` = skill loads by the SkillsMiddleware, not navigation).

**Navigation patterns observed:**
- Most questions follow the intended loop: orient (`get_folder_toc` /
  `list_documents`) → map (`get_document_toc`) → search (`search_sections`) →
  read (`get_section_content`), iterating until grounded.
- `_00757` (customer concentration) needed 4 `search_sections` calls before
  landing on the right note — keyword sensitivity matters.
- The agent correctly targets statements by name (Consolidated Balance Sheets,
  Cash Flows, Segment Reporting / Note 4).

**Cost:** ~520k input tokens for 7 questions (avg 74k in). The high input
figure reflects reading whole financial-statement sections (large markdown
tables). This is the main efficiency lever.

## Failure taxonomy (improvement backlog)

1. **Numerical reasoning / formula selection** (`_00222`) — the agent picks a
   plausible-but-wrong numerator for ratios. *Fix candidates:* (a) a
   ratio-definition helper skill (quick ratio, turnover, capex% etc. with the
   exact line-item formula); (b) a "compute then re-derive" self-check step;
   (c) lower temperature / seeded decoding for numeric questions.
2. **Reasoning preamble leaking into the final answer** — several answers begin
   with "Now let me also check the MD&A…" (a DeepAgents streaming artifact).
   *Fix:* strip planner/scratchpad text from the final assistant message, or
   use the DeepAgents `final_answer` channel only.
3. **Keyword-search sensitivity** — `_00757` took 4 searches. *Fix:* a
   thesaurus/alias map in the skill (e.g. "customer concentration" → also
   search "10%", "significant customer", "Note 4").
4. **Token efficiency** — reading whole statements is token-heavy. *Fix:*
   `get_section_content` could return a compacted table view, or add a
   `get_table`/line-item extraction tool.
5. **Reproducibility** — numeric answers vary run-to-run. *Fix:* fixed seed /
   temperature 0 for the agent LLM (the judge already uses temp 0).

## Phase 2 plan

- **Scale:** more documents (the next-richest `doc_name`s) and all their
  questions; corpus-wide agent (`folder_id=None` already supports this).
- **Parallelism:** fan question-runs out to parallel child agents (the runner
  already isolates per question by `thread_id`).
- **Auto-improvement loop (the goal):** use the per-question trajectories +
  judge verdicts to drive iterative skill/tool improvements — i.e. the failure
  taxonomy above becomes a prioritized, trajectory-grounded backlog. Concretely:
  feed `_00222`-style failures back into the ratio-definition skill and
  re-run to confirm the fix.
- **Stronger numerics:** evaluate a stronger reasoning model (e.g. GPT-5 / o3
  class) on the numeric subset, and add a table/line-item node type to the
  Document Graph so cells are first-class retrievable objects.
- **Reproducible eval harness:** seed + temperature 0 for the agent; a
  `just bench` recipe that runs load → fetch → build → run → grade → report.

## Reproducing this phase

```bash
uv sync --extra harnessing
uv run python -m financebench.bench.load_dataset        # → AMD_2022_10K, 7 questions
uv run python -m financebench.bench.fetch_pdf
uv run python -m financebench.bench.build_graph         # Mistral OCR → Document Graph
uv run python -m financebench.bench.run_questions       # 7 questions → runs.jsonl
uv run python -m financebench.bench.grade               # LLM-as-judge → scores.jsonl
cli trajectory list                                      # inspect recorded trajectories
```

Artifacts (gitignored, under `data/`): `data/financebench/{questions,runs,scores}.jsonl`,
`data/kg/financebench_tree.db`, `data/trajectories/`. OCR markdown is mirrored
to `$ONEDRIVE/prj/financebench/markdown/`.

---

# FinanceBench Phase 1.1 — LLM-enhanced Document Graph (re-run)

**Date:** 2026-08-24
**Trigger:** a new `genai-graph` build path (commit `40201f1`) uses a flash LLM to
discover each document's real table of contents and summarize its sections in
one call, instead of splitting on every Markdown `#`. Re-run the 7 questions on
the rebuilt graph, grade, and compare to Phase 1.
**Build LLM:** `deepseek_v4flash@openrouter` (outline pass) · **Agent/Judge
LLM:** `deepseek_v4flash@openrouter` (unchanged from Phase 1 for a clean
comparison).

## TL;DR (Phase 1.1)

| Metric | Phase 1 (algo) | Phase 1.1 (LLM) | Δ |
|---|---|---|---|
| Questions | 7 | 7 | — |
| **Accuracy (strict correct)** | 6/7 = 85.7% | **7/7 = 100%** | **+1** |
| Groundedness | 7/7 = 100% | 7/7 = 100% | — |
| Numeric match | 1/2 = 50% | **2/2 = 100%** | **+1** |
| Avg tool calls / question | 6.4 | 13.4 | +7.0 (2.1×) |
| Avg input tokens / question | 74,254 | 176,657 | +102k (2.4×) |
| Avg output tokens / question | 1,801 | 2,344 | +543 (1.3×) |
| Agent errors | 0 | 0 | — |

The LLM-enhanced graph **fixes the one Phase-1 failure** (the `_00222` quick
ratio is now `1.57`, matching gold) while keeping groundedness perfect. The
trade-off is cost: ~2.4× input tokens and ~2.1× tool calls, because the LLM
outline produces far fewer, much larger sections (each `get_section_content`
returns a whole 10-K item rather than a fine sub-heading). Accuracy ↑, cost ↑.

## What changed in the build

The new `build_graph.py --llm` path wires `OutlineConfig` +
`DocumentGraphFactory.extract_outlines()` (parallel content-addressed cache) +
`ingest_document_graph` directly, mirroring `document_graph_flow` without the
Prefect server. The flash model returns a content-free JSON outline (TOC +
per-section `description` + `summary` for substantial sections + a document
`description`/`summary`); a deterministic merge anchors the outline titles back
to the Markdown.

| Graph property | Phase 1 (algorithmic) | Phase 1.1 (LLM outline) |
|---|---|---|
| MarkdownSection nodes | 259 | **27** |
| Sections with `description` | 0 | **26 / 27** |
| Sections with `summary` | 0 | **9 / 27** (`summary_source=llm`) |
| Document `description` | — | ✅ (1 sentence) |
| Document `summary` | — | ✅ (4 sentences) |
| Section granularity | every `#` heading | the **real 10-K TOC** (PART I–IV, ITEMS 1–8) |

The 27 sections are the actual 10-K items: `PART I`, `ITEM 1. BUSINESS`,
`ITEM 1A. RISK FACTORS`, … `ITEM 7. MD&A`, `ITEM 8. FINANCIAL STATEMENTS`, …
`PART IV`. The 9 summarized ones are the substantial parts (Item 1, 1A, 7, 8,
the PARTs, Item 5).

A required **bug fix in `genai-graph`**: the outline prompt baked the raw
Markdown into a `ChatPromptTemplate` user string, so the 10-K's LaTeX
superscripts (`^{(1)}`, `^{(\*)}`) were parsed as prompt-template variables →
"missing variables" → the LLM call failed and the build silently degraded to
algorithmic parsing (no summaries). Fixed in
`genai_graph/kg/document_graph/outline_extract.py` by passing the document as a
`{raw}`/`{filename}` template variable filled at `.invoke()` time (braces in the
source are no longer interpreted as variables). The stale degraded outline
cache was cleared so the call retries.

## Per-question results (Phase 1.1)

| financebench_id | Type | Reasoning | Verdict | Numeric | Ground | Tool calls | In tok |
|---|---|---|---|---|---|---|---|
| _00222 | domain-relevant | Logical/numerical | **correct** ✅ | True | grounded | 13 | 151,236 |
| _00563 | novel-generated | — | correct | — | grounded | 17 | 225,904 |
| _00757 | novel-generated | — | correct | True | grounded | 26 | 424,066 |
| _00917 | domain-relevant | Logical/numerical | correct | — | grounded | 14 | 127,251 |
| _00995 | domain-relevant | Info extraction | correct | — | grounded | 7 | 109,917 |
| _01198 | domain-relevant | Numerical | correct | — | grounded | 6 | 58,045 |
| _01279 | domain-relevant | Numerical | correct | — | grounded | 11 | 140,182 |

### The `_00222` quick-ratio fix

- **Gold:** quick ratio = **1.57** = (cash + ST investments + AR + related
  receivables) / current liabilities.
- **Agent (Phase 1.1):** quick ratio = **1.57**, computed as
  (cash $4,835M + ST investments $1,020M + AR $4,126M) = $9,981M / current
  liabilities $6,369M, citing `[f391da52bf0af1c2::13]` (ITEM 8 Financial
  Statements — one of the 9 summarized sections) and `[f391da52bf0af1c2::11]`
  (ITEM 7 MD&A, also summarized).
- **Why it helped:** the LLM outline's section descriptions (e.g. *"Item 8
  presents AMD's audited financial statements… income statements, balance
  sheets, cash flow statements…"*) route the agent straight to the balance
  sheet, and the coarse section holds the full statement so the line items are
  read together → the correct quick-asset numerator.
- **Caveat (non-determinism):** Phase 1 noted that an earlier smoke-test run of
  this same question also produced 1.57. The agent runs at the model's default
  sampling, so this single-question fix is partly sampling luck — a seeded
  (temperature-0) re-run is needed to confirm it is a structural improvement.

## Trajectory analysis (Phase 1.1)

**Tool frequency (7 questions):** `search_sections` 41, `get_section_content`
14, `get_document_toc` 11, `get_folder_toc` 5, `list_documents` 1, plus
`read_file`/`grep` (DeepAgents built-in file tools — see caveat below).

**Why cost rose ~2.4×:** the 27 coarse sections each span a whole 10-K item
(e.g. ITEM 8 is the bulk of the 83k-token document), so each
`get_section_content` returns a large chunk; the agent also issues more
`search_sections` calls because coarser sections yield fewer, broader hits per
search. Phase 1's 259 fine sections let the agent read a tiny targeted
sub-heading (cheap) at the cost of weaker routing. The LLM outline flips that:
better routing (descriptions/summaries) but bigger reads.

**Navigation pattern (unchanged and healthy):** orient (`get_folder_toc` /
`list_documents`) → map (`get_document_toc`, now showing the document
`description`+`summary` and every section's `description`) → search/read
(`search_sections`, `get_section_content`) → answer, citing `[hash::seq]`.

## Caveats & findings

1. **Mixed retrieval path (benchmark integrity):** the `type: deep` profile
   ships DeepAgents file tools (`read_file`, `grep`), so the agent can read
   `data/markdown/*.md` directly and bypass the graph. This was already true in
   Phase 1, so the comparison is fair, but it means the score is an upper bound
   on "graph-only" retrieval. *Recommendation:* disable file tools for the
   docgraph agent so the Document Graph is the sole retrieval path.
2. **Empty relationship tables:** `merge_relationships_batch` reports N
   relationships created but **0** `HAS_SECTION`/`CONTAINS` edges are queryable
   via Cypher. This is **functionally irrelevant** — the navigation tools query
   `MarkdownSection` nodes by `markdown_hash` and reconstruct the tree from
   `parent_section_id`/`sequence`, never traversing edges. But it is a
   `genai-graph` ingest bug worth fixing (and a reason not to rely on edge
   counts as a build-quality metric).
3. **Summaries are opt-in:** `get_document_toc` emits section `description` by
   default but the fuller `summary` only when the agent passes
   `include_summaries=True`. The document-level `summary` is always shown.
4. **Non-determinism:** numeric verdicts still vary run-to-run (default
   sampling); see the `_00222` caveat.

## Improvement backlog (Phase 1.1 additions)

1. **Hybrid granularity** (top priority for cost): keep the LLM outline for the
   top-level TOC + descriptions/summaries, but re-introduce fine-grained
   sub-sections *within* large items so the agent can read a targeted balance-
   sheet chunk instead of all of ITEM 8. Target: Phase-1 token cost with
   Phase-1.1 routing quality.
2. **Graph-only retrieval:** disable `read_file`/`grep`/`ls` for the docgraph
   agent so the benchmark measures the Document Graph, not the filesystem.
3. **Surface section summaries:** default `get_document_toc(include_summaries=True)`
   (or have the skill request it) so the 2–3 sentence summaries are a routing
   signal, not just the one-line description.
4. **Reproducibility:** seed / temperature 0 for the agent LLM (the judge
   already uses temp 0) and re-run to confirm the `_00222` fix is structural.
5. **Upstream the brace fix** to `genai-graph` `outline_extract` (and a unit
   test with a Markdown containing `^{(1)}` superscripts).
6. **Investigate the empty relationship tables** in `genai-graph`
   `merge_relationships_batch` (low priority — tools don't use edges).

## Reproducing Phase 1.1

```bash
# Build LLM-enhanced graph from the existing OCR markdown (one outline LLM call):
uv run python -m financebench.bench.build_graph --skip-ocr --force --llm
# Re-run + grade (same commands as Phase 1):
uv run python -m financebench.bench.run_questions
uv run python -m financebench.bench.grade
```

The outline LLM call is content-addressed and cached under
`data/kg/financebench_tree_outlines/` (gitignored), so re-builds are free.

---

# FinanceBench Phase 1.2 — Hybrid outline + benchmark-integrity fixes + deterministic re-run

**Date:** 2026-08-25
**Trigger:** Phase 1.1's LLM outline produced only 27 coarse sections (each a
whole 10-K item → ~176k tok/q, 2.4× Phase 1) and ignored Markdown heading
levels; plus four benchmark-integrity caveats from the Phase-1.1 report (file
tools on, empty relationship tables, summaries opt-in, non-determinism). Address
all four and re-run.
**Scope:** `genai-graph` (hybrid outline + ingest bug fix), `genai-tk` (tool-
exclusion config), `financebench` (docgraph profile + inlined strategy).

## TL;DR (Phase 1.2)

| Metric | Phase 1.1 (LLM, 27 sections) | Phase 1.2 (hybrid, 251 sections) | Δ |
|---|---|---|---|
| Questions | 7 | 7 | — |
| **Accuracy (strict correct)** | 7/7 = 100% | **7/7 = 100%** | — (now graph-only, not an upper bound) |
| Groundedness | 7/7 = 100% | 7/7 = 100% | — |
| Numeric match | 2/2 = 100% | 3/3 = 100% | — (judge classified 3 numeric; all match) |
| Avg tool calls / question | 13.4 | **5.43** | **−59%** |
| Avg input tokens / question | 176,657 | **59,410** | **−66%** |
| Avg output tokens / question | 2,344 | 1,757 | −25% |
| File-tool calls (corpus access) | `read_file`/`grep` present | **0** | graph-only achieved |
| Agent temperature | default (non-det) | **0.0 (deterministic)** | reproducible |
| Agent errors | 0 | 0 | — |

Same 100% accuracy and groundedness, now at ~1/3 the input-token cost, with
file tools disabled and temperature 0 — so the score is a true, reproducible
**graph-only** result rather than a non-deterministic upper bound.

## What changed

### Build: hybrid heading-anchored outline (27 → 251 sections)

The LLM outline now anchors to the **algorithmically detected Markdown headings**
(H1/H2/H3) instead of inventing a coarse 27-entry TOC.

- `tree_parser` dedupes repeated zero-body page-headers (258 → 250 headings on AMD).
- `outline_extract._build_prompt` lists every detected heading (`[Llevel] title`)
  and asks the LLM for one `description`/`summary` per heading; `_align_outline`
  matches the LLM entries back to the authoritative detected headings before
  caching. Policy hash bumped to `hybrid-v1` (cache `34975673e354`).
- `outline_merge.merge_outline` slices on the detected headings and attaches
  `description`/`summary` by index (title-anchored reconciliation only as a
  count-mismatch fallback).

| Graph property | Phase 1.1 (LLM outline) | Phase 1.2 (hybrid) |
|---|---|---|
| MarkdownSection nodes | 27 | **251** |
| Heading levels | flat (all level 1) | **{1:176, 2:15, 3:59}** |
| Sections with `description` | 26 / 27 | **250 / 250** |
| Sections with `summary` | 9 / 27 | 9 / 251 |
| ITEM 8 granularity | one block | **Balance Sheets / Statements / Notes / NOTE 1–17** |
| Outline LLM calls on rebuild | 1 | **0 (cache warm)** |

The 251 fine-grained sections let the agent read a **targeted balance-sheet
chunk** instead of all of ITEM 8 — the direct cause of the ~66% token drop.

### Caveat fixes

1. **File tools disabled (graph-only).** Added `excluded_tools` to `genai-tk`'s
   `AgentProfileConfig`; `_create_deep_agent` appends deepagents'
   `_ToolExclusionMiddleware(excluded=...)` last in the user middleware chunk
   (after NeMo relay), stripping the built-in tools from the model's tool list
   each turn. The docgraph profile excludes
   `ls, read_file, grep, glob, write_file, edit_file, execute, task`. The agent
   can no longer read `data/markdown/*.md` or delegate to the general-purpose
   subagent (`task`); the four graph tools (`list_documents`, `get_folder_toc`,
   `get_document_toc`, `get_section_content`, `search_sections`) are the sole
   retrieval path. Because skills are unreadable without `read_file`,
   `prepare_docgraph_profile` skips skill loading (and the filesystem backend)
   in graph-only mode and the `financebench-qa` navigation strategy is inlined
   into the docgraph system prompt instead.
   - **Verified in traces:** 0 calls to `ls/grep/glob/write_file/edit_file/
     execute/task` across all 7 questions. The single `read_file` call observed
     (`_00995`) targeted `/large_tool_results/<call_id>` — deepagents'
     overflow-recovery pagination of an already-graph-retrieved
     `get_section_content` result, not filesystem access (no `FilesystemBackend`
     in graph-only mode). The agent never touched the source markdown.
2. **Empty relationship tables fixed.** Root cause: `merge.py::
   merge_relationships_batch`'s no-property branch used a two-stage
   `LOAD FROM ... WITH from, to_id MATCH ... MATCH ... MERGE` — the `WITH`
   dropped the `LOAD FROM` column binding after the first `MATCH`, so the
   second `MATCH` matched nothing → 0 rows. Replaced with a batch-inline
   `LOAD FROM arrow_rel_table MATCH (from{key:from_id}), (to{key:to_id}) MERGE`
   (point lookups, no cross product), and `total_created` now uses a
   before/after count delta (MERGE is idempotent → exact) instead of
   `len(row_data)`. Rebuilt: `HAS_SECTION=1`, `HAS_SUBSECTION=250`,
   `CONTAINS=1` (was 0/0/0). The navigation tools still don't traverse edges,
   but edge counts are now a trustworthy build-quality signal.
3. **Summaries on by default.** Flipped `include_summaries` default `False`→
   `True` in `build_toc_tree`, `document_toc_yaml`, `folder_toc_yaml` and the
   `get_document_toc` tool. Cost scales with how many sections were summarised
   (only 9/251 here) so it's cheap; verified the live AMD TOC now emits all 9
   per-section summaries + the document summary.
4. **Determinism.** Agent + judge both run at temperature 0.0 (`genai-tk`
   `llm_factory.common_params` applies `temperature: 0.0` to every LLM). Re-ran
   to confirm the `_00222`=1.57 fix is structural, not sampling luck.

## Per-question results (Phase 1.2)

| financebench_id | Reasoning | Verdict | Numeric | Ground | Tool calls | In tok | Out tok |
|---|---|---|---|---|---|---|---|
| _00222 | Logical/numerical | **correct** ✅ | True | grounded | 3 | 23,854 | 1,205 |
| _00563 | — | **correct** ✅ | True | grounded | 5 | 58,138 | 2,300 |
| _00757 | — | **correct** ✅ | True | grounded | 15 | 126,139 | 1,720 |
| _00917 | Logical/numerical | **correct** ✅ | null | grounded | 5 | 86,042 | 3,517 |
| _00995 | Info extraction | **correct** ✅ | null | grounded | 4 | 62,667 | 1,324 |
| _01198 | Numerical | **correct** ✅ | null | grounded | 3 | 39,139 | 1,480 |
| _01279 | Numerical | **correct** ✅ | null | grounded | 3 | 19,891 | 755 |

Numeric verdicts: `_00222` quick ratio = **1.57** (= (cash $4,835M + ST
investments $1,020M + AR $4,126M) / current liabilities $6,369M, citing
`[f391da52bf0af1c2::130]`); `_00563` = **Data Center** (64% growth, largest
proportional increase excl. Embedded); `_00757` = **one customer = 16%** of
consolidated net revenue.

vs Phase 1.1 per-q input tokens: `_00222` 151,236→23,854 (−84%), `_00563`
225,904→58,138, `_00757` 424,066→126,139 (−70%), `_00917` 127,251→86,042,
`_00995` 109,917→62,667, `_01198` 58,045→39,139, `_01279` 140,182→19,891
(−86%). Every question cheaper; the biggest savings are on the high-cost
Phase-1.1 questions where coarse sections forced huge reads.

## Trajectory analysis (Phase 1.2)

**Tool frequency (7 questions, 38 calls):** `get_section_content` 14,
`search_sections` 11, `get_folder_toc` 7, `get_document_toc` 5, `read_file` 1
(overflow pagination only). vs Phase 1.1: `search_sections` 41→11 (−73%),
`get_document_toc` 11→5, `get_section_content` 14→14 (unchanged — the agent
still reads ~2 sections/q, but now targeted sub-sections, not whole items).

**Why cost fell ~66%:** the hybrid outline's 251 fine-grained sections (ITEM 8
splits into Balance Sheets / Statements / Notes / NOTE 1–17) mean each
`get_section_content` returns a targeted chunk (e.g. just the Consolidated
Balance Sheets) instead of all of ITEM 8. Better routing (a `description` on
every section + summaries on by default) means fewer `search_sections` probes
and fewer `get_document_toc` re-maps — the agent reads the right small section
first time.

**Navigation pattern (clean and consistent):** every question opens with
`get_folder_toc` (orient → `AMD_2022_10K`, now showing the doc `description`+
`summary`), then either `get_document_toc` (map the section tree) or
`search_sections` (targeted keyword), then `get_section_content` (read the
matching sections), then answer citing `[hash::sequence]`. `_00757` (customer
concentration) is the outlier at 15 calls (heavy `search_sections` probing
across NOTE 10 Concentrations of Credit Risk + risk factors), but still correct
and grounded.

## Caveats & findings (Phase 1.2)

1. **`_00995` overflow `read_file`:** one `read_file` call
   (`/large_tool_results/<call_id>`) is deepagents' pagination of a large
   `get_section_content` result, not filesystem access — no corpus leak. It
   re-reads graph-retrieved content only. Could be eliminated by also stripping
   `read_file` from the tool node, but that would prevent the agent paginating
   large section reads (which can hurt) — left as-is.
2. **Skill loading skipped in graph-only mode:** because `read_file` is
   excluded, `SkillsMiddleware` could not read any `SKILL.md`; loading skills
   would inject a "use `read_file` for full instructions" prompt pointing at a
   tool the agent lacks. The navigation strategy is therefore inlined in the
   docgraph system prompt (the `financebench-qa` SKILL.md is now documentation-
   only for this profile). If file tools are re-enabled, skill loading resumes.
3. **Empty rel tables were a real ingest bug** (now fixed) — see caveat fix #2.
4. **Judge numeric classification:** the judge marked 3 questions numeric
   (Phase 1.1 marked 2). The same flash judge (temp 0) classifies "is a number
   expected" per question; the count can shift slightly run-to-run but all
   matched, so accuracy is unaffected.

## Improvement backlog (Phase 1.2 → next)

1. **Larger question set:** 7 questions on one 10-K is a thin benchmark; expand
   to multiple filings (e.g. the full FinanceBench AMD set + other issuers) to
   stress routing across documents and reduce per-question variance.
2. **Stronger reasoning model on the numeric subset:** evaluate a GPT-5/o3-class
   model on the numeric questions to test whether graph-only + hybrid routing
   holds for harder multi-step numerics.
3. **Table/line-item node type:** add structured table nodes to the Document
   Graph so line items (e.g. "Cash and cash equivalents $4,835M") are first-class
   retrievable objects — removes the agent's need to read+parse whole
   balance-sheet Markdown.
4. **Reproducible eval recipe:** a `just bench` recipe (load → fetch → build →
   run → grade → report) + a frozen `runs.jsonl`/`scores.jsonl` snapshot for
   regression checks.
5. **Overflow `read_file` provenance:** optionally annotate the tool-result
   overflow path so traces make the `/large_tool_results/` provenance explicit
   (it currently looks like a file read).

## Reproducing Phase 1.2

```bash
# Hybrid outline rebuild from the existing OCR markdown (cached, 0 LLM calls on re-run):
uv run python -m financebench.bench.build_graph --skip-ocr --force --llm
# Graph-only, temperature-0 run + judge:
uv run python -m financebench.bench.run_questions
uv run python -m financebench.bench.grade
```

Agent profile: `config/agents.yaml` `docgraph` (`excluded_tools`, inlined
strategy, temp 0). Outline cache: `data/kg/financebench_tree_outlines/
deepseek_v4flash_openrouter__34975673e354/` (gitignored).

---

# FinanceBench Phase 1.3 — Restore heading hierarchy + richer descriptions + rerun/report

**Date:** 2026-08-25
**Trigger:** Phase 1.2's hybrid outline produced 251 sections but the heading *levels*
were still degenerate (`{1:176, 2:15, 3:59}` — almost everything forced to level 1)
because `tree_parser._infer_levels` overrode the Markdown levels whenever ≥3 headings
started with a number, and the AMD 10-K's only "numbered" headings were 5 false
positives (`3.924% Senior Notes`, `2.125% Notes`, `7.50% Senior Notes`,
`1. Financial Statements`, `2. Exhibits`). Consequences: many LLM descriptions just
rephrased the title, and some titles carried `***` emphasis
(`***Original Equipment Manufacturers***`). Improve the structure extraction
(keeping it robust for more-structured documents), then rerun and report.
**Scope:** `genai-graph` (`tree_parser`, `outline_extract`, `commands_docgraph`);
the `financebench` docgraph profile (temp 0, graph-only) from 1.2 is unchanged.

## TL;DR (Phase 1.3)

| Metric | Phase 1.2 (hybrid v1) | Phase 1.3 (hybrid v2) | Δ |
|---|---|---|---|
| Questions | 7 | 7 | — |
| **Accuracy (strict correct)** | 7/7 = 100% | **6/7 = 85.7%** | **−1** (`_00757` → partial) |
| Accuracy (correct-or-partial) | 100% | 100% | — |
| Groundedness | 7/7 = 100% | 7/7 = 100% | — |
| Numeric match | 3/3 = 100% | 2/3 = 66.7% | −1 (`_00757`) |
| Avg tool calls / question | 5.43 | **4.14** | **−24%** |
| Avg input tokens / question | 59,410 | **49,035** | **−17.5%** |
| Avg output tokens / question | 1,757 | 1,540 | −12.3% |
| File-tool calls (corpus access) | 0 | 0 | graph-only holds |
| Agent temperature | 0.0 | 0.0 | reproducible |
| Agent errors | 0 | 0 | — |

The rebuilt graph restores the **real heading hierarchy**
(`{1:98, 2:63, 3:55, 4:31, 5:3}` vs 1.2's degenerate `{1:176, 2:15, 3:59}`),
strips `***` emphasis from titles, and gives every non-divider section a concrete
(non-title-restating) description. The agent is **~24% cheaper in tool calls and
~17% cheaper in input tokens**, with groundedness still perfect. One numeric
regression (`_00757`) is a **retrieval-precision** issue (the agent retrieved the
accounts-receivable concentration note instead of the net-revenue concentration),
not a structural failure — see below.

## What changed

### 1. Heading levels restored (`tree_parser._infer_levels`)

`_infer_levels` was overriding Markdown-it's own (correct) heading levels whenever
≥3 headings started with a number. The AMD 10-K's only "numbered" headings are 5
false positives (interest-rate note titles + `1. Financial Statements` / `2.
Exhibits`); once triggered it forced everything before the first number to level 1,
collapsing the hierarchy to `{1:176, 2:15, 3:59}`.

- **Tightened `_OUTLINE_NUMBER_RE`** to require the number be followed by
  whitespace / `.` / end-of-string, so `3.924% Senior Notes` (an interest rate,
  not an outline item) is rejected while `1. Financial Statements` and `3.4
  Device life cycle` are kept.
- **Degeneracy gate on `_infer_levels`**: it now returns the Markdown levels
  **unchanged** unless they are degenerate (≤1 distinct levels, or the modal level
  is ≥85% of headings) — and only then (and only if ≥3 numbered headings exist)
  does it re-derive from outline numbers. This makes well-structured Markdown
  authoritative; only genuinely flat documents fall back to outline-number
  inference, so more-structured documents keep their native hierarchy.

Result on AMD: `{1:98, 2:63, 3:55, 4:31, 5:3}` (250 headings) — the real
PART I/ITEM 1 → Our Industry/Data Center Segment → Data Center Market nesting.
Reconstruction is byte-for-byte intact.

### 2. Emphasis stripped from titles (`tree_parser.detect_headings`)

Added `_strip_surrounding_emphasis` (unwraps balanced `***foo***`, then trims
unbalanced dangling `*`/`_` glued to text; backticks excluded to protect inline
code) and applied it in `detect_headings`. `***Original Equipment Manufacturers***`
→ `Original Equipment Manufacturers`. 0 residual emphasis titles across all 250.

### 3. Richer, non-restating descriptions (`outline_extract`)

- `OutlineEntry.description` made optional (`str | None`).
- **Prompt rewrite:** require CONCRETE subject matter (entities/metrics/products/
  scope), forbid restating the title, return `null` for structural dividers
  (`PART I`, `FORM 10-K`, `INDEX`, repeated company-name headers), with few-shot
  BAD/GOOD examples.
- **Restatement post-filter** (`_is_title_restatement`): drops any description
  whose significant (non-stopword) words are a subset of the title's — so
  "Customers → Describes the customers section" is dropped to `null`.
- **Policy hash `hybrid-v1` → `hybrid-v2`** (cache invalidation; new cache dir
  `deepseek_v4flash_openrouter__5cab039c8230`).

Result: 31/250 null descriptions (the structural dividers), the rest substantive —
e.g. *Data Center Products → "Lists EPYC CPUs, Instinct GPUs, Pensando DPUs, Alveo
FPGAs, and Versal Adaptive SoCs."*; *Our Strategy → "Lists five strategic
pillars…"*. Rebuild cost: **1 LLM call** (cache cold after the hash bump).

### 4. CLI TOC YAML serialization fix (`commands_docgraph.py`)

`cli docgraph toc <id> --yaml` had been producing **invalid YAML** (continuation
lines landing at column 1, failing `yaml.safe_load`) whenever a
 description/summary line wrapped past the terminal width. Root cause: the command
routed the YAML string through Rich's `console.print`, which re-wraps text to the
terminal width and **drops indentation from wrapped continuations**. Fixed by
emitting with `console.print(..., soft_wrap=True)` in the `toc` and `folder-toc`
commands (3 call-sites). The agent-facing `document_toc_yaml` tool was never
affected (it returns the string directly, not through Rich).

## Per-question results (Phase 1.3)

| financebench_id | Reasoning | Verdict | Numeric | Ground | Tool calls | In tok | Out tok |
|---|---|---|---|---|---|---|---|
| _00222 | Logical/numerical | **correct** ✅ | True | grounded | 3 | 19,316 | 1,175 |
| _00563 | — | **correct** ✅ | True | grounded | 3 | 20,969 | 1,003 |
| _00757 | — | **partial** ⚠️ | False | grounded | 4 | 18,713 | 601 |
| _00917 | Logical/numerical | **correct** ✅ | null | grounded | 5 | 89,204 | 3,885 |
| _00995 | Info extraction | **correct** ✅ | null | grounded | 5 | 73,805 | 1,444 |
| _01198 | Numerical | **correct** ✅ | null | grounded | 5 | 74,085 | 1,756 |
| _01279 | Numerical | **correct** ✅ | null | grounded | 4 | 47,155 | 913 |

Numeric verdicts: `_00222` quick ratio = **1.57** (correct); `_00563` = **Data
Center** (largest proportional sales increase excl. Embedded); `_00757` = **18% of
accounts receivable** (see regression detail — gold wanted 16% of net revenue).

### Regression detail — `_00757` (customer concentration)

- **Question:** Did AMD report customer concentration in FY22?
- **Gold:** Yes — one customer accounted for **16% of consolidated net revenue**.
- **Agent:** Yes — in Note 10 (Concentrations of Credit Risk), one customer
  accounted for **~18% of total consolidated accounts receivable** (and two
  customers at 20%/15% of A/R for the prior year).
- **Diagnosis:** a **retrieval-precision** regression, not a structural one. The
  agent searched `search_sections(keyword="concentration")`, which matched
  **Note 10 – Concentrations of Credit Risk** (the *accounts-receivable*
  concentration disclosure) rather than the *net-revenue* customer-concentration
  disclosure the gold answer cites. The 10-K has two distinct "concentration"
  notes; the improved (more direct) TOC led the agent to search-and-stop on Note
  10, where Phase 1.2's heavier probing (15 calls) happened to surface the revenue
  figure. The answer is directionally correct ("yes, concentration exists") and
  fully grounded, hence **partial**, not **incorrect**.
- **Fix direction:** a `search_sections` alias/thesaurus (e.g. "customer
  concentration" → also probe "net revenue", "significant customer", revenue
  disaggregation) or returning sibling concentration notes together.

## Trajectory analysis (Phase 1.3)

**Tool frequency (7 questions, 29 calls):** `get_section_content` 11,
`get_folder_toc` 7, `search_sections` 5, `get_document_toc` 4, `read_file` 2
(overflow pagination only). vs Phase 1.2 (38 calls): `search_sections`
11→5 (−55%), `get_section_content` 14→11, `get_document_toc` 5→4,
`get_folder_toc` 7→7. Total −24%.

**Why cost fell further:** the restored heading levels + concrete descriptions let
the agent pick the right section from the TOC *first time* — fewer
`search_sections` probes (5 vs 11) and fewer `get_document_toc` re-maps. Every
question still opens with `get_folder_toc` (orient), then either
`get_document_toc` (map) or `search_sections` (target), then
`get_section_content` (read), then answer citing `[hash::seq]`.

**Navigation nuance:** on the two broadest questions (`_00917` operating margin,
`_01198` revenue drivers) the agent read 3–4 sections each (the highest call
counts, 5/q) — these genuinely span multiple MD&A sub-sections, so the extra
reads are warranted, not waste.

## Caveats & findings (Phase 1.3)

1. **`_00757` retrieval precision** — see regression detail above. The single
   accuracy/numeric loss; directionally correct and grounded.
2. **`_00995` overflow `read_file` (2 calls)** — both target
   `/large_tool_results/<call_id>` with `offset`/`limit`: deepagents' pagination of
   a large graph-retrieved `get_section_content` result, not filesystem access (no
   corpus leak). Same residual as 1.2.
3. **Judge numeric classification** — 3 questions classified numeric (unchanged
   from 1.2); 2/3 matched.
4. **YAML serialization was a real CLI bug** (now fixed) — the agent-facing path
   was never affected, but `cli docgraph toc --yaml` had been emitting unparseable
   YAML whenever a description/summary line wrapped past the terminal width.

## Improvement backlog (Phase 1.3 → next)

1. **`search_sections` thesaurus / concentration-class probe** — directly
   addresses the `_00757` regression: expand a keyword to its disclosure-class
   aliases so one search surfaces all concentration notes (A/R + net revenue).
2. **Larger question set** — 7 questions on one 10-K is still thin; expand to
   multiple filings to stress cross-document routing.
3. **Table/line-item node type** — make balance-sheet line items first-class
   retrievable so numeric questions don't require reading+parsing whole statement
   Markdown.
4. **Overflow `read_file` provenance** — annotate the `/large_tool_results/` path
   so traces make its non-filesystem nature explicit.

## Reproducing Phase 1.3

```bash
# Hybrid-v2 outline rebuild from the existing OCR markdown (1 LLM call, cache cold after policy-hash bump):
uv run python -m financebench.bench.build_graph --skip-ocr --force --llm
# Graph-only, temperature-0 run + judge:
uv run python -m financebench.bench.run_questions
uv run python -m financebench.bench.grade
```

Outline cache: `data/kg/financebench_tree_outlines/deepseek_v4flash_openrouter__5cab039c8230/`
(gitignored). The `genai-graph` changes (`tree_parser`, `outline_extract`,
`commands_docgraph`) are committed alongside this report.
