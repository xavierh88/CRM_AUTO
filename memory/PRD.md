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

## Session Work Completed (January 14, 2025)

### Admin Email Updated
- ✅ Main admin email changed to: `xavier.hernandez.1988@gmail.com`
- ✅ Password remains: `Cali2020`
- ✅ Added endpoint `PUT /api/users/{user_id}/email` for admin to update user emails

### Backup System Enhanced
- ✅ Backup includes 19 collections with all data
- ✅ Dealers include addresses in backup
- ✅ Added **Merge Mode** for restore:
  - **Combinar (Merge)**: Updates existing records and adds new ones without deleting current data
  - **Reemplazar (Replace)**: Deletes all data and replaces with backup (old behavior)
- ✅ UI updated with radio buttons to select restore mode

### Default Config Data Updated
- ✅ Default dealers now include addresses:
  - Downey: 7444 Florence Ave, Downey, CA 90240
  - Fullerton: 1100 S Harbor Blvd, Fullerton, CA 92832
  - Hollywood: 6200 Hollywood Blvd, Los Angeles, CA 90028
  - Long Beach: 1500 E Anaheim St, Long Beach, CA 90813

### New Role System Implemented
- ✅ Renamed "Salesperson" role to "Telemarketer"
- ✅ Created new "BDC Manager" role with permissions:
  - Can view all clients (like Admin)
  - Can access "Vendedores" (performance metrics) page
  - Can view and manage "Solicitudes" (client transfer requests)
  - Can create and edit clients of any Telemarketer
  - Cannot access Admin configuration (Banks, Dealers, etc.)
  - Cannot create/delete users

### New "Sold" Page Created
- ✅ New menu item "Sold" showing clients with completed sales
- ✅ Telemarketer: Only sees their own sold clients
- ✅ BDC Manager / Admin: Sees all sold clients with filter by Telemarketer
- ✅ Clients automatically move to "Sold" when record_status = "completed"
- ✅ Main Clients page now excludes sold clients (exclude_sold parameter)

### Menu Reorganization
- ✅ Added "Sold" item after "Clients"
- ✅ Moved "Import" below "Pre-Qualify"
- ✅ "Solicitudes" now only visible to Admin and BDC Manager
- ✅ "Vendedores" visible to Admin and BDC Manager

### Appointment Location Fix
- ✅ Public appointment page now shows full dealer address instead of just name
- ✅ Backend endpoint `/api/public/appointment/{token}` returns `dealer_address` field

### Logo Updated Across CRM
- ✅ Updated logo from: `/logo.png` to: `https://carplusautosalesgroup.com/img/carplus.png`
- ✅ Logo updated in:
  - Login page (`/app/frontend/src/pages/LoginPage.jsx`)
  - Sidebar (`/app/frontend/src/components/Layout.jsx`)
  - Public appointment page (`/app/frontend/src/pages/PublicAppointmentPage.jsx`)
  - Public documents page (`/app/frontend/src/pages/PublicDocumentsPage.jsx`)
  - Pre-qualify form (`/app/frontend/public/prequalify-FINAL.html`)
  - All email templates in backend (appointment, documents, collaboration, pre-qualify notifications)
- ✅ Company branding constants added to backend:
  - `COMPANY_LOGO_URL = "https://carplusautosalesgroup.com/img/carplus.png"`
  - `COMPANY_NAME = "CARPLUS AUTOSALE"`
  - `COMPANY_TAGLINE = "Friendly Brokerage"`

### Appointment System Issues - VERIFIED & FIXED
- ✅ Appointment form works correctly for vendedor (salesperson) role - NOT blank
- ✅ Dealer dropdown shows all options (verified with 5 dealers)
- ✅ Admin notifications are created when appointments are created
- ✅ `send_appointment_email` endpoint now uses dealer full address (from config_lists)
- ✅ `send_appointment_sms` endpoint already using dealer full address (confirmed)

### Dealer Addresses Configured
- ✅ Downey: 7444 Florence Ave, Downey, CA 90240
- ✅ Fullerton: 1100 S Harbor Blvd, Fullerton, CA 92832
- ✅ Hollywood: 6200 Hollywood Blvd, Los Angeles, CA 90028
- ✅ Long Beach: 1500 E Anaheim St, Long Beach, CA 90813

### Backup System - EXPANDED
- ✅ Backup now includes ALL 19 collections (previously only 8):
  - users, clients, user_records, cosigner_records, cosigner_relations
  - appointments, prequalify_submissions, config_lists, record_comments
  - client_comments, client_requests, notifications, sms_logs, email_logs
  - sms_templates, sms_conversations, imported_contacts, public_links, collaboration_requests
- ✅ Restore function updated to support all collections
- ✅ Delete-all-data function updated to clear all collections

### Pre-Qualify to Client Conversion - VERIFIED
- ✅ Admin can convert pre-qualify submission to client
- ✅ Client is assigned to the admin who converts it (`salesperson_id = admin_id`)
- ✅ Record is created with employment data from pre-qualify
- ✅ Notes are created with `admin_only=True` flag (only admins can see pre-qualify data)
- ✅ Submission status changes to `converted` with `matched_client_id`

### New Test Suites Created
- ✅ `/app/tests/test_appointments_and_config.py` - 14 tests for appointments and config lists
- ✅ `/app/tests/test_backup_and_prequalify_conversion.py` - 14 tests for backup and pre-qualify conversion

### Test Credentials Created
- ✅ Vendedor test account: `test_vendedor@test.com` / `test123`
- ✅ Test client: Juan Perez (+15551234567) with record

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
- `/app/tests/test_prequalify_and_clients.py` - Pre-qualify and client tests
- `/app/tests/test_appointments_and_config.py` - Appointments and config lists tests (14 tests)
- `/app/tests/test_backup_and_prequalify_conversion.py` - Backup and pre-qualify conversion tests (14 tests)

## Last Updated
January 13, 2025 - Expanded backup to include all collections, configured dealer addresses, verified pre-qualify to client conversion flow
