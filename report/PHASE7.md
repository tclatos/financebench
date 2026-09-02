# FinanceBench Phase 7: Full-Scale 150-Document Benchmark Report (84 Documents, 150 Questions)

## Executive Summary

Phase 7 completes the scaling arc projected in Phase 6: from the 30-document / 83-question dress rehearsal to the **full FinanceBench corpus — 84 filings spanning 150 questions** across ~30 issuers and 4 filing types (10-K, 10-Q, 8-K, Earnings Releases).

The evaluation was performed against the **GLM 5.2** deep agent operating over an embedded **Ladybug Document Graph**, evaluated by **DeepSeek V4 Pro (0813)** as the LLM-as-judge under strict equivalence guidelines.

**The dominant finding is that observed accuracy is governed by infrastructure failures, not reasoning quality.** Of the 17 incorrect answers, **12 (70.6%) are runtime/infrastructure crashes** that aborted the agent before it produced any answer — and a 150th question was silently left ungraded by a judge serialization bug. Stripping those, the agent's *clean* reasoning accuracy is **92.0% exact / 96.4% lenient / 93.8% numeric match**.

### Headline Metrics

| Metric | Phase 2 (1D/7Q) | Phase 3 (3D/9Q) | Phase 4 (3D/9Q) | Phase 5 (3D/9Q) | Phase 6 (30D/83Q) | **Phase 7 (84D/150Q)** |
|---|---|---|---|---|---|---|
| **Documents in Graph** | 1 | 3 | 3 | 3 | 30 | **84** |
| **Questions Evaluated** | 7 | 9 | 9 | 9 | 83 | **150** |
| **Exact Correct** | 5 (71.4%) | 7 (77.8%) | 6 (66.7%) | 6 (66.7%) | 70 (84.3%) | **126 (84.0%)** |
| **Correct or Partial** | 6 (85.7%) | 8 (88.9%) | 8 (88.9%) | 7 (77.8%) | 76 (91.6%) | **132 (88.0%)** |
| **Incorrect** | 1 (14.3%) | 1 (11.1%) | 1 (11.1%) | 2 (22.2%) | 7 (8.4%) | **17 (11.3%)** |
| **Groundedness Rate** | 100.0% | 88.9% | 88.9% | 88.9% | 91.6% | **88.0%** |
| **Numeric Match Rate** | 75.0% | 75.0% | 83.3% | 71.4% | 77.8% (35/45) | **86.7% (91/105)** |
| **Avg Tool Calls / Q** | 6.86 | 5.56 | 5.33 | 5.11 | 7.49 | **5.31** |
| **Avg Input Tokens / Q** | 48,150 | 52,700 | 49,679 | 49,961 | 121,849 | **83,417** |
| **Avg Output Tokens / Q** | 1,220 | 1,410 | 1,404 | 1,383 | 2,689 | **1,938** |

### Observed vs. Clean (Infrastructure-Excluded) View

| View | n | Exact | Lenient | Numeric Match | Groundedness |
|---|---|---|---|---|---|
| **Observed (all 150)** | 150 | 84.0% | 88.0% | 86.7% (91/105) | 88.0% |
| **Clean (exclude 12 runtime crashes + 1 ungraded)** | 137 | 92.0% | 96.4% | 93.8% (91/97) | 96.4% |

The gap between 84.0% and 92.0% exact is almost entirely the two infrastructure bugs detailed in §6. Per-question efficiency also improved materially versus Phase 6: avg tool calls fell 29% (7.49 → 5.31) and avg input tokens fell 31% (121,849 → 83,417) despite an 1.8× larger question set, reflecting the DeduplicateToolCallsMiddleware, bounded concurrency, and TOC/section caching maturing under load.

---

## Benchmark Corpus & Dataset Composition

The 84 documents form a balanced cross-section of SEC filing types:

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

### Document Inventory

1. **Annual Reports (10-K)** (64 docs, 112 questions): multi-year coverage of 3M, Adobe, AMD, Amazon, Amcor, AmEx, American Water Works, Best Buy, Block, Boeing, Coca-Cola, Corning, Costco, CVS Health, General Mills, J&J, JPMorgan, KraftHeinz, Lockheed Martin, MGM Resorts, Microsoft, Netflix, Nike, PayPal, PepsiCo, Pfizer, Ulta Beauty, Verizon, Walmart, Activision Blizzard, AES.
2. **Quarterly Reports (10-Q)** (8 docs, 15 questions): `3M_2023Q2`, `BESTBUY_2024Q2`, `Pfizer_2023Q2`, `JPMORGAN_2021Q1`, `JPMORGAN_2022Q2`, `JPMORGAN_2023Q2`, `AMCOR_2023Q2`, `MGMRESORTS_2023Q2`.
3. **Current Reports (8-K)** (6 docs, 9 questions): J&J, PepsiCo (×2), Amcor, Foot Locker (×2).
4. **Earnings Releases** (6 docs, 14 questions): Ulta Beauty, MGM Resorts, Amcor, J&J (×2), PepsiCo.

---

## Detailed Results Breakdown

### Performance by Document Type

| Document Type | Questions | Exact Correct | Partial | Incorrect | Accuracy (Lenient) | Avg Tool Calls | Avg Input Tokens | Avg Output Tokens |
|---|---|---|---|---|---|---|---|---|
| **10-K (Annual)** | 112 | 98 (87.5%) | 4 (3.6%) | 9 (8.0%) | **91.1%** | 4.84 | 75,003 | 1,799 |
| **10-Q (Quarterly)** | 15 | 8 (53.3%) | 2 (13.3%) | 5 (33.3%) | **66.7%** | 8.27 | 172,796 | 2,137 |
| **8-K (Current)** | 9 | 9 (100.0%) | 0 (0.0%) | 0 (0.0%) | **100.0%** | 4.78 | 52,357 | 1,205 |
| **Earnings Release** | 14 | 11 (78.6%) | 0 (0.0%) | 3 (21.4%) | **78.6%** | 6.21 | 74,928 | 3,304 |

### Key Observations by Document Type

1. **8-K Perfection Holds (100%)**:
   - 8-K filings again achieved 100% accuracy at the lowest avg tool-call count (4.78) and lowest input-token load (52,357). The Exhibit 99.1 routing and condensed-structure rules remain the most reliable part of the pipeline.
2. **10-K High Reliability but Failure-Mode Shift (91.1%)**:
   - 10-Ks account for 112 of 150 questions and 9 of 17 incorrects — but **8 of those 9 incorrects are infrastructure crashes** (6 pub/sub collisions + 2 `_aintercept` crashes), leaving only **1 genuine reasoning miss** on 10-K (PepsiCo restructuring face-vs-note). The 10-K reasoning engine is effectively at ~99% clean accuracy.
3. **10-Q Collapse is Infrastructure-Driven (66.7%, down from 86.7% in Phase 6)**:
   - 10-Qs carry the highest tool-call (8.27) and input-token (172,796) load due to dense segment-reporting tables, and absorbed 4 of the 12 infrastructure failures (3 pub/sub + 1 `_aintercept`). Only **1 of 5** 10-Q incorrects is a genuine reasoning failure.
4. **Earnings Releases: All Failures Are Genuine Reasoning (78.6%)**:
   - The 3 Earnings incorrects (Ulta disambiguation, J&J guidance, MGM coverage ratio) carry **no infrastructure error** — these are the truest reasoning gaps in the run.

---

## Comprehensive Failure Mode Analysis

Of 150 questions, **23 were non-perfect (17 incorrect + 6 partial)** and **1 was silently ungraded**. Every non-perfect run was examined and categorized. The failures split into three super-categories: **Infrastructure/Runtime (12)**, **Genuine Reasoning/Gold-Ambiguity (11)**, and **Observability (1)**.

```
Non-perfect outcomes (24 of 150):
├── Infrastructure / Runtime crashes .... 12  (all "incorrect", no answer produced)
│   ├── A. Pub/sub subscriber collision ....... 9   (genai-tk-atof, pre-execution)
│   └── B. Large-tool-result interception ..... 3   (_aintercept, all on 3M filings)
├── Genuine reasoning / gold ambiguity ...... 11  (5 incorrect + 6 partial)
│   ├── C. Benchmark gold temporal/labeling ... 2   (Pfizer Upjohn, Ulta disambiguation)
│   ├── D. Metric / formula convention ........ 3   (MGM EBIT, JPM TBVPS, PayPal WC scope)
│   ├── E. Face vs. note granularity .......... 1   (PepsiCo restructuring)
│   ├── F. Sign / direction convention ........ 1   (Boeing ETR sign)
│   ├── G. Qualitative conclusion divergence .. 1   (CVS capital-intensive)
│   ├── H. Guidance base discrepancy .......... 1   (J&J EPS accelerate vs decelerate)
│   ├── I. Forward-looking nuance ............. 1   (Boeing 777X)
│   └── J. Articulation gap ................... 1   (Amcor 87%)
└── Observability / judge bug ................ 1   (malformed correctness label)
```

### 1. Infrastructure / Runtime Crashes (12 questions — 70.6% of all incorrect)

These are the single largest drag on the headline score. All 12 produced **no substantive answer**, were scored `ungrounded`, and count as numeric non-matches where applicable. They decompose into two distinct bugs.

#### 1A. Pub/Sub Subscriber Collision — `already exists: genai-tk-atof subscriber already exists` (9 questions)

- **Affected**: `id_00005` (Corning WC), `id_00070` (AWW WC), `id_00216` (Verizon quick ratio), `id_00222` (AMD quick ratio), `id_00283` (Pfizer Upjohn payment), `id_00288` (Best Buy cash decline), `id_00302` (Pfizer PPNE), `id_00394` (JPM segment NI), `id_00540` (AES inventory turnover).
- **Signature**: `n_tool_calls = 0`, `input_tokens = 0`, `output_tokens = 0`. The task crashed **before the agent loop started** — a pub/sub subscriber was registered twice with the same `genai-tk-atof` subscriber ID under concurrent dispatch, raising `already exists` and aborting the run.
- **Root cause**: A non-unique subscriber identifier in the `genai-tk` async task-output-forwarding (atof) bus. Under the 150-question bounded-concurrency dispatch, two tasks raced to register the same subscriber name. This is exactly the concurrency hazard Phase 6 flagged for 150-file scaling, now realized.
- **Why it is not a reasoning failure**: The 9 questions are standard ratio/metric computations (working capital, quick ratio, inventory turnover, PPNE growth, segment net income, cash decline, separation payment) — categories the agent answers correctly elsewhere (e.g., AMD/Corning/AWW quick-ratio and WC peers that *did* run scored correctly). The content profile is incidental; the failure is timing.
- **Fix**: Generate a per-task unique subscriber ID (e.g., append the `financebench_id` or a UUID to the `genai-tk-atof` subscriber name) so concurrent registrations cannot collide. Add a startup self-check that asserts subscriber uniqueness across the worker pool.

#### 1B. Large-Tool-Result Interception Crash — `Unreachable code reached in _aintercept_large_tool_result: for tool_result of type <class 'str'>` (3 questions)

- **Affected**: `id_01858` (3M_2023Q2_10Q, dividends), `id_03029` (3M_2018_10K, capex), `id_04672` (3M_2018_10K, net PPNE).
- **Signature**: Unlike 1A, the agent **did execute** — 6 to 13 tool calls, 64k–190k input tokens — then the tool-result interception middleware hit an `assert`/`else`-branch labeled "unreachable" for a `str`-typed tool result and raised, aborting before a final answer was emitted. The "agent answer" left behind is either empty (`04672`) or a transcript of search steps with no conclusion (`01858`, `03029`).
- **Root cause**: A control-flow assumption in `_aintercept_large_tool_result` that a tool result would be a structured/non-`str` type; a large raw-string section payload (likely a big 3M financial table) violated the assumption. **All three failures are on 3M filings**, suggesting 3M's converted markdown yields oversized string sections that exercise this path.
- **Fix**: Handle the `str` branch explicitly in `_aintercept_large_tool_result` (truncate/stream-chunk large string results instead of asserting), and add a regression test with a >100k-character string tool result. This also ties into the Phase 6 `markitdown` fallback concern — ensure 3M PDFs ingest with proper heading segmentation rather than monolithic string sections.

#### 1C. Observability — Judge Serialization Bug (1 question)

- **Affected**: `id_01279` (AMD_2022_10K). The row's `correctness` field is the literal string `"correctness"` (not `correct`/`partial`/`incorrect`), `rationale` is empty, `groundedness` is `"partial"`, `numeric_match` is `None`, and 6 tool calls were executed. The judge returned a malformed/garbage verdict label that the parser did not normalize.
- **Impact**: This is the missing 150th question — `126 correct + 6 partial + 17 incorrect = 149`, not 150. One question was effectively **ungraded**, silently excluded from every aggregate. The summary metrics and the per-document "Results by Document" table therefore under-count by one (this also surfaces as internal row inconsistencies, e.g. `AMD_2022_10K` showing 7 questions but 5+0+1 = 6 accounted).
- **Fix**: Validate judge output against the allowed enum and, on parse failure, retry the judge call once with a stricter output schema (or fall back to a deterministic secondary judge) rather than recording a sentinel label. Add a post-grade integrity check: `assert sum(correctness counts) == n`.

### 2. Genuine Reasoning & Gold-Ambiguity Failures (11 questions — 5 incorrect + 6 partial)

These are the real signal. Several are **recurring carry-overs from Phase 6**, confirming they are structural benchmark/skill traps rather than one-offs.

#### 2A. Benchmark Gold Temporal/Labeling Issues (2 incorrect — recurring)

- **`Pfizer_2023Q2_10Q` — `id_02419`** ("Is Pfizer spinning off any large business segments as of Q2 2023?"):
  - *Agent*: "No — Upohn/Viatris was completed in Nov 2020; Q2 2023 shows only post-close wind-down." (10 tool calls, 145k tokens, detailed evidence.)
  - *Gold*: "Yes, it's spinning off Upjohn."
  - *Verdict*: Identical to the Phase 6 failure. The gold label assumes the Note disclosure implies an ongoing spin-off; the agent's reading is factually better-supported. **Recurring.**
- **`ULTABEAUTY_2023Q4_EARNINGS` — `id_00601`** ("What drove the reduction in SG&A as a % of net sales in FY2023?"):
  - *Agent*: Analyzed **Best Buy**'s FY2023 10-K because the question omits the company name and Best Buy shares the same Jan-2023 fiscal year-end; even contradicted the premise (SG&A % rose, dollars fell).
  - *Gold*: Ulta Beauty ("lower marketing expenses and incentive-compensation leverage from higher sales").
  - *Verdict*: Identical to Phase 6. Anonymous-question company disambiguation remains unsolved. **Recurring.**

#### 2B. Metric / Formula Convention Traps (3 — 1 incorrect + 2 partial)

- **`MGMRESORTS_2022Q4_EARNINGS` — `id_01911`** (incorrect, interest coverage):
  - *Agent*: 5.88× using MGM's reported **Adjusted EBITDAR** as the "Adjusted EBIT" numerator; noted a strict Adjusted EBIT (negative) → 0× alternative only as a secondary interpretation.
  - *Gold*: 0×, because FY2022 Adjusted EBIT is negative.
  - *Fix*: Skill should require the *strict* Adjusted EBIT (Operating Income − D&A − triple-net rent, etc.) as the primary numerator for "Adjusted EBIT" coverage, with EBITDAR only as a named alternative.
- **`JPMORGAN_2021Q1_10Q` — `id_02119`** (partial, liquidation value per share):
  - *Agent*: Tangible BVPS **$64.27** and Common BVPS **$82.31** — neither matches gold.
  - *Gold*: **$66.56** per share.
  - *Verdict*: A genuine numeric discrepancy in the tangible computation (goodwill/MSR/intangible split or share-count basis), not just the Phase 6 convention gap. **Recurring but now deeper** — the agent identifies the right metric but the arithmetic/inputs diverge by ~$2.3/share.
- **`PAYPAL_2022_10K` — `id_00080`** (partial, working capital):
  - *Agent*: $12,416M face-value (total current assets − total current liabilities), with a strong narrative that WC is distorted by ~$36–40B customer pass-through funds; adjusted figure $16,166M.
  - *Gold*: $1.6Bn (operating working capital, excluding pass-through funds).
  - *Verdict*: Right direction, wrong scope. The agent computed *headline* WC; gold used *operating* WC. **Recurring** class: working-capital-scope ambiguity for payments/fiduciary businesses.

#### 2C. Face vs. Note Granularity (1 incorrect — recurring)

- **`PEPSICO_2022_10K` — `id_01328`** ("restructuring costs directly outlined in Pepsico's income statements for FY2022; if not explicitly outlined then state 0"):
  - *Agent*: **$0** — no separate "Restructuring costs" line on the face of the Consolidated Statement of Income (embedded in SG&A); explicitly acknowledged Note 3 discloses productivity/restructuring charges but followed the literal "directly outlined" instruction.
  - *Gold*: **$411 million** (Note 3).
  - *Verdict*: Identical trap to Phase 6. **Recurring.** Fix: dual-response rule — state "$0 on the face; $411M in Note 3."

#### 2D. Sign / Direction Convention (1 partial)

- **`BOEING_2022_10K` — `id_00585`** (effective tax rate FY2022 vs FY2021):
  - *Agent*: 14.7% (FY2021) and (0.6)% (FY2022) — treating the tax **benefit** as a positive rate and the small expense as a negative rate.
  - *Gold*: −14.76% (FY2021) and 0.62% (FY2022) — benefit as negative, expense as positive.
  - *Verdict*: Same underlying figures, opposite sign convention for benefit-vs-expense rate presentation. Fix: standardize ETR sign convention (tax expense → positive, benefit → negative) in the financial-ratios skill.

#### 2E. Qualitative Conclusion Divergence (1 partial)

- **`CVSHEALTH_2022_10K` — `id_00790`** ("Is CVS Health capital-intensive based on FY2022?"):
  - *Agent*: **No** — PP&E/Revenue 3.99%, CapEx/Revenue 0.85%, PP&E/Total Assets 5.6%; argued the low 1.82% ROA is an artifact of Aetna goodwill/intangibles (45% of assets) and 2022 opioid-litigation charges, not physical capital.
  - *Gold*: **Yes** — using the same ROA 1.82% and PP&E/Total Assets 5.6% figures, with the goodwill caveat noted.
  - *Verdict*: Identical inputs, opposite qualitative verdict. The agent's analysis is arguably more nuanced, but it contradicts the gold conclusion. Fix: when a skill rule (ROA < 5% ⇒ capital-intensive) fires, the agent should lead with that conclusion and *then* add caveats, rather than overriding the rule with its own judgment.

#### 2F. Guidance Base Discrepancy (1 incorrect — recurring)

- **`JOHNSON_JOHNSON_2022Q4_EARNINGS` — `id_00651`** ("Is J&J adjusted EPS growth expected to accelerate in FY2023?"):
  - *Agent*: **Yes** — midpoint guidance $10.55 ⇒ +4.0% vs FY2022 +3.6% (≈40 bps acceleration).
  - *Gold*: **No** — deceleration to 3.5% (vs 3.6% in FY2022).
  - *Verdict*: Same recurring Phase 6 issue — nominal-guidance-midpoint vs constant-currency operational guidance base. **Recurring.** Fix: for "accelerate/decelerate" guidance questions, compute both reported and constant-currency operational growth and pick the basis the issuer emphasizes.

#### 2G. Forward-Looking Narrative Nuance (1 partial — recurring)

- **`BOEING_2022_10K` — `id_00494`** (FY2023 production rate forecasts):
  - *Agent*: Correctly captured 737 and 787 increases, but stated 777X production **paused through 2023**.
  - *Gold*: Increases for 737, **777X**, and 787 (i.e., 777X resumption timeline).
  - *Verdict*: Identical to Phase 6. **Recurring.**

#### 2H. Articulation Gap (1 partial)

- **`AMCOR_2023Q2_10Q` — `id_01936`** (nature/purpose of restructuring liability):
  - *Agent*: Comprehensive rollforward giving Employee Costs $81M / Total $93M, from which 87% is inferable, but never stated "87% employee liabilities" explicitly.
  - *Gold*: "87% of the total restructuring liability is related to Employee liabilities."
  - *Verdict*: Substantively correct; the judge required the explicit percentage. Fix: when a question asks for a proportion/nature, the agent should compute and state the explicit ratio, not just the components.

### Recurrence Summary (Phase 6 → Phase 7)

| Failure class | Phase 6 | Phase 7 | Status |
|---|---|---|---|
| Pfizer Upjohn temporal gold label | 1 | 1 | **Unresolved (recurring)** |
| Anonymous-question company disambiguation | 1 | 1 | **Unresolved (recurring)** |
| Face-vs-note (PepsiCo restructuring) | 1 | 1 | **Unresolved (recurring)** |
| Guidance base (J&J accelerate/decelerate) | 1 | 1 | **Unresolved (recurring)** |
| Boeing 777X forward-looking | 1 | 1 | **Unresolved (recurring)** |
| Quick-ratio dual definition | 2 | 0 | **Resolved** |
| Inventory-turnover denominator | 1 | 0 (infra-killed) | **Indeterminate** (AES Q crashed before answering) |
| PPNE acronym | 1 | 0 (infra-killed) | **Indeterminate** (Pfizer Q crashed before answering) |
| Numeric match rate (overall) | 77.8% | 86.7% (93.8% clean) | **Improved** |

The four Phase 6 skill fixes that *did* land (quick-ratio dual definition, dual inventory-turnover, PPNE aliasing, liquidation dual BVPS) are masked here because two of their probe questions (AES inventory turnover, Pfizer PPNE) were killed by the pub/sub collision before the agent could answer — an unfortunate confound. The numeric-match jump to 93.8% (clean) is the strongest evidence that the dual-formula skill work paid off.

---

## Technical & Infrastructure Deep-Dive

### 1. The `genai-tk-atof` Pub/Sub Collision (Critical, 9-question blast radius)

- **Mechanism**: The async task-output-forwarding (atof) bus registers a named subscriber per question task. The subscriber name is not namespaced by task/question ID, so under bounded concurrency (max_workers ≥ 2) two tasks can attempt to register `genai-tk-atof` simultaneously; the second registration raises `already exists` and the task returns an error dict with zero tool calls / zero tokens.
- **Blast radius**: 9 questions, all scored incorrect/ungrounded, 6 of them numeric non-matches. This single bug accounts for **5.3 percentage points of the headline accuracy gap** (126 → 135 if fixed = 90.0%).
- **Fix priority**: P0. Per-task unique subscriber ID + a worker-pool startup uniqueness assertion. Low-risk, high-yield.

### 2. The `_aintercept_large_tool_result` String-Branch Crash (3 questions, 3M-only)

- **Mechanism**: The tool-result interception middleware asserts a non-`str` payload type; a large raw-string section (big 3M financial table) hits the "unreachable" `else` and raises, aborting the agent mid-run after substantial work (up to 13 tool calls / 190k tokens).
- **Blast radius**: 3 questions, all on 3M filings (2× `3M_2018_10K`, 1× `3M_2023Q2_10Q`). Strongly correlated with 3M document ingestion producing oversized unstructured string sections — the same family of risk as the Phase 6 `markitdown` monolithic-section incident.
- **Fix priority**: P1. Explicit `str` branch with truncation/streaming; ingest-time heading heuristics for 3M PDFs; regression test with a >100k-char string tool result.

### 3. Judge Serialization Robustness (1 question silently ungraded)

- **Mechanism**: `id_01279` recorded `correctness: "correctness"` and an empty rationale — the judge emitted a malformed label the parser passed through verbatim instead of normalizing/retrying. This left one question outside the correct/partial/incorrect tally (126+6+17 = 149 ≠ 150) and corrupted the per-document "Results by Document" row arithmetic.
- **Fix priority**: P2. Enum-validate judge output, retry-once on parse failure, post-grade `sum(counts) == n` integrity assertion.

### 4. What Held Up Well

- **DeduplicateToolCallsMiddleware + caching**: avg tool calls 7.49 → 5.31 (−29%) and input tokens 121,849 → 83,417 (−31%) at 1.8× the question volume. Navigation efficiency scaled.
- **Bounded concurrency**: contained the OpenRouter burst traffic that caused streaming drops in Phase 6; no `Upstream error: stream failed` events observed in this run.
- **Prefect task isolation**: the try/except wrappers added in Phase 6 worked — the 12 infra crashes were captured as structured error dicts and did **not** abort sibling tasks or the parent flow (the run completed to a full summary).

---

## Key System Insights & Recommendations

### 1. Fix Infrastructure Before Tuning the Model
The highest-leverage action is not a reasoning improvement: fixing the `genai-tk-atof` subscriber collision alone lifts exact accuracy from 84.0% to ~90.0%, and fixing the `_aintercept` string branch and judge serializer brings the clean reasoning floor to ~92.0% exact / 96.4% lenient. **The model is not the bottleneck; the harness is.**

### 2. Close the Five Recurring Gold-Ambiguity Loops
Five failures recurred identically from Phase 6 (Pfizer Upjohn, Ulta disambiguation, PepsiCo face-vs-note, J&J guidance base, Boeing 777X). These are structural and will persist until addressed:
- **Anonymous questions**: scan all candidate documents sharing the question's period before committing to a company.
- **Face vs. note**: state both the face-of-statement value and the Note disclosure value when a line item is subsumed.
- **Guidance "accelerate/decelerate"**: compute both reported and constant-currency operational bases; default to the issuer's emphasized basis.
- **Temporal gold labels**: flag benchmark questions whose premise assumes a historical event is ongoing (Pfizer Upjohn) for relabeling or agent-side hedging.
- **Forward-looking resumption timelines**: extract explicit "resume/return to" phrases rather than inferring pause-continuation.

### 3. Standardize Financial-Statement Sign Conventions
Add to the financial-ratios skill: **effective tax rate** sign convention (expense = positive, benefit = negative), and require the strict Adjusted EBIT (not EBITDAR) as the primary coverage numerator when a question names "Adjusted EBIT." Require explicit proportion statements (e.g., "87% employee") when a question asks for nature/composition, not just the component table.

### 4. Don't Override Skill Rules with Narrative Judgment
The CVS capital-intensive case shows the agent computing the correct skill inputs (ROA 1.82% < 5% trigger) then *overriding* the rule with its own goodwill/one-time-charge narrative. Skill rules should fire as the primary conclusion, with counter-narrative reserved as a caveat, so the agent's verdict tracks the benchmark's rule-based definitions.

### 5. Observability: Assert Aggregate Integrity
Add a post-grade integrity check (`sum(correctness counts) == n`) and enum-validate judge labels so a silently ungraded question can never again corrupt every downstream aggregate and per-document table.

---

## Conclusion

Scaling FinanceBench to the **full 84-document / 150-question corpus** demonstrates that the **genai-tk + genai-graph + Ladybug** architecture scales correctly in the large: 8-K perfection held, 10-K reasoning is at ~99% clean accuracy, numeric match improved to 93.8% (clean), and per-question efficiency improved 25–30% over Phase 6.

The observed 84.0% exact / 88.0% lenient headline, however, is **dominated by two infrastructure bugs** — a `genai-tk-atof` pub/sub subscriber collision (9 questions) and a `_aintercept_large_tool_result` string-branch crash (3 questions, all 3M) — plus one judge serialization bug that silently dropped a 150th question. Together these 13 non-reasoning failures mask a clean reasoning floor of **92.0% exact / 96.4% lenient / 93.8% numeric match / 96.4% groundedness**.

The remaining 11 genuine failures are dominated by **five recurring Phase 6 gold-ambiguity/convention traps** (Pfizer Upjohn, Ulta disambiguation, PepsiCo face-vs-note, J&J guidance base, Boeing 777X) that remain unresolved and are now the clear priority once the harness bugs are closed. Priority order: **(P0) subscriber-ID uniqueness → (P1) `_aintercept` string branch + 3M ingestion → (P2) judge enum validation + integrity assert → (P3) close the five recurring reasoning loops.**
