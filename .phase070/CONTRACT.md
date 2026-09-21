# DEALER AI OS V2
# PHASE 070 — FINAL PRODUCT COMPLETION

## MISSION

Finish Dealer AI OS V2 as the actual product requested by the owner.

Previous phases passing automated tests DOES NOT mean the product is finished.

The final product must visibly implement the approved Dealer AI OS V2 experience on desktop and mobile while preserving the working V2 backend, security, authentication, permissions, AI foundations, integrations, and existing business logic.

---

# 1. NON-NEGOTIABLE SAFETY

PRODUCTION MUST NOT BE TOUCHED.

Production:
    /var/www/carplus

Development V2:
    /opt/dealer-ai-v2/app

Never:

- deploy to production
- modify production files
- modify production database
- use real customer information
- send real SMS/messages
- enable real providers
- expose secrets
- delete working V2 functionality
- reset or destroy Git history

All development remains isolated in Dealer AI OS V2.

---

# 2. VISUAL TARGET IS REQUIRED

The final UI must implement the approved visual direction supplied by the owner.

DESKTOP TARGET:

Professional dark Dealer AI dealership operating system with:

- CarPlus Dealer AI V2 branding
- professional left navigation
- top search/header
- modern dashboard
- KPI cards
- Action Center
- inventory overview
- lead overview
- sales information
- appointments
- recent activity
- Jarvis assistant
- insights
- quick actions
- responsive layout

The result must NOT simply preserve the old CRM interface.

MOBILE TARGET:

Native-app-like responsive experience with bottom navigation:

    Home
    Inventory
    Leads
    Jarvis
    More

and appropriate contextual access to:

- appointments
- customers
- reports
- settings
- documents
- conversations
- developer tools where authorized

The mobile version must not merely be the desktop sidebar compressed onto a phone.

---

# 3. HOME / ACTION CENTER

Home must prioritize operational actions, not decorative statistics.

Include useful actionable information such as:

- today's appointments
- appointments awaiting confirmation
- new leads
- leads older than 48 hours
- stale leads
- unread conversations
- incomplete documents
- prequalification status
- near-close deals
- follow-ups due
- inventory requiring attention

Quick actions should include relevant operations such as:

- call
- SMS
- open lead/customer
- confirm appointment
- create appointment
- add lead
- add vehicle

Use existing backend functionality where available.

Do not fabricate successful backend operations.

---

# 4. JARVIS

Jarvis must feel integrated into Dealer AI OS.

Architecture:

AI
→ intent
→ permission engine
→ typed CRM tool
→ API
→ database
→ audit

Never permit unrestricted LLM database writes.

Sensitive/destructive operations require appropriate confirmation.

Jarvis UI must work on desktop and mobile.

Do not show capabilities as functional if they are not connected.

---

# 5. UNIFIED DEMO MODE

DO NOT create a separate Demo application or separate Demo dashboard.

Demo must use the SAME Dealer AI OS interface.

Create/support a Demo user/role or equivalent controlled capability.

Example:

    role = demo

The Demo user logs in through the normal login.

The Demo user sees the same product UI but receives isolated fictional data.

Demo dataset should provide realistic fictional examples for:

- vehicles
- leads
- customers
- appointments
- sales/deals
- conversations
- activities
- reports
- financial examples where appropriate
- attribution examples
- AI/Jarvis examples
- document metadata without real sensitive documents

Display a persistent but unobtrusive:

    DEMO

indicator.

Provide a safe Demo reset mechanism if architecture permits.

Demo data must never mix with production or real V2 dealership data.

Demo actions must never invoke real external providers.

---

# 6. DESKTOP NAVIGATION

Implement a coherent navigation model based on actual supported modules.

Expected areas include:

- Dashboard / Home
- Inventory
- Leads
- Customers
- Deals / Sales
- Conversations
- Appointments / Agenda
- Documents
- Reports
- AI / Jarvis
- Settings

Developer Mode must be visible only to authorized roles.

---

# 7. MARKETING BOUNDARY

Dealer AI OS is NOT the social-content publishing system.

Dealer AI OS:

    converse
    qualify
    follow up
    attribute
    convert
    sell

Marketing AI OS:

    create content
    publish content
    attract people

Remove or redesign UI implying Dealer AI directly performs Marketing OS content publishing.

Dealer AI may contain:

- conversation sources
- campaign attribution
- social lead origin
- campaign leads
- Marketing OS integration/status

Do not duplicate Marketing AI OS.

---

# 8. SOCIAL CONVERSATIONS

Where architecture supports it, Dealer AI should be prepared for conversations originating from:

- Facebook
- Instagram
- TikTok
- website chat
- SMS
- future WhatsApp integration

Official/legal provider constraints must be respected.

Human takeover always wins.

Unknown contacts may become pending/new leads.

No real provider communication during development.

---

# 9. INVENTORY

Professional desktop and mobile inventory experience.

Support existing functionality and expose it coherently:

- vehicle list
- search
- filters
- vehicle detail
- status
- pricing
- vehicle matching where implemented
- add/edit operations according to permissions

Do not create fake backend capabilities solely to match the mockup.

---

# 10. LEADS / COMMERCIAL PIPELINE

Present the existing commercial pipeline professionally.

Support:

- source
- status
- salesperson
- vehicle interest
- follow-up
- appointments
- communication history
- attribution
- lead scoring where implemented
- recovery workflow where implemented

Map existing statuses safely.

Do not blindly replace existing data models.

---

# 11. CUSTOMERS

Customer experience must expose existing CRM capabilities clearly.

Respect authorization and privacy boundaries.

Sensitive information must never be sent to Marketing OS or exposed to unauthorized roles.

---

# 12. APPOINTMENTS

Desktop and mobile agenda/calendar experience.

Include where supported:

- appointment date/time
- customer/lead
- vehicle
- appointment type
- confirmation state
- assigned salesperson
- quick actions

---

# 13. REPORTS / FINANCIAL

Professional reports using real application data or isolated Demo data.

Where implemented, expose:

- sales
- leads
- appointments
- close rate
- attribution
- inventory
- financial summaries

Financial calculations must use the implemented financial model rather than invented UI-only numbers.

---

# 14. AUTHENTICATION

Preserve existing hardened V2 authentication.

Current authentication functionality must not regress.

Desktop and mobile login must work.

Do not weaken security merely to simplify UI development.

---

# 15. RESPONSIVE QUALITY

Explicitly test at least representative widths:

    390px
    430px
    768px
    1024px
    1440px+

Check:

- overflow
- menus
- dialogs
- tables
- cards
- forms
- navigation
- Jarvis
- touch targets
- typography
- loading states
- error states

---

# 16. FUNCTIONAL UI RULE

No decorative fake buttons.

Every visible action must be one of:

A. connected and functional
B. clearly disabled with explanation
C. explicitly marked future/pending integration

Never present a fake successful action.

---

# 17. PRESERVE EXISTING V2 WORK

Do not rewrite working architecture unnecessarily.

Reuse:

- backend
- API routes
- authorization
- authentication
- security
- AI foundations
- document authorization
- Demo isolation foundations
- existing CRM modules
- existing tests

Refactor only when necessary.

---

# 18. QA

Completion requires more than compilation.

Run:

- frontend build
- Python compile
- authentication tests
- authorization tests
- security tests
- Demo isolation tests
- relevant existing regression tests
- responsive UI checks
- route checks

Fix regressions before completion.

---

# 19. VISUAL FIDELITY GATE

This phase MUST NOT pass merely because tests pass.

Before PASS:

1. render actual desktop UI
2. render actual mobile UI
3. compare them against approved visual references
4. identify discrepancies
5. correct material discrepancies
6. repeat visual verification

The final report must explicitly describe:

- what matches
- what differs
- why any intentional difference exists

---

# 20. REAL USER JOURNEYS

Verify at minimum:

ADMIN:

login
→ dashboard
→ leads
→ customer
→ appointment
→ inventory
→ Jarvis
→ reports/settings

DEMO:

normal login
→ same Dealer AI OS
→ fictional isolated data
→ perform safe Demo interactions
→ verify no real provider interaction
→ reset Demo if implemented

MOBILE:

login
→ Home
→ Inventory
→ Leads
→ Jarvis
→ More
→ key CRM action

---

# 21. DEFINITION OF DONE

Phase 070 is PASS only when:

- approved visual direction is actually implemented
- desktop is usable
- mobile is usable
- unified Demo behavior is implemented
- Demo is NOT a separate product/dashboard
- existing V2 functionality remains intact
- login works
- major navigation works
- critical actions work
- no critical/high regression remains
- no production modification occurred
- automated regression passes
- visual verification passes
- final screenshots/evidence are produced
- final completion report is produced

A technically passing backend with the old frontend is NOT completion.

---

# 22. STOP CONDITIONS

Stop and report BLOCKED rather than guessing if work requires:

- production modification
- real customer data
- credentials/secrets
- real external provider activation
- destructive migration
- unsupported API access
- owner approval for a major product-direction change

Otherwise continue autonomously until the phase is genuinely complete.

