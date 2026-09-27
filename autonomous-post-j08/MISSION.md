# DEALER AI OS V2 — POST J08 AUTONOMOUS WORK

WORK ONLY IN THIS WORKTREE.

J01-J03 = APPROVED BY OWNER.
J04-J08 = BEING MANUALLY VALIDATED.

Do NOT modify J04-J08 unless an explicit technical dependency is discovered.
If dependency exists, document it and continue with an independent task.

==================================================
J09 — MODERNIZE CRM FORMS
==================================================

FIRST PRIORITY.

Modernize the existing old CRM forms:

1. Client Profile
2. Opportunity
3. Co-Signer

This is a real UX modernization, NOT merely changing colors.

AUDIT FIRST:

- existing fields
- validation
- permissions
- API calls
- create/edit behavior
- persistence
- relationships
- mobile behavior
- existing reusable components

Then implement the modern V2 experience.

Preserve every existing supported field and capability.

Do not invent backend fields.

Client Profile:
- logical sections
- modern field layout
- clear required/optional states
- validation
- loading/error/success states
- responsive desktop/tablet/mobile

Opportunity:
- modern V2 layout
- preserve all existing opportunity data
- preserve status
- preserve relationships
- preserve create/edit behavior

Co-Signer:
- modern V2 layout
- preserve buyer/cosigner relationship
- preserve all supported data
- preserve authorization
- responsive mobile/desktop

Verify:
- create
- edit
- save
- reload
- validation
- permissions
- mobile
- frontend build

Write:
autonomous-post-j08/reports/J09_MODERN_CRM_FORMS.md

==================================================
J10 — REAL DASHBOARD
==================================================

Audit Dashboard.

Fix real-data endpoints and authorization issues.

Known possible issues:
- Recent Activity 404
- Action Items 403

No mock statistics.

Write:
autonomous-post-j08/reports/J10_DASHBOARD.md

==================================================
J11 — REAL CONVERSATIONS
==================================================

Audit real conversation data sources and authorization.

Fix applicable internal 403/404 issues.

Jarvis may only access authorized real conversation data.

Never send real external messages.

Write:
autonomous-post-j08/reports/J11_CONVERSATIONS.md

==================================================
J12 — PREQUALIFICATION / FINANCING
==================================================

Audit current implementation.

Fix internal issues where possible.

Do not perform real lender, bank, credit, or financial submissions.

External dependency = PENDING_EXTERNAL.

Write:
autonomous-post-j08/reports/J12_PREQUALIFICATION.md

==================================================
J13 — ANDROID SMS GATEWAY
==================================================

Prepare architecture for:

- Android gateway
- authentication
- heartbeat
- online/offline
- inbound queue
- outbound queue
- delivery status
- retry
- contact/client association
- audit history
- tenant isolation

NO real SMS during autonomous QA.

Write:
autonomous-post-j08/reports/J13_ANDROID_SMS_GATEWAY.md

==================================================
J14 — JARVIS ACTIONS
==================================================

Prepare controlled CRM mutations:

- appointments
- lead updates
- notes
- follow-ups

Use actual backend tools.

Sensitive mutations require confirmation.

Never claim success unless backend actually succeeds.

Write:
autonomous-post-j08/reports/J14_JARVIS_ACTIONS.md

==================================================
J15 — CONTINUOUS VOICE
==================================================

Build on existing STT/TTS/Voice.

Safe flow:

listen -> transcribe -> Jarvis -> TTS -> listen

Must have explicit start/stop.

No uncontrolled microphone loop.

Write:
autonomous-post-j08/reports/J15_CONTINUOUS_VOICE.md

==================================================
J16 — DOCUMENT INTELLIGENCE
==================================================

Extend supported document handling where architecture allows:

PDF
DOC/DOCX
XLS/XLSX
CSV
TXT

Respect permissions and client association.

No fabricated extraction.

Write:
autonomous-post-j08/reports/J16_DOCUMENT_INTELLIGENCE.md

==================================================
J17 — SAAS / MULTI-TENANT READINESS
==================================================

Audit:

- tenant isolation
- roles
- authorization
- API boundaries
- demo data
- mobile/PWA readiness
- security
- deployment readiness

DO NOT touch production.

Write:
autonomous-post-j08/reports/J17_SAAS_READINESS.md

==================================================
GLOBAL RULES
==================================================

NEVER TOUCH:

/var/www/carplus
SoyEcua
production
deploy screen sessions

NEVER:

git reset --hard
git clean
force push
delete existing backups
send real SMS
send real WhatsApp/email
perform real financing
modify production

Preserve uncommitted work.

Maximum 2 reasonable attempts per blocker.

If blocked:

STATUS=BLOCKED

Record:
- exact error
- files
- attempts
- recommendation

Then continue with an independent task.

Allowed statuses:

NO_INICIADO
EN_DESARROLLO
BLOCKED
LISTO_PARA_PRUEBA

Never use:
APROBADO_POR_TI

LISTO_PARA_PRUEBA requires actual automatic evidence.

For meaningful frontend changes:

REACT_APP_BACKEND_URL='' npm run build

For backend changes:

python3 -m py_compile backend/server.py

Do not claim tests that were not actually executed.

When the available autonomous work is complete, EXIT.
Do not wait.
Do not monitor.
Do not remain alive.
