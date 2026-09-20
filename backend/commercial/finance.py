"""Exact decimal calculations for a single currency and explicit deal cohort."""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable
from pydantic import model_validator
from .common import DomainModel, Identifier, Money
from .pipeline import Stage


class FinancialInput(DomainModel):
    vehicle_purchase_cost: Money = Decimal(0)
    reconditioning_cost: Money = Decimal(0)
    transport_cost: Money = Decimal(0)
    auction_fees: Money = Decimal(0)
    other_acquisition_cost: Money = Decimal(0)
    sale_price: Money = Decimal(0)
    contract_amount: Money = Decimal(0)
    down_payment: Money = Decimal(0)
    dealer_reserve: Money = Decimal(0)
    warranty_income: Money = Decimal(0)
    gap_income: Money = Decimal(0)
    other_backend_income: Money = Decimal(0)
    salesperson_commission: Money = Decimal(0)
    bdc_commission: Money = Decimal(0)
    referral_commission: Money = Decimal(0)
    other_expenses: Money = Decimal(0)

    @model_validator(mode='after')
    def validate_funding(self):
        if self.down_payment > self.contract_amount:
            raise ValueError('down_payment exceeds contract_amount')
        return self


class FinancialResult(DomainModel):
    total_vehicle_cost: Decimal
    financed_amount: Decimal
    front_end_gross: Decimal
    back_end_gross: Decimal
    gross_profit: Decimal
    commissions: Decimal
    net_profit: Decimal


def calculate(values: FinancialInput) -> FinancialResult:
    cost = values.vehicle_purchase_cost + values.reconditioning_cost + values.transport_cost + values.auction_fees + values.other_acquisition_cost
    front = values.sale_price - cost
    back = values.dealer_reserve + values.warranty_income + values.gap_income + values.other_backend_income
    commissions = values.salesperson_commission + values.bdc_commission + values.referral_commission
    return FinancialResult(total_vehicle_cost=cost, financed_amount=values.contract_amount-values.down_payment, front_end_gross=front, back_end_gross=back, gross_profit=front+back, commissions=commissions, net_profit=front+back-commissions-values.other_expenses)


class Deal(DomainModel):
    deal_id: Identifier
    stage: Stage
    financials: FinancialInput
    acquired_on: date | None = None
    approved_on: date | None = None
    sold_on: date | None = None

    @model_validator(mode='after')
    def validate_dates(self):
        if (self.stage == Stage.SOLD) != (self.sold_on is not None):
            raise ValueError('SOLD stage and sold_on must be supplied together')
        if self.sold_on and any(d and d > self.sold_on for d in (self.acquired_on, self.approved_on)):
            raise ValueError('Sale cannot precede acquisition or approval')
        if self.acquired_on and self.approved_on and self.approved_on < self.acquired_on:
            raise ValueError('Approval cannot precede acquisition')
        return self


class FinancialKPIs(DomainModel):
    units_sold: int
    gross_sales: Decimal
    contract_volume: Decimal
    vehicle_cost: Decimal
    front_end_gross: Decimal
    back_end_gross: Decimal
    gross_profit: Decimal
    commissions: Decimal
    other_expenses: Decimal
    net_profit: Decimal
    avg_gross_per_unit: Decimal | None
    avg_net_per_unit: Decimal | None
    days_to_sale: Decimal | None
    approval_to_sale_conversion: Decimal | None


def summarize(deals: Iterable[Deal]) -> FinancialKPIs:
    cohort = list(deals)
    if len({d.deal_id for d in cohort}) != len(cohort):
        raise ValueError('Duplicate deal_id in reporting cohort')
    sold = [d for d in cohort if d.stage == Stage.SOLD]
    results = [calculate(d.financials) for d in sold]
    def total(items):
        return sum(items, Decimal(0))
    def average(amount, count):
        return (amount / count).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if count else None
    gross = total(r.gross_profit for r in results)
    net = total(r.net_profit for r in results)
    durations = [(d.sold_on-d.acquired_on).days for d in sold if d.acquired_on is not None]
    approved = [d for d in cohort if d.approved_on is not None]
    return FinancialKPIs(units_sold=len(sold), gross_sales=total(d.financials.sale_price for d in sold), contract_volume=total(d.financials.contract_amount for d in sold), vehicle_cost=total(r.total_vehicle_cost for r in results), front_end_gross=total(r.front_end_gross for r in results), back_end_gross=total(r.back_end_gross for r in results), gross_profit=gross, commissions=total(r.commissions for r in results), other_expenses=total(d.financials.other_expenses for d in sold), net_profit=net, avg_gross_per_unit=average(gross, len(sold)), avg_net_per_unit=average(net, len(sold)), days_to_sale=average(total(durations), len(durations)), approval_to_sale_conversion=Decimal(sum(d.stage == Stage.SOLD for d in approved))/len(approved) if approved else None)
