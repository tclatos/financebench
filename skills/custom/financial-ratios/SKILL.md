---
name: financial-ratios
description: Reference for financial ratio, margin, and metric definitions, formulas, components, and conventions (quick ratio, ROE, EBITDA, free cash flow, DSO, etc.) when computing or interpreting figures from financial statements. Use when a question involves a named ratio/margin/metric, units or sign conventions, or where-to-find guidance for a line item.
---

# Financial Ratios & Metrics Reference

Canonical definitions, formulas, line-item locations, and critical conventions for computing and interpreting financial statement metrics.

## General Calculation Rules

- **Parent Company Attributable**: Use Net Income attributable to common/parent shareholders (exclude non-controlling interests) unless total is requested.
- **Signs & Units**: 
  - CapEx is reported as negative on Cash Flow Statement; use **absolute value** for formulas (FCF = Operating Cash Flow − CapEx).
  - Effective tax rate **preserves sign** (negative tax provision or loss = negative rate, e.g. `-14.76%`).
  - Keep reported unit scale (millions vs billions) consistent across all formula terms.
- **Averages vs Single Periods**:
  - Use balance sheet period-end for single-period ratios (ROA, Quick Ratio, Working Capital) unless comparative/average is explicitly requested.
  - Inventory turnover and asset turnover prefer $(Beginning + Ending) / 2$ when multi-period balance sheets are provided.

---

## 1. Liquidity

### Quick Ratio (Acid-Test)
- **Standard (Acid-Test) Formula**: `(Cash & Cash Equivalents + Marketable Securities + Net Accounts Receivable) / Total Current Liabilities` (or `(Total Current Assets - Inventories - Prepaid Expenses) / Total Current Liabilities`)
- **Alternative Formula**: `(Total Current Assets - Inventories) / Total Current Liabilities` (includes prepaid expenses)
- **Location**: Balance Sheet — Current Assets & Current Liabilities sections.
- **Conventions & Dual-Response Rule**:
  - **Always calculate and state BOTH values**:
    1. Standard Acid-Test (excluding inventory and prepaid expenses)
    2. Alternative Quick Ratio (excluding inventory only, including prepaid expenses)
  - State both clearly (e.g. "Standard Quick Ratio (excluding prepaids) = X.XX; Alternative Quick Ratio (Current Assets - Inventory) = Y.YY").
  - A quick ratio $\ge 1.0$ is healthy; $< 1.0$ indicates inability to cover current liabilities with liquid assets.
  - Use period-end balance sheet values.

### Current Ratio / Working Capital Ratio
- **Formula**: `Total Current Assets / Total Current Liabilities`
- **Location**: Balance Sheet — Total Current Assets and Total Current Liabilities line items.
- **Conventions**:
  - **Includes inventory**, unlike Quick Ratio.
  - Typically acceptable between 1.0 and 2.0.

### Working Capital (Net Working Capital)
- **Formula**: `Total Current Assets - Total Current Liabilities`
- **Location**: Balance Sheet face.
- **Conventions**:
  - By default, use the explicit "Total current assets" minus "Total current liabilities" lines.
  - For fintech/payment processors, customer funds/pass-through balances are included unless "operating working capital" is explicitly specified.
  - Do NOT subtract non-current items.

### Operating Cash Flow Ratio
- **Formula**: `Net Cash Provided by Operating Activities / Total Current Liabilities`
- **Location**: Cash Flow Statement (Operating Activities) & Balance Sheet (Current Liabilities).
- **Conventions**:
  - Measures ability to cover short-term debt from operating cash generation. Ratio $> 1.0$ is strong.

---

## 2. Profitability & Margins

### Gross Profit Margin
- **Formula**: `((Revenue - COGS) / Revenue) * 100` (or `(Gross Profit / Revenue) * 100`)
- **Location**: Income Statement — Revenue / Net Sales and Cost of Goods Sold / Cost of Revenue.
- **Conventions**: COGS excludes SG&A and R&D unless directly tied to production.

### Operating Margin (EBIT Margin)
- **Formula**: `(Operating Income / Net Revenue) * 100`
- **Location**: Income Statement — Operating Income (EBIT) and Total Revenue / Net Sales.
- **Conventions**: Operating Income is before interest expense and income taxes.

### Net Profit Margin
- **Formula**: `(Net Income / Total Revenue) * 100`
- **Location**: Income Statement — Net Income (attributable to parent) and Total Revenue.

### EBITDA
- **Formula**: `Operating Income (EBIT) + Depreciation + Amortization`
- **Alternate**: `Net Income + Interest + Taxes + Depreciation + Amortization`
- **Location**: Income Statement (Operating Income) + Cash Flow Statement (D&A line in Operating Activities).
- **Conventions**:
  - **PP&E D&A Only**: D&A in EBITDA includes only PP&E depreciation and intangible amortization.
  - **Do NOT add back**: Content amortization (streaming/films), right-of-use/lease amortization, or debt issuance cost amortization.
  - Use unadjusted formula unless "Adjusted EBITDA" is specifically requested.

### EBITDA Margin
- **Formula**: `(EBITDA / Total Revenue) * 100`
- **Location**: Derived from Income Statement and Cash Flow Statement.

### Return on Equity (ROE)
- **Formula**: `Net Income / Average Shareholders' Equity` (or `Net Income / Period-End Equity`)
- **Location**: Income Statement (Net income attributable to common shareholders) & Balance Sheet (Total stockholders' equity).
- **Conventions**:
  - Exclude non-controlling interests from Net Income.
  - Prefer average equity `(Beginning + Ending) / 2` if multiple periods available; otherwise period-end.

### Return on Assets (ROA)
- **Formula**: `Net Income / Total Assets (Period-End)`
- **Location**: Income Statement (Net income attributable to company) & Balance Sheet (Total assets).
- **Conventions**:
  - Use end-of-period total assets from the current year balance sheet unless average is explicitly requested.
  - Low ROA ($< 5\%$) is a primary indicator of capital intensity.

### Earnings Per Share (EPS)
- **Formula**:
  - `Basic EPS = (Net Income - Preferred Dividends) / Weighted Average Common Shares`
  - `Diluted EPS = (Net Income - Preferred Dividends) / Weighted Average Diluted Shares`
- **Location**: Income Statement — Bottom section (Earnings Per Share).

### Depreciation & Amortization as % of Revenue
- **Formula**: `((Depreciation + Amortization) / Total Revenue) * 100`
- **Location**: Cash Flow Statement (D&A in Operating Activities) & Income Statement (Total Revenue).
- **Conventions**: Use the primary D&A line from Cash Flow adjustments to net income. Exclude content amortization.

### Effective Tax Rate
- **Formula**: `(Provision for Income Taxes / Pre-Tax Income) * 100`
- **Location**: Income Statement — Provision for Income Taxes / Income Before Taxes.
- **Conventions**:
  - **Preserve Sign**: Tax benefit (negative provision) or pre-tax loss (negative income) results in a **negative** rate (e.g. `-14.76%`). Do not take absolute value.

---

## 3. Solvency & Coverage

### Debt-to-Equity (D/E)
- **Formula**: `Total Liabilities / Total Shareholders' Equity`
- **Alternate (Strict)**: `Total Interest-Bearing Debt / Total Shareholders' Equity`
- **Location**: Balance Sheet — Total Liabilities and Total Stockholders' Equity.

### Interest Coverage Ratio (Times Interest Earned)
- **Formula**: `EBIT / Interest Expense` (or `EBITDA / Interest Expense`)
- **Location**: Income Statement — Operating Income (EBIT) and Interest Expense (gross).
- **Conventions**:
  - **Negative EBIT = 0 Coverage**: If EBIT / Operating Income is negative, coverage ratio is **zero** (cannot cover interest).
  - If given EBITDAR: `EBIT = EBITDAR - D&A - Rent Expense`.

---

## 4. Efficiency & Operations

### Inventory Turnover
- **Formula (Average Inventory)**: `COGS / Average Inventory` where Average Inventory = `(Beginning + Ending) / 2`
- **Formula (Ending Inventory)**: `COGS / Ending Inventory`
- **Location**: Income Statement (COGS / Cost of Sales) & Balance Sheet (Inventory).
- **Conventions & Dual-Response Rule**:
  - Use COGS in numerator, **not revenue**.
  - **Always calculate and state BOTH formulas**:
    1. Average Inventory: `COGS / ((Beginning Inv + Ending Inv) / 2)`
    2. Ending Inventory: `COGS / Ending Inv`
  - Equivalent to "how many times the company has sold its inventory".

### Days Sales Outstanding (DSO)
- **Formula**: `(Accounts Receivable / Total Revenue) * Number of Days` (365 annual, 90 quarterly)
- **Location**: Balance Sheet (Net Accounts Receivable) & Income Statement (Revenue).

### Days Payable Outstanding (DPO)
- **Formula**: `(Accounts Payable / COGS) * Number of Days` (365 annual, 90 quarterly)
- **Location**: Balance Sheet (Accounts Payable) & Income Statement (COGS).

### Asset Turnover
- **Formula**: `Net Revenue / Average Total Assets`
- **Location**: Income Statement (Revenue) & Balance Sheet (Total Assets).

### Capital Intensity
- **Formula**: `Total Assets / Revenue` or `CapEx / Revenue`
- **Location**: Balance Sheet (Total Assets, PP&E), Income Statement (Revenue), Cash Flow (CapEx).
- **Conventions**:
  - High fixed assets (PP&E) / CapEx relative to revenue signals capital intensity.
  - **Always calculate and cite ROA**: Low ROA ($< 5\%$) strongly reinforces capital intensity.

---

## 5. Cash Flow & Shareholder Returns

### Capital Expenditure (CapEx) / PP&E / PPNE
- **Formula**: Purchases of Property, Plant and Equipment (from Cash Flow Statement)
- **Location**: Cash Flow Statement — Investing Activities section; Balance Sheet — Property, Plant and Equipment, Net.
- **Conventions & Acronym Mapping**:
  - **"PPNE" / "PP&E Net"**: Refers to **Property, Plant and Equipment, Net** on the Balance Sheet. (Do NOT confuse with Pension & Postretirement Non-service Expense).
  - Look for "Purchases of property, plant and equipment" or "Capital expenditures".
  - Reported as negative (cash outflow); quote the **absolute positive value** for CapEx.
  - Do not include acquisitions/business combinations.

### Free Cash Flow (FCF)
- **Formula**: `Operating Cash Flow - Capital Expenditures`
- **Location**: Cash Flow Statement — Net cash provided by operating activities minus PP&E purchases.
- **Conventions**: CapEx must be subtracted as a positive number from operating cash flow.

### FCF Conversion
- **Formula**: `Free Cash Flow / Net Income` (or `(Operating Cash Flow - CapEx) / Net Income`)
- **Location**: Cash Flow Statement (Operating Cash Flow, CapEx) & Income Statement (Net Income).
- **Conventions**: FCF must be computed after subtracting CapEx, not Operating Cash Flow alone.

### Dividend Payout Ratio
- **Formula**: `(Total Dividends Paid / Net Income) * 100` (or `(Dividends Per Share / EPS) * 100`)
- **Location**: Cash Flow Statement (Financing / Dividends Paid) or Equity Statement & Income Statement.

---

## 6. Valuation, Derivatives & Special Items

### Price-to-Earnings (P/E)
- **Formula**: `Stock Price / EPS`
- **Location**: Market price & Income Statement (EPS).

### Book Value Per Share (BVPS) & Liquidation Value
- **Common BVPS Formula**: `(Total Common Shareholders' Equity - Preferred Equity) / Common Shares Outstanding`
- **Tangible BVPS Formula**: `(Total Common Equity - Preferred Equity - Goodwill - Intangible Assets) / Common Shares Outstanding`
- **Location**: Balance Sheet (Stockholders' Equity, Common Shares Outstanding on face; Intangibles / Goodwill).
- **Conventions & Dual-Response Rule**:
  - **Liquidation Scenario**: When asked how much shareholders receive if a company liquidates assets at book value, provide **BOTH**:
    1. Common Book Value per Share = `Total Common Equity / Common Shares`
    2. Tangible Book Value per Share = `(Total Common Equity - Goodwill - Intangibles) / Common Shares`
  - Use common shares outstanding from balance sheet face (do **not** use diluted shares).
  - For banks, use "Total stockholders' equity", excluding non-controlling interests.

### Revenue Growth Rate (YoY)
- **Formula**: `((Current Period Revenue - Prior Period Revenue) / Prior Period Revenue) * 100`
- **Location**: Income Statement — Consecutive periods of Total Revenue / Net Sales.

### Notional Value (Derivatives)
- **Description**: Total underlying value of contract positions (swaps, forwards, options).
- **Location**: Notes to Financial Statements — "Derivative Instruments" / "Hedging Activities".
- **Conventions**: Reported directly in notes tables; identify contract with highest aggregate notional amount.

### Restructuring Costs & Primary Statement vs Footnotes
- **Description**: One-time reorganization, severance, or facility closure charges.
- **Location**: Income Statement (face) and Notes to Consolidated Financial Statements (e.g. Note on Restructuring).
- **Conventions & Dual-Response Rule**:
  - If asked for restructuring costs "directly outlined in the income statement" or similar:
    - If restructuring is **not** broken out as a separate line item on the statement face (e.g., subsumed into SG&A or Cost of Goods Sold): state **$0 (or not explicitly outlined as a standalone line item) on the face of the Income Statement**, but **explicitly provide the detailed restructuring figure from the Notes to Financial Statements** (e.g., "$411 million detailed in Note 3").
