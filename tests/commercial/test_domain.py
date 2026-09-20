import unittest
from copy import deepcopy
from datetime import date
from decimal import Decimal
from pydantic import ValidationError
from backend.commercial.pipeline import Stage, map_legacy, transition
from backend.commercial.attribution import Attribution, map_source
from backend.commercial.finance import Deal, FinancialInput, calculate, summarize
from backend.commercial.inventory import VehiclePreference, mock_inventory


class CommercialTests(unittest.TestCase):
    def test_legacy_mapping_preserves_input(self):
        old = {'record_status': 'completed', 'finance_status': 'lease', 'custom': {'x': 1}}
        snapshot = deepcopy(old)
        self.assertEqual(map_legacy(old).stage, Stage.SOLD)
        self.assertEqual(old, snapshot)
        self.assertIsNone(map_legacy({'finance_status': 'financiado'}).stage)
        self.assertIsNone(map_legacy({'record_status': 'pending'}).stage)
        self.assertTrue(map_legacy({'record_status': 'custom'}).needs_review)

    def test_canonical_and_transition(self):
        for stage in Stage:
            self.assertEqual(map_legacy({'commercial_stage': stage.value}).stage, stage)
        self.assertEqual(map_legacy({'appointment_status': 'cumplido'}).stage, Stage.SHOW)
        self.assertEqual(map_legacy({'commercial_stage': 'bad', 'record_status': 'completed'}).stage, None)
        state = transition({'record_status': 'pending'}, Stage.APPROVED)
        self.assertEqual(state['record_status'], 'pending')
        self.assertEqual(state['commercial_stage'], 'APPROVED')
        with self.assertRaises(ValueError):
            transition({}, 'invalid')

    def test_attribution(self):
        self.assertEqual(map_source(' facebook ').source.value, 'Facebook')
        self.assertEqual(map_source(' custom ').legacy_source, ' custom ')
        self.assertEqual(map_source('custom campaign').legacy_source, 'custom campaign')
        self.assertIsNone(map_source(None).acquisition_type)
        self.assertEqual(Attribution(source='AI Chat', acquisition_type='AI_ASSISTED').acquisition_type.value, 'AI_ASSISTED')
        with self.assertRaises(ValidationError):
            Attribution(acquisition_type='automatic')

    def test_calculation(self):
        inputs = FinancialInput(vehicle_purchase_cost='10000', reconditioning_cost='500', transport_cost='100', auction_fees='200', other_acquisition_cost='50', sale_price='14000', contract_amount='15000', down_payment='2000', dealer_reserve='300', warranty_income='200', gap_income='100', other_backend_income='50', salesperson_commission='400', bdc_commission='100', referral_commission='50', other_expenses='75')
        result = calculate(inputs)
        self.assertEqual(result.total_vehicle_cost, Decimal('10850'))
        self.assertEqual(result.financed_amount, Decimal('13000'))
        self.assertEqual(result.front_end_gross, Decimal('3150'))
        self.assertEqual(result.back_end_gross, Decimal('650'))
        self.assertEqual(result.gross_profit, Decimal('3800'))
        self.assertEqual(result.net_profit, Decimal('3175'))
        self.assertEqual(calculate(FinancialInput(sale_price='0.30', vehicle_purchase_cost='0.10')).net_profit, Decimal('0.20'))
        self.assertEqual(calculate(FinancialInput(vehicle_purchase_cost='100')).net_profit, Decimal('-100'))

    def test_validation(self):
        for value in ['-1', 'NaN', 'Infinity', '1.001', True, '1,000']:
            with self.subTest(value=value), self.assertRaises(ValidationError):
                FinancialInput(sale_price=value)
        with self.assertRaises(ValidationError):
            FinancialInput(contract_amount='1', down_payment='2')
        with self.assertRaises(ValidationError):
            FinancialInput(net_profit='100')
        with self.assertRaises(ValidationError):
            Deal(deal_id='x', stage='SOLD', financials=FinancialInput())

    def test_kpis_and_cohort(self):
        sold = Deal(deal_id='a', stage='SOLD', financials=FinancialInput(sale_price='200', vehicle_purchase_cost='100'), acquired_on=date(2026, 1, 1), approved_on=date(2026, 1, 2), sold_on=date(2026, 1, 11))
        unsold = Deal(deal_id='b', stage='APPROVED', approved_on=date(2026, 1, 3), financials=FinancialInput(sale_price='999'))
        result = summarize([sold, unsold])
        self.assertEqual(result.units_sold, 1)
        self.assertEqual(result.gross_sales, Decimal('200'))
        self.assertEqual(result.avg_net_per_unit, Decimal('100'))
        self.assertEqual(result.days_to_sale, Decimal('10'))
        self.assertEqual(result.approval_to_sale_conversion, Decimal('0.5'))
        self.assertIsNone(summarize([]).approval_to_sale_conversion)
        self.assertIsNone(summarize([]).avg_gross_per_unit)
        with self.assertRaises(ValueError):
            summarize([sold, sold])
        with self.assertRaises(ValidationError):
            sold.model_copy().model_validate({**sold.model_dump(), 'sold_on': date(2025, 1, 1)})

    def test_approval_chronology(self):
        with self.assertRaises(ValidationError):
            Deal(deal_id='x', stage='APPROVED', financials=FinancialInput(),
                 acquired_on=date(2026, 2, 1), approved_on=date(2026, 1, 1))

    def test_mock_inventory(self):
        first = mock_inventory()
        self.assertTrue(all(v.is_mock for v in first))
        self.assertEqual(len({v.vehicle_id for v in first}), len(first))
        first.clear()
        self.assertTrue(mock_inventory())
        VehiclePreference(budget='20000', down_payment='1000', min_year=2020, body_type='SUV', credit_constraints=['manual review'])
        with self.assertRaises(ValidationError):
            VehiclePreference(min_year=2025, max_year=2020)


if __name__ == '__main__':
    unittest.main()
