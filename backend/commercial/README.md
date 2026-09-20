# Commercial foundation

Independent Python/Pydantic v2 package for MASTER_BUILD_SPEC sections 7, 17,
18 and 21 and IMPLEMENTATION_PLAN phase 2 / inventory preparation in phase 5.
No server imports, routes, persistence, external calls or customer fixtures.
The supplied worktree instruction supersedes AGENT_RULES' original app path and
branch restriction. The requested CODEX-NAVIGATION-GUIDE.md was not present in
this worktree or the app docs path.

## Integration contract

Import from `backend.commercial` submodules when running from the repository
root, or `commercial` submodules when running from `backend`.

```python
from backend.commercial.finance import FinancialInput, calculate

result = calculate(FinancialInput(
    vehicle_purchase_cost='10000.00', sale_price='14000.00',
    contract_amount='14000.00', down_payment='2000.00',
))
assert result.net_profit == 4000
payload = result.model_dump(mode='json')  # Decimal values become strings
```

The supervisor should register authorized routes, scope every cohort to the
permitted tenant/role/date range, persist separate commercial fields and audit
transitions. This package intentionally exposes no HTTP endpoint. Financial
visibility and permission tests belong to that integration. Call Pydantic
`model_validate` at input boundaries; do not use `model_construct` or unvalidated
`model_copy(update=...)` for external payloads.

## Pipeline compatibility

All 15 requested stages use the spec's exact labels. `commercial_stage` is a
new field. `map_legacy` projects without changing any inherited data:

1. Explicit canonical value wins. Invalid canonical values require review.
2. `record_status=completed` means SOLD (confirmed in inherited server logic).
3. Explicit `appointment_status` supports agendado/confirmado/reagendado/scheduled
   as APPOINTMENT and cumplido as SHOW.
4. Everything else stays unmapped and requires review.

Do not pass generic `status` or `finance_status` as commercial stage. Existing
`financiado`/`lease` describes financing type, `pending` is ambiguous, no-show is
not LOST, and color codes describe contact freshness. An appointment projection
is a hint, not an automatic overwrite of a deal's stage. The caller must choose
which appointment is relevant. `transition` returns a deep copy with only the
canonical field changed; it neither writes data nor enforces an invented linear
sales sequence. Preserve original fields during any later migration.

## Attribution

All 11 sources and four acquisition types are enumerated. `map_source` matches
canonical sources ignoring case and surrounding whitespace, while retaining the
exact original source in `legacy_source`. Unknown source and acquisition type
remain null until explicitly classified. A source never implies AI acquisition.

## Financial policy

All monetary inputs are nonnegative finite Decimal amounts with at most two
decimal places and 16 digits. Negative profits are valid. Unknown extra fields
(including caller-supplied calculated totals) are rejected. Inputs default to
zero for explicit draft calculations; these defaults do not establish that
missing inherited amounts were actually zero. No automatic financial migration
is provided: an integrator must reconcile incomplete or formatted legacy strings
and distinguish commission meanings before building FinancialInput.

Use a single currency per cohort (two-decimal currency such as USD); currency
conversion is not implemented. Income fields mean recognized net income, not
product retail price. Taxes, trade equity, refunds and loan amortization are not
inferred.

- total_vehicle_cost = purchase + reconditioning + transport + auction + other acquisition
- financed_amount = contract_amount - down_payment (negative funding rejected)
- front_end_gross = sale_price - total_vehicle_cost
- back_end_gross = dealer_reserve + warranty_income + gap_income + other_backend_income
- gross_profit = front_end_gross + back_end_gross
- commissions = salesperson + BDC + referral commissions
- net_profit = gross_profit - commissions - other_expenses

Contract volume is tracked independently of sale revenue. Down payment is a
funding allocation, not additional revenue. Reserve/backend income is counted
once. Calculations remain exact; monetary averages use half-up cent rounding.

`summarize` accepts a caller-selected, unique-deal cohort. It rejects duplicate
IDs, inconsistent SOLD/date states and reversed dates. Only SOLD deals contribute
to units, sales, contract volume, vehicle cost, front/back gross, gross profit,
commissions, expenses, net profit and per-unit averages.

`days_to_sale` is the average calendar days from vehicle acquisition to sale for
sold deals with acquisition dates. `approval_to_sale_conversion` is a ratio 0–1:
sold deals with approval dates / all deals with approval dates in the supplied
cohort, including subsequently lost/declined deals. Do not select only sold deals
when calculating conversion. Missing denominators return null, not a misleading
zero. Empty monetary totals return zero. No date filtering is implicit.

## Inventory

`mock_inventory()` returns fresh, validated fictional vehicles with MOCK stock
numbers, availability, price, acquisition date, year, body type and mileage.
VehiclePreference captures budget, down payment, preferred monthly payment,
year range, body type and non-sensitive credit constraints for later matching.
No match ranking, credit decision, payment estimate or external inventory is
implemented. These fixtures are not the application's Demo Mode.

## Verification

See [test evidence](../../docs/testing/commercial-foundation.tdd.md).
