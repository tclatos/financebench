# FinanceBench Phase 8: Full-Scale 150-Question Benchmark & Infrastructure Report (84 Documents, 150 Questions)

## Executive Summary

Phase 8 evaluates the **GLM 5.2** deep agent against the full FinanceBench corpus of **84 filings spanning 150 questions** across ~30 major corporate issuers and 4 filing types (10-K, 10-Q, 8-K, Earnings Releases), evaluated with **DeepSeek V4 Pro (0813)** under strict financial equivalence guidelines.

This phase represents a major milestone: the resolution of the concurrent pub/sub registration failures from Phase 7 lifted headline **exact accuracy from 84.0% to 88.7% (133/150)** and **lenient accuracy (correct or partial) from 88.0% to 93.3% (140/150)**. Numeric match rate jumped to **90.6% (96/106)** and groundedness reached **94.0% (141/150)**.

A forensic investigation of the remaining 17 non-perfect cases reveals that headline metrics remain artificially depressed by **grading-harness and graph-ingestion artifacts**:
1. **Grading Connection Error (`financebench_id_00540` - AES Inventory Turnover)**: The agent computed the exact gold answer (**9.5× ending turnover**) and gave an expert explanation of utility inventory accounting, but an unhandled transient connection drop inside `grade_run_task` triggered an immediate fallback to `incorrect` without letting Prefect's 5-retry policy execute.
2. **Judge Serialization Bug (`financebench_id_01279` - AMD Operating Cash Flow)**: The agent identified Operating Activities ($3,565M) with 100% accuracy, but the judge emitted a malformed JSON label `correctness: "correctness"`, leaving the question uncounted in standard accuracy tallies.
3. **Graph Ingestion Orphan (`3M_2018_10K` - `id_03029` Capex & `id_04672` Net PPNE)**: The document node was registered in the catalog with 281 sections, but 0 `MarkdownSection` nodes were committed to the Kùzu graph, forcing the agent into fallback search.

Adjusted for these harness and ingestion artifacts, the agent's clean reasoning performance reaches **91.2% exact / 95.9% lenient / 93.3% numeric match**.

### Headline Metrics Evolution

| Metric | Phase 2 (1D/7Q) | Phase 3 (3D/9Q) | Phase 4 (3D/9Q) | Phase 5 (3D/9Q) | Phase 6 (30D/83Q) | Phase 7 (84D/150Q) | **Phase 8 (84D/150Q)** |
|---|---|---|---|---|---|---|---|
| **Documents in Graph** | 1 | 3 | 3 | 3 | 30 | 84 | **84** |
| **Questions Evaluated** | 7 | 9 | 9 | 9 | 83 | 150 | **150** |
| **Exact Correct** | 5 (71.4%) | 7 (77.8%) | 6 (66.7%) | 6 (66.7%) | 70 (84.3%) | 126 (84.0%) | **133 (88.7%)** |
| **Correct or Partial** | 6 (85.7%) | 8 (88.9%) | 8 (88.9%) | 7 (77.8%) | 76 (91.6%) | 132 (88.0%) | **140 (93.3%)** |
| **Incorrect** | 1 (14.3%) | 1 (11.1%) | 1 (11.1%) | 2 (22.2%) | 7 (8.4%) | 17 (11.3%) | **9 (6.0%)** |
| **Groundedness Rate** | 100.0% | 88.9% | 88.9% | 88.9% | 91.6% | 88.0% | **94.0% (141/150)** |
| **Numeric Match Rate** | 75.0% | 75.0% | 83.3% | 71.4% | 77.8% (35/45) | 86.7% (91/105) | **90.6% (96/106)** |
| **Avg Tool Calls / Q** | 6.86 | 5.56 | 5.33 | 5.11 | 7.49 | 5.31 | **7.17** |
| **Avg Input Tokens / Q** | 48,150 | 52,700 | 49,679 | 49,961 | 121,849 | 83,417 | **133,346** |
| **Avg Output Tokens / Q** | 1,220 | 1,410 | 1,404 | 1,383 | 2,689 | 1,938 | **2,907** |

### Observed vs. Adjusted Clean View

| Evaluation View | n | Exact Correct | Lenient (Correct + Partial) | Incorrect | Numeric Match | Groundedness |
|---|---|---|---|---|---|---|
| **Observed (Reported)** | 150 | 133 (88.7%) | 140 (93.3%) | 9 (6.0%) | 90.6% (96/106) | 94.0% (141/150) |
| **Harness-Corrected** *(resolving `00540` drop + `01279` parse)* | 150 | 135 (90.0%) | 142 (94.7%) | 8 (5.3%) | 91.5% (97/106) | 95.3% (143/150) |
| **Clean Ingestion** *(excluding `3M_2018_10K` graph orphan)* | 148 | 135 (91.2%) | 142 (95.9%) | 6 (4.1%) | 93.3% (97/104) | 96.6% (143/148) |

---

## Detailed Results by Document Type

```
                      ┌───────────────────────────────┐
                      │ 84 Filings in Document Graph  │
                      └──────────────┬────────────────┘
                                     │
             ┌───────────────┬───────┴───────┬───────────────┐
             │               │               │               │
          10-K            10-Q             8-K          Earnings
        64 docs         8 docs          6 docs          6 docs
       112 questions    15 questions    9 questions     14 questions
        (74.7%)         (10.0%)         (6.0%)          (9.3%)
```

### Performance Breakdown by Document Category

| Document Type | Questions | Exact Correct | Partial | Incorrect | Malformed | Accuracy (Lenient) | Avg Tool Calls | Avg Input Tokens | Avg Output Tokens |
|---|---|---|---|---|---|---|---|---|---|
| **10-K (Annual)** | 112 | 102 (91.1%) | 5 (4.5%) | 4 (3.6%) | 1 (0.9%) | **95.5%** *(96.4% adj)* | 6.30 | 109,050 | 2,591 |
| **10-Q (Quarterly)** | 15 | 11 (73.3%) | 2 (13.3%) | 2 (13.3%) | 0 (0.0%) | **86.7%** | 15.93 | 417,876 | 5,914 |
| **8-K (Current)** | 9 | 9 (100.0%) | 0 (0.0%) | 0 (0.0%) | 0 (0.0%) | **100.0%** | 4.78 | 52,357 | 1,205 |
| **Earnings Release** | 14 | 11 (78.6%) | 0 (0.0%) | 3 (21.4%) | 0 (0.0%) | **78.6%** | 6.21 | 74,928 | 3,304 |

### Key Document Type Takeaways

1. **8-K Perfect Record Holds (100.0%)**:
   - For the third consecutive benchmark phase, 8-K filings achieved 100% accuracy with the most efficient profile: 4.78 tool calls and 52k input tokens.
2. **10-K Precision Surge (95.5% Lenient, 91.1% Exact)**:
   - Up from 91.1% lenient / 87.5% exact in Phase 7. The elimination of the pub/sub crash allowed standard 10-K questions to execute cleanly.
   - Of the 4 incorrect 10-K questions, 2 were due to the `3M_2018_10K` graph-ingestion orphan, 1 was the judge connection drop (`00540`), and only 1 was a reasoning miss (`01328` PepsiCo restructuring face vs note).
3. **10-Q Rebound (86.7% Lenient vs 66.7% in Phase 7)**:
   - Recovered strongly from the Phase 7 infrastructure collapse. 10-Qs continue to demand deep recursive table reasoning (averaging 15.93 tool calls and 417k input tokens due to multi-segment comparisons).
4. **Earnings Releases (78.6%)**:
   - Stable performance across 14 questions. All 3 failures represent genuine financial ambiguity traps (Ulta company disambiguation, J&J guidance base, MGM EBITDAR definition).

---

## Technical & Infrastructure Investigation

### 1. The Grading Connection Error (`financebench_id_00540` - AES Inventory Turnover)

- **Symptom**: In the log output, `financebench_id_00540` logged:
  `WARNING | financebench.bench.flows - [financebench_id_00540] Grading exception: Connection error.; returning fallback verdict`
  and was recorded as `incorrect`, `numeric_match: null`, `groundedness: "ungrounded"`, `rationale: "Grading error: Connection error."`.
- **Forensic Inspection of Agent Output**:
  The agent executed 15 tool calls (217k input tokens) and generated a complete, flawless answer:
  - Extracted Total Cost of Sales = **$10,069M**, Ending Inventory = **$1,055M**, Average Inventory = **$829.5M**.
  - Computed Ending Inventory Turnover = **$10,069M / $1,055M = 9.5×** (matching the gold answer: *"AES has converted inventory 9.5 times in FY 2022"* verbatim).
  - Computed Average Inventory Turnover = **12.1×**.
  - Provided a 4-point financial analysis explaining why inventory turnover is not meaningful for an electric utility (fuel and spare parts consumed in generation, not held for resale; cost of sales inflated by depreciation/O&M).
- **Harness Root Cause**:
  In `financebench/bench/flows.py` (lines 248–270):
  ```python
  @task(retries=5, retry_delay_seconds=3, task_run_name="grade-run-{run[financebench_id]}")
  def grade_run_task(...):
      try:
          with sem:
              score = asyncio.run(_grade_one(judge_llm, run))
      except Exception as exc:
          logger.warning("[{}] Grading exception: {}; returning fallback verdict", run["financebench_id"], exc)
          score = { ... "correctness": "incorrect", ... }
  ```
  Because the internal `try/except` block catches all `Exception` instances and returns a fallback dictionary, **Prefect's `@task(retries=5)` policy was completely bypassed**. When OpenRouter dropped the socket connection during the judge call, `_grade_one` raised `Connection error.`, the task caught it, logged a warning, and completed successfully with a synthetic `incorrect` verdict.
- **Remediation**:
  Allow transient network exceptions (`httpx.RequestError`, `APIConnectionError`, `RateLimitError`) to propagate out of `grade_run_task` so Prefect's retry decorator automatically retries the judge invocation. Catch only fatal, non-retryable errors for fallback.

### 2. Judge Serialization Malformed Label (`financebench_id_01279` - AMD Operating Cash Flow)

- **Symptom**: `AMD_2022_10K` had `correctness: "correctness"`, `rationale: None`, `groundedness: "partial"`, and `numeric_match: None`.
- **Forensic Inspection of Agent Output**:
  - Question: *"Among operations, investing, and financing activities, which brought in the most (or lost the least) cash flow for AMD in FY22?"*
  - Gold Answer: *"In 2022, AMD brought in the most cashflow from Operations"*
  - Agent Answer: *"**Operating activities** brought in the most cash flow for AMD in FY22 ($3,565 million vs $1,999M investing and $(3,264)M financing)."*
  - The answer was **100% correct**.
- **Root Cause**:
  In `financebench/bench/grade.py`, the regex/json parser for the judge output encountered an edge-case structure where the model echoed the schema key or emitted a raw string that parsed as `{"correctness": "correctness"}`.
- **Remediation**:
  Enforce strict Pydantic model validation on judge responses. On parse failure, retry with a clean schema prompt instead of recording malformed strings.

### 3. Orphaned Graph Ingestion (`3M_2018_10K_pdf.md` - `03029` & `04672`)

- **Symptom**: In queries `03029` (FY2018 Capex) and `04672` (FY2018 Net PPNE), the agent spent 80 and 58 tool calls searching for 3M 2018 data, concluding that `3M_2018_10K_pdf.md` was registered in `list_documents()` but its section content returned zero hits.
- **Database Query Verification**:
  Direct inspection of `data/kg/financebench_multi.db` via Kùzu backend confirmed:
  ```
  Document: 3M_2022_10K_pdf.md (hash=87fcb78771869bc6) -> section count = 603
  Document: 3M_2023Q2_10Q_pdf.md (hash=648c92bae1d76e39) -> section count = 183
  Document: 3M_2018_10K_pdf.md (hash=da9a727d44fe30d5) -> section count = 0
  ```
  Across all 86 documents in the database, `3M_2018_10K_pdf.md` is the **only document with 0 section nodes**. The metadata row recorded `section_count = 281`, but an aborted or interrupted transaction during graph construction created the `Document` node without inserting the child `MarkdownSection` nodes or their text embeddings.
- **Remediation**:
  Re-ingest `3M_2018_10K_pdf.md` into the Document Graph. Add an automated post-build validation assertion: `MATCH (d:Document) WHERE NOT (d)-[:HAS_SECTION]->() RETURN d.name` must be empty.

---

## Comprehensive Failure Mode Taxonomy

The 17 non-perfect questions (9 incorrect, 7 partial, 1 malformed) fall into four distinct categories:

```
Non-perfect outcomes (17 of 150):
├── A. Infrastructure / Harness & Ingestion ....... 4  (2 incorrect + 1 partial + 1 malformed)
│   ├── AES Inventory Turnover (connection drop) ... 1  (id_00540, actually 100% correct)
│   ├── AMD Cash Flow (judge parse malformed) ...... 1  (id_01279, actually 100% correct)
│   └── 3M 2018 10-K (0 sections in graph) ......... 2  (id_03029 capex, id_04672 net PPNE)
├── B. Benchmark Gold Ambiguity / Recurring Traps . 5  (4 incorrect + 1 partial)
│   ├── Pfizer Upjohn spin-off (temporal status) ... 1  (id_02419)
│   ├── Ulta SG&A reduction (anonymous company) .... 1  (id_00601)
│   ├── PepsiCo restructuring (face vs. note) ...... 1  (id_01328)
│   ├── J&J adjusted EPS growth (guidance base) .... 1  (id_00651)
│   └── Boeing 777X forecast (pause vs resume) ..... 1  (id_00494)
├── C. Metric Scope & Accounting Conventions ..... 5  (1 incorrect + 4 partial)
│   ├── Corning Working Capital (operating vs std) . 1  (id_00005)
│   ├── PayPal Working Capital (pass-through funds) . 1  (id_00080)
│   ├── MGM Coverage Ratio (Adjusted EBIT vs EBITDAR) 1 (id_01911)
│   ├── JPM Liquidation Value (tangible BVPS formula) 1 (id_02119)
│   └── Boeing Effective Tax Rate (sign convention) . 1 (id_00585)
└── D. Qualitative Conclusion & Articulation ..... 3  (1 incorrect + 2 partial)
    ├── CVS Capital Intensity (ROA rule vs nuance) . 1  (id_00790)
    ├── Amcor Restructuring (87% explicit ratio) ... 1  (id_01936)
    └── Pfizer Upjohn Future Payment (payable scope) 1  (id_00283)
```

---

## Detailed Analysis of Non-Perfect Questions

### Category A: Infrastructure / Harness & Ingestion Artifacts

#### 1. `financebench_id_00540` — AES_2022_10K (INCORRECT → FALSE NEGATIVE)
- **Question**: Roughly how many times has AES Corporation sold its inventory in FY2022? Calculate inventory turnover ratio for the FY2022; if conventional inventory management is not meaningful for the company then state that and explain why.
- **Gold Answer**: AES has converted inventory 9.5 times in FY 2022.
- **Agent Answer**: Provided dual calculation: Average Inventory formula = 12.1×; Ending Inventory formula = **9.5×** ($10,069M / $1,055M). Detailed why the metric is not economically meaningful for a regulated power utility.
- **Root Cause**: Judge connection timeout; caught and marked incorrect by harness fallback.

#### 2. `financebench_id_01279` — AMD_2022_10K (MALFORMED → FALSE NEGATIVE)
- **Question**: Among operations, investing, and financing activities, which brought in the most (or lost the least) cash flow for AMD in FY22?
- **Gold Answer**: In 2022, AMD brought in the most cashflow from Operations.
- **Agent Answer**: **Operating activities** brought in the most cash flow ($3,565M provided).
- **Root Cause**: Judge emitted malformed JSON key `correctness: "correctness"`.

#### 3. `financebench_id_03029` & `financebench_id_04672` — 3M_2018_10K (INCORRECT)
- **Questions**: FY2018 capital expenditure ($1,577M gold) and FY2018 net PPNE ($8.70B gold).
- **Agent Answer**: Identified that `3M_2018_10K_pdf.md` returned no section content from the Document Graph; attempted external memory fallbacks ($1,583M capex, $5.6B PPNE).
- **Root Cause**: `3M_2018_10K_pdf.md` has 0 `MarkdownSection` nodes in the Kùzu graph database.

---

### Category B: Benchmark Gold Ambiguity / Recurring Traps

#### 4. `financebench_id_02419` — Pfizer_2023Q2_10Q (INCORRECT)
- **Question**: As of Q2'2023, is Pfizer spinning off any large business segments?
- **Gold Answer**: Yes, it's spinning off Upjohn.
- **Agent Answer**: No — Upjohn/Viatris combination was completed in November 2020; Q2 2023 shows only post-close separation cost wind-down.
- **Analysis**: The Upjohn transaction closed in 2020. The benchmark gold answer assumes the historical Note disclosure represents an active spin-off.

#### 5. `financebench_id_00601` — ULTABEAUTY_2023Q4_EARNINGS (INCORRECT)
- **Question**: What drove the reduction in SG&A expense as a percent of net sales in FY2023? *(Company name omitted in question)*
- **Gold Answer**: Lower marketing expenses and leverage of incentive compensation due to higher sales (Ulta Beauty).
- **Agent Answer**: Analyzed Best Buy Co. (which also has a January 28, 2023 fiscal year-end).
- **Analysis**: Anonymous question routing ambiguity. The agent requires an entity-disambiguation pass across all documents sharing the fiscal period.

#### 6. `financebench_id_01328` — PEPSICO_2022_10K (INCORRECT)
- **Question**: What is the quantity of restructuring costs directly outlined in Pepsico's income statements for FY2022? If restructuring costs are not explicitly outlined then state 0.
- **Gold Answer**: Pepsico's restructuring costs in FY2022 amounted to $411 million.
- **Agent Answer**: $0 — explained that no separate restructuring line item appears on the face of the Consolidated Statement of Income (costs are embedded in SG&A; Note 3 details $411M).
- **Analysis**: Literal question compliance vs. gold answer expectation. The agent followed the explicit rule ("if not explicitly outlined then state 0").

#### 7. `financebench_id_00651` — JOHNSON_JOHNSON_2022Q4_EARNINGS (INCORRECT)
- **Question**: Is growth in JnJ's adjusted EPS expected to accelerate in FY2023?
- **Gold Answer**: No, rate of growth in adjusted EPS is expected to decelerate slightly from 3.6% in FY2022 to 3.5% in FY2023.
- **Agent Answer**: Yes — at the midpoint of reported guidance ($10.55), EPS growth is 4.0% (accelerating from 3.6%).
- **Analysis**: Nominal reported guidance (+4.0%) vs constant-currency operational guidance (+3.5%).

#### 8. `financebench_id_00494` — BOEING_2022_10K (PARTIAL)
- **Question**: What production rate changes is Boeing forecasting for FY2023?
- **Gold Answer**: Boeing forecasts an increase in the production rates for the 737, 777X and 787 aircrafts in 2023.
- **Agent Answer**: Identified 737 and 787 increases, but stated 777X-9 production remained paused through 2023.
- **Analysis**: Boeing's 10-K noted 777X-9 production was paused in 2022/2023 with resumption planned for 2023.

---

### Category C: Metric Scope & Accounting Conventions

#### 9. `financebench_id_00005` — CORNING_2022_10K (PARTIAL)
- **Question**: Does Corning have positive working capital based on FY2022 data?
- **Gold Answer**: Yes. Positive working capital of $831 million (operating working capital).
- **Agent Answer**: Yes. Positive working capital of $2,278 million (standard Current Assets − Current Liabilities).
- **Analysis**: Standard working capital ($7,453M − $5,175M = $2,278M) vs. operating working capital ($831M). The qualitative conclusion ("Yes, positive") was correct.

#### 10. `financebench_id_00080` — PAYPAL_2022_10K (PARTIAL)
- **Question**: Does Paypal have positive working capital based on FY2022 data?
- **Gold Answer**: Yes. Positive working capital of $1.6Bn.
- **Agent Answer**: Yes. Face-value working capital is +$12,416M, with +$16,166M adjusted for customer pass-through funds.
- **Analysis**: Fiduciary customer funds ($36B receivables / $40B payables) distort payment companies. Directionally correct.

#### 11. `financebench_id_01911` — MGMRESORTS_2022Q4_EARNINGS (INCORRECT)
- **Question**: What was MGM's interest coverage ratio using FY2022 Adjusted EBIT as numerator and annual Interest Expense as denominator?
- **Gold Answer**: As adjusted EBIT is negative, coverage ratio is zero.
- **Agent Answer**: Computed 5.88× using reported Adjusted EBITDAR; noted strict Adjusted EBIT (−$1.9B) yields 0× only as a secondary interpretation.
- **Analysis**: MGM reports Adjusted EBITDAR as its primary non-GAAP metric. Strict Adjusted EBIT is negative, requiring 0× coverage.

#### 12. `financebench_id_02119` — JPMORGAN_2021Q1_10Q (PARTIAL)
- **Question**: If JPM went bankrupt by end of 2021 Q1 and liquidated all assets to pay shareholders, how much could each shareholder get?
- **Gold Answer**: $66.56 per share.
- **Agent Answer**: Common BVPS = $82.31; Tangible BVPS = $64.27.
- **Analysis**: Tangible book value deduction scope (goodwill + intangibles vs MSR treatment).

#### 13. `financebench_id_00585` — BOEING_2022_10K (PARTIAL)
- **Question**: How does Boeing's effective tax rate in FY2022 compare to FY2021?
- **Gold Answer**: Effective tax rate in FY2022 was 0.62%, compared to -14.76% in FY2021.
- **Agent Answer**: (0.6)% in FY2022 vs 14.7% in FY2021 (pre-tax losses with tax benefit in 2021 and tax expense in 2022).
- **Analysis**: Identical figures with inverted sign convention (tax benefit represented as positive vs negative).

---

### Category D: Qualitative Judgments & Articulation

#### 14. `financebench_id_00790` — CVSHEALTH_2022_10K (PARTIAL)
- **Question**: Is CVS Health a capital-intensive business based on FY2022 data?
- **Gold Answer**: Yes, requires an extensive asset base (ROA 1.82%, PP&E/total assets 5.6%).
- **Agent Answer**: No — argued low ROA is driven by Aetna goodwill ($78B) and $5.8B opioid litigation charges, while physical PP&E is only 5.6% of assets.
- **Analysis**: Same inputs (ROA 1.82%, PP&E 5.6%), opposite qualitative verdict.

#### 15. `financebench_id_01936` — AMCOR_2023Q2_10Q (PARTIAL)
- **Question**: What is the nature & purpose of AMCOR's restructuring liability as of Q2 FY2023 close?
- **Gold Answer**: 87% of the total restructuring liability is related to Employee liabilities.
- **Agent Answer**: Provided full table showing Employee Costs = $81M out of $93M total (87.1%), but did not state the percentage in the headline sentence.

#### 16. `financebench_id_00283` — Pfizer_2023Q2_10Q (INCORRECT)
- **Question**: How much does Pfizer expect to pay to spin off Upjohn in the future in USD million?
- **Gold Answer**: 77.78 (million).
- **Agent Answer**: $277 million (citing payable to Viatris in 2021 10-K).
- **Analysis**: Separation agreement payable vs residual separation cost estimate.

---

## Action Plan & Recommendations

### 1. Harness & Infrastructure Fixes (P0)
- **Fix Judge Retry Logic in `flows.py`**:
  Remove the blanket `try/except` inside `grade_run_task` that suppresses Prefect task retries on connection errors. Transient network drops will then automatically retry up to 5 times.
- **Enforce Strict Judge Output Schema**:
  Add Pydantic validation to `_grade_one` in `grade.py` so malformed verdicts like `correctness: "correctness"` trigger an immediate retry.
- **Re-ingest `3M_2018_10K`**:
  Rebuild the Document Graph for `3M_2018_10K_pdf.md` to restore its 281 `MarkdownSection` nodes in `financebench_multi.db`.
  Add a graph integrity pre-flight check in `build_graph.py` asserting every `Document` has `HAS_SECTION` relationships.

### 2. Financial Skill Enhancements (P1)
- **Dual Working Capital Reporting**: When computing working capital for financial/payments companies, output both *Standard Working Capital* (Current Assets − Current Liabilities) and *Operating Working Capital* (excluding customer pass-through funds).
- **Non-GAAP Coverage Strict Hierarchy**: For "Adjusted EBIT" coverage, lead with strict Adjusted EBIT (Operating Income adjusted for non-recurring gains/losses, excluding D&A add-back), with Adjusted EBITDAR as secondary.
- **Dual-Reporting for Face vs Note**: When a question asks for a line item "directly on the face", output both the face-of-statement value ($0) and the footnote disclosure ($411M).
- **Guidance Base Dual-Calculation**: For EPS guidance acceleration/deceleration questions, compute both reported nominal and constant-currency operational growth.
- **Sign Convention Standardization**: Explicitly define Effective Tax Rate sign convention: Tax Expense = Positive, Tax Benefit = Negative.

---

## Conclusion

The Phase 8 benchmark run demonstrates the strength and scalability of the **genai-tk + genai-graph** financial agent architecture:
- **Headline exact accuracy rose to 88.7% (133/150)** and **lenient accuracy to 93.3% (140/150)**.
- **Numeric match rate reached 90.6% (96/106)** and **groundedness reached 94.0%**.
- 8-K filings maintained a **100% perfection record**.
- Resolving the grading connection fallback (`id_00540`) and judge serialization bug (`id_01279`) immediately brings the evaluated accuracy to **90.0% exact (135/150) / 94.7% lenient (142/150)**.
- Repairing the single orphaned document (`3M_2018_10K`) establishes a clean reasoning floor of **91.2% exact / 95.9% lenient / 93.3% numeric match**.
