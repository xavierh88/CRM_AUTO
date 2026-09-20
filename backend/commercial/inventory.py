"""Fictional inventory contracts for later matching, without lending decisions."""
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal
from pydantic import Field, model_validator
from .common import DomainModel, Identifier, Money

Year = Annotated[int, Field(strict=True, ge=1886, le=2100)]


class Vehicle(DomainModel):
    vehicle_id: Identifier
    stock_number: Identifier
    make: Identifier
    model: Identifier
    year: Year
    body_type: Identifier
    mileage: Annotated[int, Field(strict=True, ge=0)]
    asking_price: Money
    acquired_on: date
    availability: Literal['AVAILABLE', 'RESERVED', 'SOLD'] = 'AVAILABLE'
    is_mock: Literal[True] = True


class VehiclePreference(DomainModel):
    budget: Money | None = None
    down_payment: Money | None = None
    payment_preference: Money | None = None
    min_year: Year | None = None
    max_year: Year | None = None
    body_type: Identifier | None = None
    credit_constraints: tuple[str, ...] = ()

    @model_validator(mode='after')
    def validate_years(self):
        if self.min_year and self.max_year and self.min_year > self.max_year:
            raise ValueError('min_year exceeds max_year')
        return self


def mock_inventory() -> list[Vehicle]:
    return [Vehicle(vehicle_id=f'mock-vehicle-{i}', stock_number=f'MOCK-{i}', make='Fictional Motors', model=model, year=2022+i, body_type=body, mileage=10000*i, asking_price=Decimal(price), acquired_on=date(2026, 1, 1)) for i, (model, body, price) in enumerate([('City', 'Sedan', '15000'), ('Trail', 'SUV', '22000'), ('Work', 'Truck', '28000')], start=1)]
