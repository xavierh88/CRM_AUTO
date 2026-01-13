# CARPLUS AUTOSALE CRM - Product Requirements Document

## Overview
CRM completo para concesionarios de autos en español con gestión de clientes, oportunidades de venta, citas, SMS automatizados y notificaciones por email.

## Core Features (Implemented)

### Authentication & Access Control
- ✅ JWT-based authentication
- ✅ Roles: Admin y Vendedor (Salesperson)
- ✅ Admin approval for new accounts
- ✅ Admin-only features properly restricted

### Client Management
- ✅ Centralized client list with search/filter
- ✅ Import functionality with duplicate handling
- ✅ Progress bar with instant updates
- ✅ Sold status indicators (star/car icons)
- ✅ Date of Birth field
- ✅ Time at Address (years/months) - FIXED mapping from Pre-Qualify
- ✅ Housing Type (Dueño/Renta/Vivo con familiares)
- ✅ Rent Amount (conditional)
- ✅ UI modals fixed - no more overlay issues
- ✅ **ID Type field** (Licencia de Conducir, Pasaporte, etc.) - Admin only
- ✅ **ID Number field** - Admin only
- ✅ **SSN/ITIN fields** - Admin only

### User Records (Oportunidades)
- ✅ Nested sales opportunities per client
- ✅ Conditional form with detailed fields
- ✅ Employment section with time at employment (years/months)
- ✅ Income Frequency and Net Income Amount
- ✅ Commission fields (Admin-only)
- ✅ **ID Type field now properly mapped from Pre-Qualify**

### Pre-Qualify Module
- ✅ Public form for lead capture
- ✅ Admin-only review page (/prequalify)
- ✅ Multiple file upload support (combines into single PDF)
- ✅ Automatic document transfer when converting to client
- ✅ **Time fields separated (years/months) - FIXED**
- ✅ **Notes include formatted time strings (e.g., "2 años, 6 meses")**
- ✅ Email notifications to ALL admins on new submission
- ✅ **In-app notifications for new submissions (Admin only)**
- ✅ **ID Type mapping from website to CRM** (DL→Licencia, Passport→Pasaporte, etc.)

### Backup & Restore (Admin Only)
- ✅ Download complete database backup as JSON
- ✅ Restore database from backup file
- ✅ Delete all data option (with confirmation)
- ✅ Reset ID Type options

### Communications
- ✅ Twilio SMS integration (pending A2P approval)
- ✅ Two-way SMS inbox
- ✅ SMTP Email notifications (Gmail)

### Notifications System
- ✅ In-app notifications for admins
- ✅ New Pre-Qualify submissions trigger notifications
- ✅ Click notification to navigate to Pre-Qualify page
- ✅ Mark all as read functionality

## Technical Stack
- **Backend:** FastAPI + MongoDB (motor) + Pydantic
- **Frontend:** React + Shadcn/UI + Tailwind CSS + i18next
- **Auth:** JWT tokens
- **SMS:** Twilio
- **Email:** SMTP (Gmail)
- **PDF Processing:** PyPDF2, Pillow, reportlab

## Deployment
- ✅ Live deployment at crm.carplusautosalesgroup.com (Hostinger VPS)
- ✅ SSL certificate (HTTPS) via Certbot
- ✅ Nginx reverse proxy
- ✅ systemd service management

## Session Work Completed (January 13, 2025)

### Appointment System Issues - VERIFIED & FIXED
- ✅ Appointment form works correctly for vendedor (salesperson) role - NOT blank
- ✅ Dealer dropdown shows all options (verified with 5 dealers)
- ✅ Admin notifications are created when appointments are created
- ✅ `send_appointment_email` endpoint now uses dealer full address (from config_lists)
- ✅ `send_appointment_sms` endpoint already using dealer full address (confirmed)

### New Test Suite Created
- ✅ `/app/tests/test_appointments_and_config.py` - 14 tests for appointments and config lists
- ✅ Tests cover: login, config lists access, appointment CRUD, notifications

### Test Credentials Created
- ✅ Vendedor test account: `test_vendedor@test.com` / `test123`
- ✅ Test client: Juan Perez (+15551234567) with record
- ✅ Downey dealer configured with address: "7444 Florence Ave, Downey, CA 90240"

---

## Session Work Completed (January 11, 2025)

### Pre-Qualify to Client Data Mapping - FIXED
- ✅ Backend endpoint `/prequalify/submit-with-file` now accepts separated time fields
- ✅ Create client endpoint maps these fields correctly to client and record
- ✅ Notes contain formatted time strings

### UI Modal Layout Issues - FIXED
- ✅ "Add Client" modal uses responsive grid
- ✅ "Client Info" modal fixed with proper spacing
- ✅ No more element overlap issues

### Backend Refactoring - IN PROGRESS
- ✅ Created `/app/backend/config.py` - Configuration and DB connection
- ✅ Created `/app/backend/auth.py` - Authentication utilities
- ✅ Created `/app/backend/models/` - Pydantic models separated by entity:
  - `user.py`, `client.py`, `record.py`, `appointment.py`, `cosigner.py`, `config_list.py`, `prequalify.py`
- ✅ Created `/app/backend/services/` - Reusable services:
  - `email.py`, `sms.py`, `pdf.py`
- Note: `server.py` still contains all routes (4900+ lines) - can be gradually migrated

### Frontend Refactoring - DOCUMENTED
- ✅ Created `/app/frontend/src/components/clients/` folder structure
- Note: `ClientsPage.jsx` (4097 lines) contains internal components that can be extracted gradually

### Website Package - COMPLETED
- ✅ Created `/app/carplus-website-con-prequalify.zip` containing:
  - Original website files (without Emergent branding)
  - `prequalify.html` - Updated form with separated time fields
  - `README.md` - Installation instructions in Spanish

## File Locations

### Backend Refactored Structure
```
/app/backend/
├── server.py           # Main entry point (routes still here)
├── config.py           # NEW: Configuration & DB
├── auth.py             # NEW: Auth utilities
├── models/
│   ├── __init__.py     # Exports all models
│   ├── user.py
│   ├── client.py
│   ├── record.py
│   ├── appointment.py
│   ├── cosigner.py
│   ├── config_list.py
│   └── prequalify.py
└── services/
    ├── __init__.py
    ├── email.py
    ├── sms.py
    └── pdf.py
```

### Downloadable Packages
- `/app/carplus-website-con-prequalify.zip` - Website with pre-qualify form
- `/app/carplus-prequalify-form-updated.zip` - Standalone pre-qualify form

## Pending/Future Tasks

### P3 - Technical Debt (Continue when needed)
- [ ] Migrate routes from server.py to /routes/ modules
- [ ] Extract components from ClientsPage.jsx to /components/clients/

### P4 - Enhancements
- [ ] Co-signer comments/notes section
- [ ] Dashboard export to Excel/PDF
- [ ] Advanced analytics dashboard

## Credentials
- **Admin:** admin@carplus.com / Cali2020
- **Live URL:** https://crm.carplusautosalesgroup.com

## Test Files
- `/app/tests/test_prequalify_and_clients.py` - Comprehensive test suite

## Last Updated
January 11, 2025 - Refactoring backend structure, created website package with pre-qualify form
