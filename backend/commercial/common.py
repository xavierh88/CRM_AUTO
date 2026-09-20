"""Shared validation for new commercial contracts only."""
from decimal import Decimal
from typing import Annotated
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def reject_boolean(value):
    if isinstance(value, bool):
        raise ValueError('Money cannot be a boolean')
    return value


Money = Annotated[Decimal, BeforeValidator(reject_boolean), Field(ge=0, max_digits=16, decimal_places=2, allow_inf_nan=False)]
Identifier = Annotated[str, Field(min_length=1, max_length=128)]


class DomainModel(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, str_strip_whitespace=True)
