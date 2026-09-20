"""Opaque reference-only contract: no credit checks, documents, or financial decisions."""
from dataclasses import dataclass
from typing import Protocol

from .models import required


@dataclass(frozen=True)
class PrequalifyResult:
    customer_id: str
    request_id: str
    status: str = 'PENDING_PROVIDER_INTEGRATION'
    simulated: bool = True


class PrequalifyProvider(Protocol):
    def submit(self, customer_id: str, request_id: str, consent: bool) -> PrequalifyResult: ...


class MockPrequalifyProvider:
    def submit(self, customer_id: str, request_id: str, consent: bool) -> PrequalifyResult:
        required(customer_id)
        required(request_id)
        if consent is not True:
            raise ValueError('Explicit consent required')
        return PrequalifyResult(customer_id, request_id)
