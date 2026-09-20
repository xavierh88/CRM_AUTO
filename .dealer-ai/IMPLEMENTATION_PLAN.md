# DEALER AI OS V2 - IMPLEMENTATION PLAN

## AUDIT SUMMARY
The existing repository has a solid foundation utilizing FastAPI (Python) and React (with Tailwind CSS/shadcn-ui). 
- **Existing Functionality:** JWT authentication, Role-Based Access Control (Admin, BDC Manager, Telemarketer/Salesperson), Client Management (CRUD, file uploads for ID/Income/Residence), User Records/Cartillas with sales commission, Appointment scheduling, basic SMS via Twilio, and Email notifications (Resend/SMTP). There are also foundational tests in both `backend/tests` and `tests`.
- **Missing Functionality:** Mobile-first bottom navigation, Passkeys/WebAuthn, Advanced Customer 360 with AI summaries, full Commercial Pipeline mapping, Appointment Guardian automation, Communication Abstraction (Android SMS adapter, WhatsApp architecture), Jarvis AI tools, Developer Mode, Custom Fields/Modules engine, Schema Audit, comprehensive Financial Panel, Vehicle Matching AI, Lost Lead Recovery, Website AI Chat, Attribution tracking, Marketing AI Hub, Demo Mode & Guided Tour.

Based on the audit, the development will be divided into 8 safe sequential phases. Prioritizing foundational architecture before cosmetic work.

---

## PHASE 1: Security, Roles & Infrastructure Foundation
**Goal:** Establish Developer Mode, Schema Auditing, and Document Security.

1. **Existing functionality being reused:** RBAC, Document Uploads, MongoDB connection.
2. **New functionality required:** Developer Mode (SYSTEM_DEVELOPER role), Schema Audit logging, `.gitignore` document protections.
3. **Files/modules likely affected:** `backend/auth.py`, `backend/models/user.py`, `backend/server.py`, `.gitignore`.
4. **Database/model changes:** Add `SchemaAudit` collection, add `SYSTEM_DEVELOPER` role.
5. **API changes:** New endpoints for Schema Audit logs and Developer Mode verification.
6. **Frontend changes:** Developer Mode protected routes and toggle.
7. **Security implications:** Protect structural changes behind DEVELOPER MODE with re-authentication. Ensure real documents aren't versioned.
8. **Tests required:** RBAC tests for SYSTEM_DEVELOPER, Schema Audit logging tests, Document security ignore tests.
9. **Dependencies on other phases:** None.
10. **Definition of PASS:** SYSTEM_DEVELOPER can log in, structural changes log to SchemaAudit, uploads directory strictly ignored by git.
11. **Rollback/checkpoint strategy:** Revert `auth.py` and `server.py` additions.

---

## PHASE 2: Data Modeling & CRM Core Expansion
**Goal:** Implement Commercial Pipeline, Custom Fields/Modules, Financial Panel, and Attribution.

1. **Existing functionality being reused:** User Records/Cartillas, Client models.
2. **New functionality required:** Status mapping (NEW LEAD to SOLD), Custom Field Engine, Financial Panel model per deal.
3. **Files/modules likely affected:** `backend/models/client.py`, `backend/models/record.py`, `backend/server.py`, frontend Client and Record components.
4. **Database/model changes:** Add `CustomFields`, `CustomModules` collections. Update `Client` and `UserRecord` with Attribution and Financial KPIs.
5. **API changes:** CRUD for Custom Fields, Pipeline state transition endpoints, Financial calculation endpoints.
6. **Frontend changes:** Financial Panel UI on sold deals, Custom Module renderer for Developer Mode.
7. **Security implications:** Financial data visibility restricted to authorized roles.
8. **Tests required:** Financial calculation tests, Custom field validation tests.
9. **Dependencies on other phases:** Phase 1 (Developer Mode for Custom Modules).
10. **Definition of PASS:** Pipeline states accurately change, financial panel calculates gross/net profits correctly, custom fields can be created and saved.
11. **Rollback/checkpoint strategy:** Database schema rollbacks via Schema Audit.

---

## PHASE 3: Communications Hub & Adapters
**Goal:** Create abstraction layer for communications and prepare Android SMS/WhatsApp/Prequalify adapters.

1. **Existing functionality being reused:** Twilio SMS logic, Email logic, Prequalify routes.
2. **New functionality required:** Communication Abstraction Layer, Android SMS Gateway Adapter (Mock), WhatsApp AI Takeover Architecture, Prequalify Provider Adapter.
3. **Files/modules likely affected:** `backend/services/sms.py` (new), `backend/services/communications.py` (new), `backend/server.py`.
4. **Database/model changes:** Unified `CommunicationLog` (merging sms_logs/emails), Actor tracking (CLIENT, HUMAN, AI, SYSTEM).
5. **API changes:** Webhook endpoints for Android SMS Gateway and WhatsApp.
6. **Frontend changes:** Unified Inbox/Communication UI handling multiple channels.
7. **Security implications:** Ensure Mock providers are active; no real SMS/WhatsApp during development.
8. **Tests required:** Adapter interface tests, Webhook payload parsing tests.
9. **Dependencies on other phases:** None.
10. **Definition of PASS:** Communication flows through the abstraction layer. Adapters correctly mock external APIs (PENDING_EXTERNAL where applicable).
11. **Rollback/checkpoint strategy:** Keep Twilio endpoints active as fallback until abstraction is stable.

---

## PHASE 4: Customer 360 & Mobile First Navigation
**Goal:** Overhaul the UI for Mobile-First experience and unified Customer 360 view.

1. **Existing functionality being reused:** React components, Client details, Tailwind styling.
2. **New functionality required:** Bottom Navigation for mobile, Unified Customer 360 Dashboard.
3. **Files/modules likely affected:** `frontend/src/components/Layout.jsx`, `frontend/src/pages/ClientsPage.jsx`, `frontend/src/App.css`.
4. **Database/model changes:** None.
5. **API changes:** Aggregate endpoint for Customer 360 (Timeline + Summary).
6. **Frontend changes:** Implement Bottom Nav (Home, Leads, +, Agenda, AI), transform tables to cards on mobile.
7. **Security implications:** Ensure aggregated data respects RBAC.
8. **Tests required:** Mobile responsive tests, Customer 360 aggregation tests.
9. **Dependencies on other phases:** Phase 3 (Unified communications).
10. **Definition of PASS:** UI is usable with one hand on mobile, Customer 360 displays all touchpoints.
11. **Rollback/checkpoint strategy:** Git checkout previous Layout and Page components.

---

## PHASE 5: Automation & AI
**Goal:** Implement Appointment Guardian, Lost Lead Recovery, Vehicle Matching, and Website AI Chat architectures.

1. **Existing functionality being reused:** Appointments model, Scheduler (`apscheduler`).
2. **New functionality required:** Appointment Guardian logic, Stale lead detection, Mock Vehicle Matching engine.
3. **Files/modules likely affected:** `backend/server.py` (Scheduler), new AI service modules.
4. **Database/model changes:** Add mock `Inventory` collection.
5. **API changes:** Endpoints for Website Chat widget, Vehicle recommendation endpoints.
6. **Frontend changes:** AI Chat widget placeholder, Lost Lead recovery recommendations on Action Center.
7. **Security implications:** Prevent AI chat from requesting SSN/sensitive data in plain text.
8. **Tests required:** Guardian automation timing tests, Chat safety constraint tests.
9. **Dependencies on other phases:** Phase 2 (Pipeline), Phase 3 (Communications).
10. **Definition of PASS:** Guardian correctly schedules/reminds, AI Chat captures leads securely without real integrations.
11. **Rollback/checkpoint strategy:** Disable specific scheduler jobs.

---

## PHASE 6: Jarvis Integration
**Goal:** Implement Jarvis typed tools and central AI interface.

1. **Existing functionality being reused:** Backend APIs, DB models.
2. **New functionality required:** LLM orchestration, Tool execution layer with RBAC checks, Audit logging for AI actions.
3. **Files/modules likely affected:** `backend/services/jarvis.py` (new).
4. **Database/model changes:** `JarvisAuditLog`.
5. **API changes:** WebSocket or Streaming endpoint for Jarvis interaction.
6. **Frontend changes:** AI interface accessible via Mobile Nav.
7. **Security implications:** Jarvis MUST NEVER write directly to DB. Must use internal APIs with current user's permissions and require confirmation for destructive/mutative actions.
8. **Tests required:** Jarvis tool permission tests, Prompt injection safety tests.
9. **Dependencies on other phases:** Phases 2-5 (Tools rely on new features).
10. **Definition of PASS:** Jarvis can successfully execute `search_client`, `create_appointment`, etc., while respecting user permissions.
11. **Rollback/checkpoint strategy:** Disable Jarvis endpoint.

---

## PHASE 7: Demo Mode & Tour
**Goal:** Create a completely isolated Demo Mode with fictional dataset and guided tour.

1. **Existing functionality being reused:** Frontend UI, Backend routes.
2. **New functionality required:** DEMO Role, DB Middleware for isolation, Seed data generator, Guided Tour component.
3. **Files/modules likely affected:** `backend/auth.py`, `backend/server.py`, `frontend/src/components/DemoTour.jsx` (new).
4. **Database/model changes:** Fictional dataset across all collections mapped to DEMO user.
5. **API changes:** Block real data access if role == DEMO. Reset DEMO data endpoint.
6. **Frontend changes:** DEMO indicator, Tour controls (ES/EN).
7. **Security implications:** CRITICAL. Demo user must absolutely never access real production/staging client data.
8. **Tests required:** Demo isolation tests, Demo Security tests (403/404 assertions on real data).
9. **Dependencies on other phases:** All previous phases.
10. **Definition of PASS:** User logs in as DEMO, takes the tour, sees only fake data, and cannot access real client IDs via direct URL manipulation.
11. **Rollback/checkpoint strategy:** Drop Demo collections, remove Demo role.

---

## PHASE 8: Passkeys & Final Security Audit
**Goal:** Integrate Passkeys/WebAuthn and perform final security hardening.

1. **Existing functionality being reused:** JWT Login.
2. **New functionality required:** WebAuthn registration/login flow, Rate limiting, JWT expiration audit.
3. **Files/modules likely affected:** `backend/auth.py`, `frontend/src/pages/LoginPage.jsx`.
4. **Database/model changes:** Add `WebAuthnCredentials` to User model.
5. **API changes:** WebAuthn challenge and verification endpoints.
6. **Frontend changes:** Biometric login prompt.
7. **Security implications:** Enhances security. No biometrics stored on server.
8. **Tests required:** WebAuthn flow tests, API Security tests (Rate limits, CORS).
9. **Dependencies on other phases:** None directly.
10. **Definition of PASS:** User can register device and login via Face ID / Windows Hello.
11. **Rollback/checkpoint strategy:** Fallback to standard password login.

---

## NEXT STEPS
- **Recommended Implementation Phases:** 8 Phases.
- **First Implementation Phase:** PHASE 1: Security, Roles & Infrastructure Foundation.