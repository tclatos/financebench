---
name: financebench-qa
description: Answer FinanceBench financial questions about an SEC filing (10-K/10-Q) by navigating the Document Graph — get_folder_toc, get_document_toc, get_section_content, search_sections. Use when the task is to answer a grounded financial question from an ingested filing.
---

# FinanceBench Financial Question Answering

You answer questions about a company's SEC filing (10-K, 10-Q, or 8-K) by
navigating a Document Graph: a Ladybug graph of Folders → Documents → Markdown
sections. You do NOT have the document memorised — you must read it via tools.
For ratio/margin formula and convention definitions (e.g. what the quick ratio
includes), consult the `financial-ratios` skill rather than guessing.

## Workflow

1. `get_folder_toc(folder_id=None)` — list every ingested document with its id
   and one-line description. Pick the document that matches the question's
   company / period (e.g. `AMD_2022_10K_pdf.md`).
2. `get_document_toc(document_id=<id>, max_level=2)` — get that document's
   section tree. Use `max_level=2` first on a long 10-K; the financial
   statements live under "Part II, Item 8. Financial Statements".
3. `search_sections(query="<natural-language term>")` — when you do not know which
   section holds the answer, run a hybrid search (vector similarity fused with
   BM25 keyword) across the corpus. Results are ranked best-first with a
   relevance score and a matched-chunk snippet, so the top hits are the best
   candidates for `get_section_content`. This is the fastest way to land on a
   specific line item.
4. `get_section_content(section_ids="<id1>,<id2>")` — read the raw Markdown of
   ONLY the sections whose title/description matches the question. Financial
   statements are Markdown tables — read the whole section to get every column.
5. Iterate: search again with different keywords or read adjacent sections
   until your answer is grounded, then answer.

## Where financial-statement answers live (target these)

FinanceBench questions mostly resolve to one of the five consolidated
statements or the MD&A. Target the right statement by name:

- **Cash flow statement** ("capital expenditure", "cash from operations",
  "investing/financing activities", "depreciation") →
  `search_sections(query="Consolidated Statements of Cash Flows")`.
- **Balance sheet** ("net PP&E", "inventory", "current assets/liabilities",
  "goodwill", "total debt", "quick ratio", "working capital") →
  `search_sections(query="Consolidated Balance Sheets")`.
- **Income statement** ("revenue", "net income", "gross margin", "operating
  income/margin", "EPS", "SG&A") →
  `search_sections(query="Consolidated Statements of Operations")`.
- **Stockholders' equity** ("dividends", "share repurchases", "equity") →
  `search_sections(query="Stockholders")`.
- **Segment / MD&A** ("which segment grew", "what drove revenue/margin change",
  "customer concentration") → `search_sections(query="Segment")` or
  `search_sections(query="Management")` and read MD&A sections.
- **Products / business description** ("what products does X sell") →
  `get_document_toc`, then read "Item 1. Business".

## Answering rules

- **Read the table before you compute.** Ratios (quick ratio, turnover, capex %
  of revenue, 3-year averages) need two or more numbers — often from different
  statements. Read each source section fully, extract the exact line-item names
  and values, THEN compute.
- **Units & rounding:** answer in the units the question asks for (USD millions,
  billions, percent) with the requested rounding (e.g. "two decimal places",
  "one decimal place"). If the question says "primarily using the balance
  sheet", anchor on the balance sheet.
- **Signs & periods:** cash-flow line items are often shown as negatives in
  parentheses, e.g. `(1,577)`. Report capex as a positive amount unless the
  question asks for the signed cash-flow value. Match the exact fiscal period
  the question names (FY22 vs FY21 vs a quarter).
- **Cite every fact** with its section id `[hash::sequence]` and the source
  document filename, e.g. `(AMD_2022_10K_pdf.md [f391da52bf0af1c2::13])`.
- **Never invent.** If a number or fact is not in the sections you read, say so
  explicitly. Do not infer from general knowledge about the company.
- **Map before you re-search.** Do not call `search_sections` more than three
  times in a row. If two searches have not landed on the answer, call
  `get_document_toc(document_id=<id>, max_level=2)` to see the section map of the
  most relevant document, then read the specific section with `get_section_content`.
  One grounded read of the right section beats another blind search.
- Return your answer as a short, direct response: the answer first, then the
  key supporting numbers and a citation. Do not paste whole sections.
