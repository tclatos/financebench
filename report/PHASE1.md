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
