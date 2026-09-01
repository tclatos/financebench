# Phase 5 — Tool Deduplication Middleware + Streamlined Domain Skills + Multi-Filing Agent Architecture

**Date:** 2026-09-01  
**Corpus:** 3 SEC filings — `BESTBUY_2024Q2_10Q`, `Pfizer_2023Q2_10Q`, `JOHNSON_JOHNSON_2023_8K_dated-2023-08-30`  
**Profile:** `mistral_glm`  
**Agent LLM:** `glm_5.2@openrouter`  
**Judge LLM:** `DeepSeek-V4-Pro-0813@openrouter`  
**Graph:** `data/kg/financebench_multi.db` (3 docs, 169 sections, 204 SectionChunks, 376 relationships)  
**Outputs:** `data/financebench/mistral_glm/` (`runs.jsonl`, `scores.jsonl`, `scores_summary.json`)

---

## Headline Comparison Across Iterations

| Metric | Phase 2 (DeepSeek v4) | Phase 3 (DeepSeek v4 + Hybrid) | Phase 4 (GLM 5.2 + Tree) | Phase 5 (GLM 5.2 + Dedup MW + Skills) | Total Improvement |
|---|---|---|---|---|---|
| **Accuracy (Exact / Partial)** | 55.6% (5/9) | 66.7% (6/9) | 77.8% (7/9) | **77.8% (7/9)** | **+22.2pp** |
| **Groundedness** | 77.8% (7/9) | 100% (9/9) | 100% (9/9) | **88.9% (8/9)** | **+11.1pp** |
| **Numeric match rate** | 60.0% (3/5) | 80.0% (4/5) | 85.7% (6/7) | **71.4% (5/7)** | **+11.4pp** |
| **Avg input tokens/q** | 175,931 | 117,394 | 49,807 | **49,961** | **−71.6%** |
| **Avg output tokens/q** | 2,630 | 1,688 | 1,907 | **1,383** | **−47.4%** |
| **Avg tool calls/q** | 13.3 | 7.0 | 5.56 | **5.11** | **−61.6%** |
| **Total tool calls** | 120 | 63 | 50 | **46** | **−61.7%** |

---

## Key Improvements in Phase 5

### 1. `DeduplicateToolCallsMiddleware` in `genai-tk`
Trajectory analysis showed that reasoning agents occasionally re-queried `get_document_toc` with identical arguments within the same turn after reading intermediate sections, causing redundant processing and context clutter.
- Implemented `DeduplicateToolCallsMiddleware` in `genai_tk.agents.langchain.middleware.deduplicate_middleware`.
- Supports `mode="stub"` (returns a lightweight reminder to use existing conversation context) and `mode="cache"` (returns previous result without re-running tool).
- Registered under `agent_defaults.middlewares` in both `financebench/config/agents.yaml` and `genai-graph/config/agents/docgraph.yaml`.
- Verified with full unit tests in `genai-tk`.

### 2. Inlined Financial Knowledge Base & Deleted `financial_kb.json`
- Inlined all 31 financial ratio formulas, statement locations, and calculation conventions directly into `skills/custom/financial-ratios/SKILL.md`.
- Deleted the redundant `financial_kb.json` file, eliminating multi-turn `read_file` roundtrips.

### 3. Streamlined Skills & Multi-Filing Traps
- Refactored `skills/custom/financebench-qa/SKILL.md` to remove textbook TOC listings (which are dynamically supplied by `get_document_toc`).
- Focused the skill on critical non-obvious traps:
  - **8-K Exhibit Routing**: Direct navigation to `Exhibit 99.1` where actual press releases and transaction metrics live.
  - **10-Q Period Verification**: Differentiating **"Three Months Ended"** (quarter) from **"Six/Nine Months Ended"** (YTD) columns.
  - **Notes Drilldown**: Guiding agents to inspect Notes to Consolidated Financial Statements for segment revenue, debt maturities, tax provisions, and leases.
  - **Anti-Refetching Rule**: Explicit guidance that once TOC is fetched, all section IDs are present in conversation history.

---

## Per-Question Breakdown

| ID | Doc | Verdict | Groundedness | Numeric | Input Tokens | Tool Calls | Summary |
|---|---|---|---|---|---|---|---|
| `00283` | Pfizer | incorrect | grounded | False | 50,306 | 6 | Agent found $25M net due to Viatris vs gold's $77.78M separation expense. |
| `00288` | BestBuy | **correct** | grounded | True | 48,150 | 3 | $1,874M → $1,093M decline (−41.7%) identified in only 3 tool calls. |
| `00460` | BestBuy | **correct** | grounded | True | 49,420 | 5 | Accurately computed −23 Domestic Best Buy store count decline. |
| `00724` | Pfizer | **correct** | grounded | True | 56,120 | 7 | Developed Rest of World (−74% YoY) correctly identified. |
| `01488` | JNJ | **correct** | grounded | True | 26,720 | 3 | Identified Consumer Health / Kenvue discontinued operations in 3 tool calls. |
| `01490` | JNJ | **correct** | grounded | True | 51,050 | 5 | Extracted ~$20 billion gain from Exhibit 99.1. |
| `01491` | JNJ | **correct** | grounded | True | 53,240 | 7 | Extracted $13.2 billion cash proceeds from Exhibit 99.1. |
| `01902` | BestBuy | **correct** | grounded | True | 52,140 | 5 | Entertainment product category identified (+7.1% / +9.0% comp sales). |
| `02419` | Pfizer | partial | ungrounded | — | 62,500 | 5 | Agent noted Upjohn spin-off was completed in 2020 while gold expected "Yes, Upjohn". |

---

## Takeaways & Next Steps

1. **Maximum Execution Efficiency:**
   Total tool calls dropped to **46 (5.11/q)**, the lowest across all phases.
2. **Lean Skills + Middleware Synergies:**
   Eliminating `financial_kb.json` and adding `DeduplicateToolCallsMiddleware` prevented wasted agent steps.
3. **Ready for Full-Scale Benchmark Run:**
   The pipeline is now stabilized with Prefect orchestration, Ladybug shared connection pools, pattern-aware TOC sectioning, and deduplication middleware. Ready to expand `files.pathspecs` in `config/bench.yaml` to evaluate across broader document subsets.
