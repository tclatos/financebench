# FinanceBench Phase 2 — File tools + skills + multi-document evaluation

**Date:** 2026-08-26
**Trigger:** Phase 1.x validated the Document Graph + agentic search on a single filing
(AMD 10-K, 7 questions, 85.7–100%). Phase 2 scales out: a config-driven CLI, the
read-file tool **restored** so the skill system works again, a new `financial-ratios`
skill, and a **3-document corpus** (a 10-Q, another 10-Q, and an 8-K) answered
**corpus-wide** (`folder_id=None`) — the agent must pick the right filing itself.
**Scope:** `financebench` (new `bench/run.py` orchestrator + `config/bench.yaml`),
`config/agents.yaml` (docgraph profile), `skills/custom/{financebench-qa,financial-ratios}`.
**Agent / Build / Judge LLM:** `deepseek_v4flash@openrouter` (agent & judge at
temperature 0.0, unchanged from Phase 1.3 for a clean comparison).

## What was built (Phase 2)

1. **Config-driven bench orchestrator** — `financebench/bench/run.py`: a flat
   `BenchConfig` (Pydantic) loaded from `config/bench.yaml` that runs the pipeline
   `fetch → build → run → grade` for the configured docs into the configured paths.
   One command evaluates a new set of filings:
   `uv run python -m financebench.bench.run [--step run|grade|build|fetch] [--limit N] [--docs A,B]`.
   Individual step modules (`load_dataset`, `fetch_pdf`, `build_graph`,
   `run_questions`, `grade`) remain available.
2. **File tools restored (skills work again).** Phase 1.2/1.3 had to disable
   `read_file`/`grep`/`ls` for benchmark integrity (graph-only). Phase 2 re-enables
   them (`enable_file_system: true`) because progressive skill disclosure needs
   `read_file` to load `SKILL.md`. Benchmark integrity is preserved by a **corpus-access
   rule** in the docgraph system prompt: file tools are for skill/reference files
   *only*; the filings are reachable solely via the graph tools. The 10 `read_file`
   calls observed in the run are all skill/knowledge-base loads, not corpus access.
3. **`financial-ratios` skill** — `skills/custom/financial-ratios/` vendoring
   `NanoNets/nanoindex`'s `financial_kb.json` (31 metrics: quick ratio, ROE, EBITDA,
   FCF, DSO, …) behind a one-line index + a `read_file` lookup, so the agent gets
   exact numerator/denominator conventions instead of guessing (the Phase-1 `_00222`
   quick-ratio failure mode).
4. **Multi-document graph** — `data/kg/financebench_multi.db`: the three configured
   filings OCR'd (Mistral) → `data/markdown_multi/` → one hybrid-outline Document
   Graph (the Phase 1.2/1.3 hybrid-v2 build, 0 outline LLM calls on re-build).

| Document | Type | Sections |
|---|---|---|
| `Pfizer_2023Q2_10Q_pdf.md` | 10-Q | 187 |
| `BESTBUY_2024Q2_10Q_pdf.md` | 10-Q | 80 |
| `JOHNSON_JOHNSON_2023_8K_dated-2023-08-30_pdf.md` | 8-K | 26 |

## TL;DR (Phase 2)

| Metric | Phase 1.3 (1 doc, AMD 10-K) | Phase 2 (3 docs, corpus-wide) | Δ |
|---|---|---|---|
| Questions | 7 | 9 | — |
| **Accuracy (strict correct)** | 6/7 = 85.7% | **5/9 = 55.6%** | **−30 pts** |
| Accuracy (correct-or-partial) | 100% | 55.6% | −44 pts (0 partials) |
| Groundedness | 7/7 = 100% | **7/9 = 77.8%** | **−22 pts** (2 ungrounded) |
| Numeric match | 2/3 = 66.7% | 3/5 = 60% | −1 question |
| Avg tool calls / question | 4.14 | **13.33** | **+3.2×** |
| Avg input tokens / question | 49,035 | **175,931** | **+3.6×** |
| Avg output tokens / question | 1,540 | 2,630 | +1.7× |
| Agent temperature | 0.0 | 0.0 | reproducible |
| Agent errors | 0 | 0 | — |
| File-tool corpus access | 0 | 0 (10 `read_file` = skill loads) | graph-only holds |

The stack runs end-to-end on a multi-document corpus with zero errors and perfect
reproducibility, but **accuracy and groundedness both regress sharply** vs Phase 1.3,
and **cost inflates ~3.6×**. The regression is *not* uniform: it is concentrated on
the two 10-Q filings and on one pathological numeric question, and it is driven by a
single behaviour change — the agent **stops mapping the document TOC and over-searches
by keyword**. Details below.

## Per-document breakdown

| Document | Type | n | Accuracy | Grounded | Avg tool calls | Avg input tok |
|---|---|---|---|---|---|---|
| J&J 8-K | 8-K | 3 | **3/3 = 100%** | 3/3 | 9.7 | 95,902 |
| BestBuy 10-Q | 10-Q | 3 | 1/3 = 33% | 2/3 | 6.0 | 61,313 |
| Pfizer 10-Q | 10-Q | 3 | 1/3 = 33% | 2/3 | 24.3 | 370,578 |

The short, factual 8-K is answered perfectly. Both 10-Qs drop to 1/3. Pfizer alone
accounts for the cost blow-up (370k avg input tokens/q, vs 61–96k for the other two)
— entirely because of one question (`_00283`) that burned 912k input tokens.

## Per-question results

| financebench_id | Document | Verdict | Numeric | Grounded | Tool calls | In tok | Out tok |
|---|---|---|---|---|---|---|---|
| _00283 | Pfizer 10-Q | **incorrect** | False | grounded | 57 | 912,410 | 12,027 |
| _00288 | BestBuy 10-Q | **correct** ✅ | True | grounded | 7 | 64,487 | 1,387 |
| _00460 | BestBuy 10-Q | **incorrect** | False | ungrounded | 6 | 68,531 | 1,635 |
| _00724 | Pfizer 10-Q | **correct** ✅ | — | grounded | 6 | 99,237 | 1,516 |
| _01488 | J&J 8-K | **correct** ✅ | — | grounded | 6 | 92,311 | 1,062 |
| _01490 | J&J 8-K | **correct** ✅ | True | grounded | 11 | 92,853 | ~1.1k |
| _01491 | J&J 8-K | **correct** ✅ | True | grounded | 12 | 102,542 | ~1.2k |
| _01902 | BestBuy 10-Q | **incorrect** | — | grounded | 5 | 50,923 | ~1k |
| _02419 | Pfizer 10-Q | **incorrect** | — | ungrounded | 10 | 100,087 | ~1.5k |

The 5 correct answers are the easy, well-scoped ones (a yes/no cash drop, a named
geographic region, three factual J&J 8-K items). The 4 failures are a numeric-formula
error, a wrong-table retrieval, a question misread, and a tense/semantic denial —
analysed below.

## Failure analysis (the 4 incorrect)

### `_00283` — Pfizer Upjohn future separation cost (numeric + cost pathology)
- **Q:** How much does Pfizer expect to pay to spin off Upjohn in the future (USD m)?
- **Gold:** 77.78 (= 700 / 9).
- **Agent:** **$70 m** — it read the MD&A *"We expect to incur costs of approximately
  $700 million in connection with separating Upjohn, of which approximately 90% has
  been incurred … through Q2 2023"* and computed the remaining 10% = $70 m.
- **Diagnosis:** a **numeric-reasoning / decomposition error**: the agent used 10%
  (1/10) of $700 m where the gold decomposes the total over 9 periods (1/9 = $77.78 m).
  The exact remaining figure is not stated as a single number, so the agent had to
  infer the decomposition and chose the wrong one.
- **Cost pathology:** this one question used **57 tool calls and 912,410 input tokens
  (58% of the entire run's input cost)**, including **46 `search_sections`** calls.
  The agent spiralled: it even mused *"let me check … if there's a Pfizer 10-K in the
  corpus"* (there is none — it has the 10-Q). It never called `get_document_toc` to map
  the 187-section filing, so it re-searched blind ~46 times.

### `_00460` — BestBuy store-count change (retrieval precision)
- **Q:** Was there a change in the number of Best Buy stores between Q2 FY2024 and FY2023?
- **Gold:** Yes — decline of 1.32%, from 982 (Q2 FY23) to 969 (Q2 FY24).
- **Agent:** Yes — but gave **Domestic 930→907, International 127→128, Mobile 33→32**
  (sub-breakdowns by segment), never aggregating to the 982→969 total the gold cites.
- **Diagnosis:** the agent retrieved the store-count table but read the **wrong rows**
  (per-segment sub-totals for sub-periods instead of the company-total row), so its
  numbers are not the gold's totals → marked **ungrounded** (not supported by the gold
  evidence). A retrieval-precision failure, not a navigation failure.

### `_01902` — BestBuy "best-performing" category (question misread)
- **Q:** Which Best Buy product category performed the best **(by top line)** in the
  domestic market during Q2 FY2024?
- **Gold:** Entertainment — highest **growth** of 9% (from gaming).
- **Agent:** Computing and Mobile Phones — **largest by revenue** ($3,674 m), with a
  clean revenue-ranked table citing `[cd8db74b01f3b2fd::37]`.
- **Diagnosis:** a **semantic / question-misread**. The agent read "by top line" as
  "by the top-line (revenue) figure" → largest revenue. The gold means "best
  performing" = highest *growth*. The answer is well-grounded and internally coherent;
  it answers a defensible reading of an ambiguous question — but not the gold's reading.

### `_02419` — Pfizer spinning off a large segment (tense / cross-question inconsistency)
- **Q:** As of Q2 2023, is Pfizer spinning off any large business segments?
- **Gold:** Yes — it's spinning off Upjohn.
- **Agent:** **No** — it fixated on the Upjohn/Viatris legal spin-off being "already
  completed (2020)" and concluded no spin-off is occurring.
- **Diagnosis:** a **tense/semantic + retrieval failure**. The *same* MD&A section that
  `_00283`'s agent found says separation costs are **ongoing** ("~$700 m to separate
  Upjohn, ~90% incurred through Q2 2023") — so the separation is plainly still in
  progress as of Q2 2023. `_02419`'s agent did not connect this; it anchored on the 2020
  completion and answered "no". Marked **ungrounded** (contradicts the gold evidence).
  Notably this is a **cross-question inconsistency on the same filing**: `_00283`
  surfaced the ongoing-separation sentence while `_02419` ignored it.

## Trajectory & cost analysis

**Tool frequency (9 questions, 120 calls):** `search_sections` 69 (57%),
`get_section_content` 19, `read_file` 10 (skill/knowledge-base loads — Phase 2
file-tool restoration working as intended), `get_folder_toc` 9, `get_document_toc` 9,
`write_todos` 3, `list_documents` 1.

**The regression's mechanism — the agent stops mapping.** In Phase 1.3 every question
opened `get_folder_toc` (orient) → `get_document_toc` (map) → `get_section_content`
(read). In Phase 2 the agent calls `get_document_toc` only ~1×/question (9 total) and
**collapses to `search_sections`** (69 calls, 57% of all tool calls). On the easy
questions it still maps-then-reads (cheap, correct). On the hard ones — especially the
Pfizer 10-Q with 187 sections — it skips the map and **re-searches blind**, which is
both expensive (each broad search returns many large sections) and error-prone (it lands
on the wrong rows / misses the connecting fact). The skill and system prompt both say
"call `get_document_toc` first; do not chain searches" — deepseek-flash at temp 0 does
not reliably obey this under multi-document load.

**Cost concentration.** Total run: 1,583,381 input / 23,674 output tokens, 120 calls.
`_00283` alone = 912,410 input tokens (58%) and 57 calls (48%). **Excluding that one
outlier: 670,971 input tokens / 8 = 83,871 avg per question, 63 calls / 8 ≈ 7.9 avg**
— i.e. on the well-behaved 8 questions Phase 2 is only ~1.7× Phase 1.3's token cost and
~1.9× its tool calls, which is reasonable for larger, multi-document filings. The
headline 3.6× regression is essentially one runaway numeric question.

## Caveats & findings

1. **Groundedness is no longer perfect.** Phase 1.x had 100% groundedness across 7+
   7 + 7 questions; Phase 2 drops to 77.8% (2 ungrounded). Both ungrounded answers
   (`_00460`, `_02419`) are 10-Q questions where the agent retrieved the wrong rows or
   fixated on the wrong tense — i.e. the agent *did* read the filing but answered from
   the wrong part of it. The 8-K answers stayed 100% grounded.
2. **Skill system works again (Phase 2 goal met).** The 10 `read_file` calls are all
   `financebench-qa` / `financial-ratios` / `financial_kb.json` loads — zero corpus
   access via file tools. The corpus-access rule held; the graph is still the sole
   filing-retrieval path.
3. **Filing type matters more than question type.** All 9 questions are
   `novel-generated`; the split is by filing: 8-K 100%, 10-Qs 33%. The short, structured
   8-K (26 sections) is easy; the long 10-Qs (80–187 sections) expose the
   map-skipping / over-search behaviour.
4. **Judge numeric classification:** 5 questions classified numeric (Phase 1.3 had 3);
   3/5 matched. The two numeric misses are `_00283` (wrong decomposition) and `_00460`
   (wrong rows).
5. **`_01902` is partly a benchmark-ambiguity artifact:** "performed the best (by top
   line)" is genuinely ambiguous between "largest revenue" and "highest growth". The
   agent's reading is defensible; the gold's is the growth reading.

## Improvement backlog (Phase 2 → next)

1. **Enforce map-before-search (top priority — fixes both accuracy and cost).** The
   agent skipping `get_document_toc` is the root cause of the cost pathology (`_00283`,
   912k tok) and a contributor to the retrieval misses. Options: (a) a tool-ordering
   middleware that gates `search_sections` behind a `get_document_toc` call per
   document; (b) a stronger, few-shot system-prompt rule with an explicit "never
   `search_sections` before `get_document_toc`" hard prohibition; (c) cap consecutive
   `search_sections` calls (e.g. >3 without a `get_section_content` → force a
   `get_document_toc`). Re-run `_00283` to confirm the 912k→~baseline drop.
2. **`search_sections` thesaurus / disclosure-class probe** (carried from Phase 1.3).
   `_00460` and `_02419` would benefit from a keyword expanding to its disclosure
   class (e.g. "store count" → total/stores/domestic/international rows together;
   "spin off" → separation/discontinued/Upohn/Viatris) so one search surfaces the
   connecting fact instead of the agent fixating on the first hit.
3. **Numeric decomposition helper.** `_00283` is the Phase-2 analogue of Phase-1's
   `_00222` quick-ratio miss. A `financial-ratios`-style reference for "remaining
   future cost = total − incurred" and unit-fraction decompositions, plus a
   "compute-then-re-derive" self-check, would help. Also evaluate a stronger reasoning
   model (GPT-5/o3 class) on the numeric subset.
4. **Cross-question consistency / per-doc caching.** `_00224` and `_00283` both touch
   the Upjohn separation on the same filing but only one surfaced the ongoing-cost
   sentence. Consider a per-document "facts cache" so findings on a filing are reused
   across its questions.
5. **Table/line-item node type** (carried from 1.x). `_00460` read the wrong rows of a
   store-count table; first-class table/row nodes would make "the company-total store
   row" a retrievable object.
6. **Reproducible multi-doc recipe:** `just bench-multi` (load → fetch → build → run →
   grade → report) driven by `config/bench.yaml`, plus a frozen `runs.jsonl` /
   `scores.jsonl` snapshot for regression checks.

## Reproducing Phase 2

```bash
# Config: config/bench.yaml selects the 3 docs, corpus-wide (folder_id: null),
# deepseek_v4flash@openrouter for agent/build/judge, agent temp 0.
uv run python -m financebench.bench.run                 # fetch → build → run → grade
# Or step-by-step (build is cached — 0 outline LLM calls on re-run):
uv run python -m financebench.bench.run --step run      # 9 questions → runs.jsonl
uv run python -m financebench.bench.run --step grade    # LLM-as-judge → scores.jsonl
```

Artifacts (gitignored, under `data/`): `data/financebench/{questions,runs,scores}.jsonl`,
`data/kg/financebench_multi.db`, `data/markdown_multi/`. Agent profile:
`config/agents.yaml` `docgraph` (file tools on, corpus-access rule inlined, temp 0).
Outline cache: `data/kg/financebench_multi_outlines/` (gitignored).
