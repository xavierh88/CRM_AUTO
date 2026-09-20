# Mock communications foundation

Status: PASS for tested local contracts; PENDING_EXTERNAL for all real providers.
Requires Python 3.11+ (StrEnum). No third-party dependencies, configuration reads,
network calls, database access, or server startup. Existing SMS routes are not
rewired. Do not use those legacy routes to exercise this foundation.

## Integration entry points

- `models.Message`: immutable normalized customer_id, channel, direction, actor,
  text, timestamp, delivery_status, provider_message_id, and internal id. All
  timestamps must be timezone-aware. Inbound actor is CLIENT; outbound actors
  are HUMAN, AI, SYSTEM. Inbound delivery is RECEIVED. Mock sends are SIMULATED,
  never SENT/DELIVERED. Other delivery values reserve the future provider contract;
  asynchronous delivery-receipt transitions are not implemented.
- `adapters.CommunicationProvider`: structural send/normalize_inbound interface.
- `adapters.MockProvider`: SMS/email or other channel simulation.
- `adapters.AndroidSmsGateway`: mock SMS, initially OFFLINE. Call
  `heartbeat(trusted_received_at, last_error=None)` using server receipt time,
  not an untrusted device clock. Health contains last_seen, last_error and MOCK
  provider_status. Age <60 seconds is ONLINE, 60–179 is DEGRADED, >=180 is
  OFFLINE; future heartbeat is treated OFFLINE. A reported error degrades fresh
  health; a clean heartbeat clears it. DEGRADED permits simulation. OFFLINE
  blocks and the service records GATEWAY_OFFLINE for callers to display.
- `adapters.WhatsAppAdapter`: WAITING_CONFIG, always blocks outbound.
- `adapters.SocialInboundAdapter`: FACEBOOK/INSTAGRAM normalized inbound only;
  provider integration remains PENDING_EXTERNAL. Outbound returns INBOUND_ONLY.
- `handoff.WhatsAppHandoff`: one instance per conversation. Inbound opens a
  60-second human window. `human_takeover()` suppresses AI until explicit
  `release_to_ai(now)`, which restarts the window. No AI generation or scheduling.
- `prequalify.PrequalifyProvider`: reference-only submit contract. The mock accepts
  explicit consent and opaque customer/request IDs, returns deterministic
  PENDING_PROVIDER_INTEGRATION, and never produces approval or credit decisions.

```python
from datetime import datetime, timezone
from backend.communications.adapters import AndroidSmsGateway
from backend.communications.models import Actor, Channel, Direction, Message
from backend.communications.policy import ContactPolicy
from backend.communications.service import CommunicationService

now = datetime(2026, 9, 20, 15, tzinfo=timezone.utc)
gateway = AndroidSmsGateway()
gateway.heartbeat(now)
service = CommunicationService(gateway)
result = service.send(
    Message(customer_id='synthetic-customer', channel=Channel.SMS,
            direction=Direction.OUTBOUND, actor=Actor.HUMAN,
            text='Synthetic message', timestamp=now, id='synthetic-request'),
    ContactPolicy(consent=True), now)
assert result.delivery_status == 'SIMULATED'
```

Inbound internal payload: `provider_message_id` (nonempty string), `text`
(nonempty string), `timestamp` (ISO-8601 with timezone). Supply the separately
resolved, authorized customer ID to `service.receive(payload, customer_id)`.
Do not infer customer identity from arbitrary webhook fields. Unknown payload
fields are discarded. This is not a claim of compatibility with any vendor schema.

## Contact controls and storage boundary

Use the service, not adapters directly, for policy enforcement. Consent defaults
false; opt-out wins. Default quiet hours are 21:00 inclusive to 08:00 exclusive
in configured IANA timezone (UTC default); equal start/end blocks the whole day.
The cap defaults to three successful simulations in a rolling 24-hour interval,
excluding the exact lower boundary. Execution time, not request time, is counted.
STOP, STOPALL, UNSUBSCRIBE, CANCEL, END, QUIT suppress future contact on this
service instance. START does not restore consent automatically.

One service instance belongs to one tenant/provider. Its lock makes replay checks
and frequency counting atomic within that instance. Same outbound ID with same
request returns the original result; conflicting reuse fails. A blocked request
needs a new ID for a deliberate retry. Inbound IDs are provider-scoped; conflicting
replays fail. Message snapshots are immutable; events exclude content.

State is memory-only and resets on restart. Before a real integration, the
supervisor must supply durable tenant/customer/channel consent and opt-out state,
shared frequency accounting, transactional idempotency across workers, authenticated
and authorized routes, verified webhook signatures, authorized customer resolution,
provider error/retry mapping, retention, and delivery receipts. No routes are mounted
here, and no HTTP/RBAC readiness is claimed. WhatsApp handoff is an eligibility
foundation, not a concurrent distributed conversation controller.

## Verification and handoff

2026-09-20:

- RED: test import failed before the implementation existed.
- GREEN: `python3 -m unittest discover -s tests/offline -v`: 37 tests passed,
  including 14 communications tests covering normalization, validation, replay,
  health thresholds/errors, policy boundaries, STOP, concurrency, handoff, and
  pending-provider behavior.
- Build: `python3 -m compileall -q backend/communications` passed.
- Coverage: `python3 -m trace --count --summary --missing --coverdir
  /tmp/communications-coverage --module unittest discover -s tests/offline
  -p test_communications.py`: service 98%; other new modules 100% traced lines.
  This is line tracing, not branch coverage; coverage.py is unavailable.
- Static lint/type checks: unavailable (ruff, flake8, mypy not installed).
- Diff whitespace check passed; inspected imports contain only standard library
  and this package. No central server, legacy provider, or frontend changes.
- Full application/UI/network tests were not run: this deliverable is a standalone
  backend foundation. Existing offline regression tests passed.
- No inherited upload contents, real customer data, production, credentials,
  communications, deployments, commits or other Git mutations were used.

Self-evaluation (agent-self-evaluation skill): accuracy 4/5 (line coverage, not
branch coverage); completeness 4/5 (mock foundations complete, provider validation
pending); clarity 4/5 (integration assumptions documented, no HTTP example because
routes remain unmounted); actionability 4/5 (runnable local example, durable host
integration remains); conciseness 4/5 (handoff details intentionally retained).
Average 4.0/5. Highest-impact follow-ups: durable policy/idempotency integration,
then authenticated vendor webhook translation and validation. These are explicit
integration limits, consistent with the requested mock-only scope.
