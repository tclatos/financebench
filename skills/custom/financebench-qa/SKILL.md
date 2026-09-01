---
name: financebench-qa
description: Answer FinanceBench financial questions across SEC filings (10-K, 10-Q, 8-K), Earnings Releases, Annual Reports, and foreign filings (20-F, 6-K) by navigating the Document Graph — get_folder_toc, get_document_toc, get_section_content, search_sections. Use when the task is to answer a grounded financial question from an ingested filing.
---

# FinanceBench Financial Question Answering

You answer questions about companies' financial filings (**10-K, 10-Q, 8-K, Earnings Releases, Annual Reports, 20-F/6-K**) by navigating a Document Graph: Folders → Documents → Markdown sections. You do NOT have the documents memorised — you must read them via tools.
For ratio/margin formulas, calculation conventions, and sign handling (e.g. what the quick ratio includes, CapEx sign conventions), consult the `financial-ratios` skill.

---

## 1. Filing Traps & Non-Obvious Routing Rules

Use `get_document_toc` to inspect the outline, but keep these critical structural rules and failure traps in mind:

- **8-K Filings — Always Check Exhibits (Exhibit 99.1)**:
  - The main text of an 8-K is often a brief 1–2 page administrative summary that references exhibits.
  - **The actual press release, transaction metrics, pro forma tables, and financial data live in `Exhibit 99.1`** (or other exhibits). When answering 8-K questions, navigate to or search for `Exhibit 99.1`.
- **10-Q Interim Statements — Quarter vs. YTD Column Trap**:
  - Statements in 10-Qs place **"Three Months Ended"** (the quarter) and **"Six / Nine Months Ended"** (Year-to-Date cumulative) side-by-side. Always verify the column header against what the question specifies.
- **Notes to Financial Statements — Granular Line Items**:
  - The face of the Balance Sheet or Income Statement only shows top-level aggregate totals.
  - Granular details (**segment revenues/operating income, geographic breakdowns, restructuring charges, debt maturity schedules, tax rates, lease liabilities, discontinued operations**) live in the **Notes to Consolidated Financial Statements**.
- **Earnings Releases & Non-GAAP Items**:
  - For press releases and earnings announcements, distinguish GAAP figures from Non-GAAP metrics (Adjusted EBITDA, Free Cash Flow, Constant Currency revenue). Check the Non-GAAP reconciliation tables at the end of the release.
- **Foreign Filings (Form 20-F, Form 6-K, IFRS)**:
  - *Statement of Financial Position* = Balance Sheet; *Statement of Profit or Loss* = Income Statement; *Operating and Financial Review* = MD&A.

---

## 2. Navigation Workflow

1. **Orient with `get_folder_toc(folder_id=None)`**:
   - List every ingested document with its ID, filename, and one-line description.
   - Pick the document matching the target company, fiscal period, and filing type.
2. **Get the Map with `get_document_toc(document_id=<id>, max_level=2)`**:
   - Inspect the document outline first. Drill into the specific section/statement where the data resides.
3. **Targeted Search with `search_sections(query="<query>")`**:
   - Run a hybrid search (vector + BM25) across the corpus when the exact section cannot be located via the TOC.
   - Use high-signal terms (e.g. `query="Consolidated Balance Sheets"`, `query="Segment Information Note"`, `query="Exhibit 99.1"`).
4. **Read Raw Markdown with `get_section_content(section_ids="<id1>,<id2>")`**:
   - Read the complete section markdown for selected sections to view all table rows, column headers, units, and footnote markers.
5. **Map Before You Re-Search**:
   - Do not chain blind searches. If two searches fail to land on the answer, call `get_document_toc` on the document to view the section tree and read the relevant section directly.
6. **Do NOT Re-Fetch Document TOC**:
   - Once you call `get_document_toc` for a document, its full section tree and all section IDs remain available in your conversation history above. Do NOT call `get_document_toc` multiple times for the same document — refer to the earlier output to select your next sections.

---

## 3. Grounded Answering & Disambiguation Rules

- **Verify Column Headers & Periods**:
  - Always verify table column dates (e.g. *June 30, 2023* vs *June 30, 2022* or *FY22* vs *FY21*).
- **Handling Question Ambiguities**:
  - *Best Performing / Top Line Performance*: If a question asks which category/segment "performed best" without specifying metric, report **both** highest percentage growth (% YoY) and highest absolute revenue ($) with supporting figures.
  - *Corporate Actions & Spin-offs*: Clearly distinguish between completed spin-offs (discontinued operations), announced transactions, and historical events.
  - *Non-GAAP vs. GAAP*: If a metric is non-GAAP, state the GAAP figure first and provide the Non-GAAP reconciliation/figure with clear labels.
- **Units, Signs & Rounding**:
  - Report exact units (millions, billions, %) and requested decimal precision.
  - CapEx is reported as negative in cash flow statements; use positive absolute value for standalone CapEx or FCF calculations ($FCF = OCF - CapEx$).
  - Negative tax provisions or pre-tax losses yield **negative effective tax rates** (preserve the sign).
- **Citation**:
  - Always cite section ID `[hash::sequence]` and source filename, e.g. `(BESTBUY_2024Q2_10Q_pdf.md [568acd8b84733490::12])`.
- **Direct Synthesized Answers**:
  - Answer directly first, followed by supporting calculations, verbatim extracted figures, and citations. Never paste entire unstructured sections.
