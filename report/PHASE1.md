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
