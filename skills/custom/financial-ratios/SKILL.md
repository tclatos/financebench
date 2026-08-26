---
name: financial-ratios
description: Reference for financial ratio, margin, and metric definitions, formulas, components, and conventions (quick ratio, ROE, EBITDA, free cash flow, DSO, etc.) when computing or interpreting figures from financial statements. Use when a question involves a named ratio/margin/metric, units or sign conventions, or where-to-find guidance for a line item.
---

# Financial Ratios & Metrics Reference

Canonical definitions, formulas, components, and conventions for common financial
metrics. Use this to compute and interpret figures correctly (e.g. the quick
ratio EXCLUDES inventory; ROE uses net income attributable to common
shareholders; capex is reported as a positive amount unless a signed cash-flow
value is requested).

## How to use this skill

The index below names each metric, its category, and where to find it in the
filing. For the FULL formula, alternate formulas, numerator/denominator
components, and critical conventions (what to include/exclude, sign handling,
period choice), `read_file` this skill's `financial_kb.json` and look up the
term by key or alias.

## Index (31 metrics)

### Liquidity
- `quick_ratio` — Quick Ratio (Acid-Test) — Balance sheet (current assets &
  liabilities) — short-term coverage excluding inventory.
- `current_ratio` — Current Ratio — Balance sheet (total current
  assets/liabilities) — ability to pay 1-year obligations.
- `working_capital` — Working Capital — Balance sheet (current assets −
  liabilities) — short-term financial health.
- `working_capital_ratio` — Working Capital Ratio — Balance sheet — current
  assets ÷ current liabilities.
- `operating_cash_flow_ratio` — Operating Cash Flow Ratio — Cash flow statement
  + balance sheet — covers current liabilities from operations.

### Profitability
- `return_on_equity` — ROE — Income statement (net income) + balance sheet
  (equity) — profitability vs shareholders' equity.
- `return_on_assets` — ROA — Income statement + balance sheet (total assets) —
  profit per unit of assets.
- `operating_margin` — Operating Margin — Income statement (operating income /
  revenue) — post-operating-expense revenue share.
- `gross_profit_margin` — Gross Profit Margin — Income statement (revenue, COGS)
  — post-COGS revenue share.
- `net_profit_margin` — Net Profit Margin — Income statement (net income,
  revenue) — bottom-line share.
- `ebitda` — EBITDA — Income statement + cash flow (D&A) — operating cash-flow
  proxy.
- `ebitda_margin` — EBITDA Margin — Income statement + cash flow — EBITDA as %
  of revenue.
- `earnings_per_share` — EPS — Income statement (EPS section) — net income per
  share (basic & diluted).
- `depreciation_amortization_rate` — D&A % of Revenue — Cash flow (D&A) + income
  (revenue) — D&A as % of revenue.
- `effective_tax_rate` — Effective Tax Rate — Income statement (tax provision /
  pre-tax) — actual tax % paid.

### Solvency
- `debt_to_equity` — Debt-to-Equity — Balance sheet (liabilities, equity) —
  debt vs equity funding.
- `interest_coverage_ratio` — Interest Coverage — Income statement (EBIT,
  interest expense) — ability to pay interest.

### Efficiency
- `inventory_turnover` — Inventory Turnover — Income statement (COGS) + balance
  sheet (inventory avg) — inventory sales cycles.
- `days_payable_outstanding` — DPO — Balance sheet (A/P) + income (COGS) — days
  to pay suppliers.
- `days_sales_outstanding` — DSO — Balance sheet (A/R) + income (revenue) — days
  to collect.
- `asset_turnover` — Asset Turnover — Income (revenue) + balance sheet (total
  assets) — revenue per unit assets.
- `capital_intensity` — Capital Intensity — Balance sheet (assets, PP&E) +
  income (revenue) + cash flow (capex) — capital needed per revenue.

### Cash flow
- `free_cash_flow` — FCF — Cash flow (operating − investing PP&E) — cash after
  opex & capex.
- `fcf_conversion` — FCF Conversion — Cash flow (OCF, capex) — net income to FCF
  efficiency.

### Growth
- `revenue_growth_rate` — Revenue Growth Rate (YoY) — Income statement (revenue,
  consecutive periods) — period-over-period % change.

### Investment
- `capital_expenditure` — CapEx — Cash flow (investing activities) — funds for
  acquiring/upgrading physical assets.

### Shareholder returns
- `dividend_payout_ratio` — Dividend Payout Ratio — Cash flow/equity (dividends)
  + income (net income) — % of net income paid as dividends.

### Valuation
- `price_to_earnings` — P/E — Stock price + income (EPS) — price vs earnings per
  share.
- `book_value_per_share` — BVPS — Balance sheet (equity, preferred, shares
  outstanding) — net assets per share.

### Derivatives
- `notional_value` — Notional Value (Derivatives) — Notes (derivatives/hedging) —
  underlying amount of a derivative.

### Special items
- `restructuring_costs` — Restructuring Costs — Income statement or notes —
  one-time reorg expenses.

## Source

Vendored from `NanoNets/nanoindex`
(`nanoindex/knowledge/financial_kb.json`, v1.0), which compiles definitions from
Investopedia, Corporate Finance Institute, Wall Street Prep, Investing.com, and
SEC filings standards. See that project for licensing. `read_file
financial_kb.json` for any term's full detail.
