# DEALER AI OS V2 — AUTONOMOUS COMPLETION MISSION

MODE: AUTONOMOUS_UNATTENDED
MAX_STATE: LISTO_PARA_TU_PRUEBA

## ABSOLUTE SAFETY

Work ONLY in:
/opt/dealer-ai-v2/worktrees/070-final-product-completion

DO NOT:
- modify /var/www/carplus
- deploy production
- modify SoyEcua
- merge branches
- push or force-push
- git reset --hard
- git clean
- weaken authentication or tenant isolation
- use real customer data
- send real SMS, WhatsApp, social messages or financial transactions
- install unknown APKs
- expose secrets
- mark anything APROBADO

Use synthetic/demo data only.

## WORK METHOD

For every block:

AUDIT
→ REUSE EXISTING FUNCTIONALITY
→ IMPLEMENT
→ BUILD
→ FUNCTIONAL QA
→ API/BACKEND/DATA QA
→ VISUAL/RESPONSIVE QA
→ FIX
→ RETEST
→ REGRESSION
→ REPORT
→ NEXT BLOCK

Build success alone DOES NOT mean a feature is complete.

Maximum autonomous state:
LISTO_PARA_TU_PRUEBA

Only the owner can set:
APROBADO

Do not stop after completing one block unless:
- human credentials/configuration are absolutely required
- an unsafe action would be required
- production would need modification
- continuing could cause data loss.

If an external integration needs human configuration:
mark WAITING_CONFIG and continue with other independent work.

## PRIORITY 0 — FINISH JARVIS VOICE

Current facts:
- Firefox MediaRecorder button is enabled.
- Frontend build currently observed: main.79c15e67.js.
- Backend V2 runs isolated on 127.0.0.1:8102.
- POST /api/jarvis/transcribe exists.
- faster-whisper 1.2.1 installed in project venv.
- backend/voice/stt.py exists.
- STT model default is tiny, CPU int8.
- MIME normalization was added:
  (audio.content_type or "").split(";", 1)[0].strip().lower()
- Current browser still throws React error #31:
  object with keys {title, description}.
- Previous voice frontend patch introduced toast({title, description}).
- Do not assume this project's toast API accepts that object.
- Source-map warning is secondary and must not distract from functional failure.

Required Voice architecture:

MediaRecorder
→ POST /api/jarvis/transcribe
→ STT
→ transcript
→ EXISTING Jarvis message path
→ EXISTING Jarvis reasoning/tools/context
→ response
→ browser TTS

Voice is ONLY an I/O adapter.

DO NOT:
- change Jarvis reasoning to a smaller/weaker model
- reduce Jarvis context/memory merely for Voice
- create a separate Voice brain
- automatically write voice transcripts to long-term memory
- alter existing Jarvis tools unnecessarily.

Voice tasks:
1. Inspect the project's actual toast implementation/API.
2. Remove/fix incompatible toast({title,description}) calls introduced by Voice.
3. Inspect backend logs and actual response from /jarvis/transcribe.
4. Verify MIME handling.
5. Verify PyAV can decode Firefox WebM/Ogg without external ffmpeg.
6. Verify first Whisper model download/load.
7. Make transcription visible in input.
8. Then connect transcript to the EXISTING send path safely.
9. Add TTS only after a successful Jarvis response.
10. Text mode must continue working if microphone/TTS unavailable.
11. Clean up MediaRecorder streams/tracks.
12. Prevent duplicate sends/race conditions.
13. Add reasonable recording/size limits.
14. Add faster-whisper dependency to the appropriate project requirements so deployment is reproducible.
15. Build and run safe automated tests.
16. Report Voice as LISTO_PARA_TU_PRUEBA, never APROBADO.

## PRIORITY 1 — STABILIZATION

Fix and verify:
- Conversations 403
- Dashboard Action Items 403
- Recent Activity 404
- global Jarvis panel state when navigating to Conversations/other routes
- current frontend/backend regressions.

Preserve authorization. Never solve a 403 by weakening tenant isolation.

## PRIORITY 2 — COMMUNICATIONS HUB

Architecture:

External channel
→ Adapter
→ Conversation Gateway
→ Lead/Client
→ Jarvis
→ Human handoff when needed
→ Same channel response

Channels:
- SMS/Phone Android physical gateway FIRST
- WhatsApp
- Facebook Messenger
- Instagram DM
- Website Chat
- Email where appropriate
- TikTok ONLY if official supported bidirectional functionality exists.

No fake connected states.

Persist:
dealer
client/lead
salesperson
channel
messages
consent
state
timestamps
delivery state
attribution
audit trail.

SMS:
research/reuse maintained open-source Android gateway such as TextBee or better suitable alternative before custom implementation.
Do not install unknown APKs automatically.
Real sends require owner authorization/configuration.

## PRIORITY 3 — JARVIS SALES ORCHESTRATOR

Implement explicit controlled commercial state machine:

new message
→ identity/dedupe
→ lead
→ intent
→ qualification
→ vehicle match
→ follow-up
→ prequalification when appropriate
→ negotiation
→ appointment
→ show/no-show
→ opportunity/deal
→ sold/lost
→ recovery.

Jarvis must not arbitrarily invent state transitions.

Support:
- inbound social leads
- qualification
- real inventory matching
- appointments
- salesperson handoff
- follow-up
- authorized negotiation rules
- prequalification workflow
- sold/lost/recovery.

Internal data/report questions must use real authorized data, not hardcoded mock counts.

## PRIORITY 4 — ATTRIBUTION AND METRICS

Track independently:
source
origin
captured_by
assigned_to
appointment_created_by
closer
AI involvement.

Distinguish:
AI_ORIGINATED
AI_ASSISTED
HUMAN_ORIGINATED
OTHER.

Never attribute a sale to AI merely because Jarvis replied.

Metrics:
total leads
AI-originated
AI-assisted
salesperson-originated
appointments AI/human
sales/deals by source
conversion
response time
revenue/profit attribution.

## PRIORITY 5 — MULTI-TENANT SAAS

One common Dealer AI core serving multiple dealers.

dealer_id/tenant_id authorization MUST be enforced in backend.

Strict isolation for:
users
clients
leads
inventory
conversations
documents
appointments
deals
configuration
channels
Jarvis
metrics.

Create deliberate cross-tenant API/ID/session attack tests.

Do not create separate CRM forks per dealer.

## PRIORITY 6 — SUPER ADMIN CONTROL CENTER

Owner-level control center:
- create/edit/activate/suspend dealer
- plans/subscriptions
- modules/features
- users/roles/admins
- branding/logo/colors/name
- domain/subdomain
- SSL status
- communications integrations
- Jarvis configuration
- website configuration
- storage/usage/health
- audit
- explicit audited support access.

No automatic cross-tenant visibility.

## PRIORITY 7 — CUSTOM DOMAINS

Support:
dealer platform subdomain
AND
dealer custom domain.

Hostname resolves tenant before login.

Design:
DNS verification
SSL lifecycle/status
branding/domain UI
safe tenant resolution.

Do not require separate application instance per domain.

## PRIORITY 8 — CUSTOM FIELD CONSTRUCTOR

CRITICAL REQUIREMENT.

Build architecture FIRST, UI SECOND.

Per-dealer dynamic field definitions:
key
label
type
module
required
options
order
group
role visibility
validation
active state
conditional rules/dependencies where appropriate.

Types include:
text
number
money
date
yes/no
dropdown
multi-select
phone
email.

Modules:
Clients
Leads
Opportunities/Deals
Vehicles
Appointments
and compatible future modules.

Dealer A fields must never leak into Dealer B.

Implement:
data model
tenant isolation
backend validation/API
builder UI
dynamic renderer
tests.

Also support per-dealer feature/module flags.

## PRIORITY 9 — DEALER WEBSITES

Dealer websites may have completely different designs.

Website frontend must remain independent from common CRM core.

Support:
Dealer AI templates
AND
fully custom frontend using secure API/SDK.

Website integrations:
inventory
lead forms
interested button
appointments
Jarvis web chat
prequalification.

Preserve:
dealer_id
source
vehicle
campaign attribution.

Website prequalification must enter the correct dealer CRM without retyping.

## PRIORITY 10 — FINANCIAL / COMMISSION / SALES ANALYTICS

Commission applies to EVERY dealer sale according to dealer contract,
not only AI sales.

Keep commission accounting separate from AI attribution.

Per dealer periods:
today
yesterday
week
month
quarter
year
custom.

Metrics:
sales count
gross sales
gross profit when available
expenses
net profit/loss
daily/weekly/monthly results
average profit/vehicle
commission owed
lead metrics
appointment metrics
AI/human attribution
conversion.

Salesperson metrics:
leads
contacts
appointments
show/no-show
opportunities
sales
conversion
time-to-close
sales volume
profit.

Every sale trace should support:
dealer
vehicle
client
lead source
captured_by
Jarvis involvement
salesperson
appointment creator
closer
sale price
profit
date
commission rule.

Commission calculation must be deterministic and auditable.
Jarvis does NOT invent commission calculations.

## PRIORITY 11 — DOCUMENT/STORAGE OPTIMIZATION

Pipeline:
validate
→ security
→ true type detection
→ optimize safely
→ store
→ metadata.

Images:
resize/compress/efficient format when safe.

PDF:
safe optimization where appropriate.

Do not destructively convert documents whose originals must retain legal/operational fidelity.
Store derivative + original where necessary.

Implement:
limits
true MIME
safe names
hash/dedupe
storage metrics.

No data loss.

## PRIORITY 12 — OPPORTUNITY FORM V2

DO NOT redesign blindly.

First create parity matrix of EVERY existing:
field
condition
dependency
validation
calculation
action
endpoint
persisted value.

Then modernize UX while preserving 100% behavioral parity.

Use logical grouping and progressive disclosure.

After redesign compare old vs new field-by-field and behavior-by-behavior.

## PRIORITY 13 — CO-SIGNER FORM V2

Same mandatory parity process as Opportunity form.

No field/condition/logic/persistence loss.

## PRIORITY 14 — BACKUP & RECOVERY

Do not blindly clone the whole platform every 15 days.

Code remains in Git/GitHub.

Design compact recoverable backup for:
database
critical configuration
files/documents according to storage architecture.

Prefer:
compressed/encrypted DB backup
deduplicated file strategy
recoverable ~15-day snapshot where practical
monthly longer retention
automatic retention cleanup
off-server/offsite copy when configured.

Test restore in isolated environment.
A backup is not considered valid merely because a file exists.

Do not exhaust VPS disk/RAM.

## PRIORITY 15 — FINAL QA

Test desktop/tablet/mobile:
390x844
430x932
768x1024
900x1200
1023x1200
1024x1200
1280x800
1440x900.

No horizontal overflow.

End-to-end:
login
leads
clients
inventory
conversations
appointments
documents
deals
reports
Jarvis
Demo
permissions
tenant isolation
Super Admin
custom fields
websites
prequalification.

Verify persistence after refresh.

External integrations without credentials must show honest
NOT CONFIGURED / WAITING_CONFIG states.

Final state remains:
LISTO_PARA_TU_PRUEBA

Production deployment requires explicit owner approval.
