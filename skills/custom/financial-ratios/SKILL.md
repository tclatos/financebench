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
- **Formula**: `(Total Current Assets - Inventories - Prepaid Expenses) / Total Current Liabilities`
- **Alternate**: `(Cash & Cash Equivalents + Marketable Securities + Net Accounts Receivable) / Total Current Liabilities`
- **Location**: Balance Sheet — Current Assets & Current Liabilities sections.
- **Conventions**:
  - **Excludes inventory and prepaid expenses** (key distinction from Current Ratio).
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
- **Formula**: `COGS / Average Inventory` (or `COGS / Ending Inventory`)
- **Location**: Income Statement (COGS / Cost of Sales) & Balance Sheet (Inventory).
- **Conventions**:
  - Use COGS in numerator, **not revenue**.
  - Average inventory = `(Beginning + Ending) / 2` (where beginning = prior year balance sheet ending).
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

### Capital Expenditure (CapEx)
- **Formula**: Purchases of Property, Plant and Equipment (from Cash Flow Statement)
- **Location**: Cash Flow Statement — Investing Activities section.
- **Conventions**:
  - Look for "Purchases of property, plant and equipment" or "Capital expenditures".
  - Reported as negative (cash outflow); quote the **absolute positive value**.
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

### Book Value Per Share (BVPS)
- **Formula**: `(Total Shareholders' Equity - Preferred Equity) / Common Shares Outstanding`
- **Location**: Balance Sheet (Stockholders' Equity, Common Shares Outstanding on face).
- **Conventions**:
  - **Liquidation Scenario**: Represents theoretical per-share payout if assets liquidated at book value.
  - Use common shares outstanding from balance sheet face (do **not** use diluted shares).
  - For banks, use "Total stockholders' equity", excluding non-controlling interests.

### Revenue Growth Rate (YoY)
- **Formula**: `((Current Period Revenue - Prior Period Revenue) / Prior Period Revenue) * 100`
- **Location**: Income Statement — Consecutive periods of Total Revenue / Net Sales.

### Notional Value (Derivatives)
- **Description**: Total underlying value of contract positions (swaps, forwards, options).
- **Location**: Notes to Financial Statements — "Derivative Instruments" / "Hedging Activities".
- **Conventions**: Reported directly in notes tables; identify contract with highest aggregate notional amount.

### Restructuring Costs
- **Description**: One-time reorganization, severance, or facility closure charges.
- **Location**: Income Statement (line item if broken out) or Notes to Financial Statements.
