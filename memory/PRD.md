# CARPLUS AUTOSALE CRM - Product Requirements Document

## Overview
CRM completo para concesionarios de autos en español con gestión de clientes, oportunidades de venta, citas, SMS automatizados y notificaciones por email.

## Core Features (Implemented)

### Authentication & Access Control
- ✅ JWT-based authentication
- ✅ Roles: Admin, BDC Manager, Telemarketer
- ✅ Admin approval for new accounts
- ✅ Admin-only features properly restricted

### Client Management
- ✅ Centralized client list with search/filter
- ✅ Import functionality with duplicate handling
- ✅ Progress bar with instant updates
- ✅ Sold status indicators (star/car icons)
- ✅ Date of Birth field
- ✅ Time at Address (years/months)
- ✅ Housing Type (Dueño/Renta/Vivo con familiares)
- ✅ Rent Amount (conditional)
- ✅ **ID Type field** (Licencia de Conducir, Pasaporte, etc.) - Admin only
- ✅ **ID Number field** - Admin only
- ✅ **SSN/ITIN fields** - Admin only

### Document Management
- ✅ Multi-document upload support (multiple files per type)
- ✅ Document types: ID, Income Proof, Residence Proof
- ✅ Combined PDF download for all documents of a type
- ✅ Individual document download/delete
- ✅ Pre-Qualify to Client document transfer

### User Records (Oportunidades)
- ✅ Nested sales opportunities per client
- ✅ Conditional form with detailed fields
- ✅ Employment section with time at employment (years/months)
- ✅ Income Frequency and Net Income Amount
- ✅ Commission fields (Admin-only)
- ✅ Record completion status tracking

### Pre-Qualify Module
- ✅ Public form for lead capture
- ✅ Admin-only review page (/prequalify)
- ✅ Multiple file upload support (combines into single PDF)
- ✅ Automatic document transfer when converting to client
- ✅ Email notifications to ALL admins on new submission
- ✅ **In-app notifications for new submissions (Admin only)**
- ✅ **ID Type mapping from website to CRM**

### Dashboard
- ✅ Role-based statistics (Admin sees all, BDC Manager excludes admin data, Telemarketer sees own)
- ✅ Date period filters (All time, Last 6 months, This month, Specific month)
- ✅ **User filter for Admin** - Can view stats for specific users
- ✅ Sales performance chart by salesperson
- ✅ Appointment status breakdown
- ✅ Finance type breakdown (Financiado/Lease)
- ✅ Monthly sales trend chart

### Notifications System
- ✅ In-app notifications for admins
- ✅ New Pre-Qualify submissions trigger notifications
- ✅ Note reminder notifications (immediate for <24h, scheduled for >24h)
- ✅ Appointment reminder notifications (1 day before)
- ✅ Click notification to navigate to relevant page

### Agenda/Calendar
- ✅ Appointment scheduling
- ✅ Reminders integrated with agenda view
- ✅ Clickable client names in reminders

### Backup & Restore (Admin Only)
- ✅ Download complete database backup as JSON
- ✅ Restore database from backup file
- ✅ Delete all data option (with confirmation)
- ✅ Merge Mode for restore (updates existing + adds new)

### Communications
- ✅ Twilio SMS integration (pending A2P approval)
- ✅ Two-way SMS inbox
- ✅ SMTP Email notifications (Gmail)

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

---

## Session Work Completed (January 27, 2026)

### Dashboard User Filter - IMPLEMENTED ✅
- Added `user_id` parameter to `GET /api/dashboard/stats` endpoint
- Admin can now filter dashboard statistics by specific user
- Dropdown in frontend shows list of telemarketers and BDC managers
- All stats (clients, sales, appointments, etc.) filter based on selected user

### Pre-Qualify Document Transfer - ENHANCED ✅
- Updated `/api/prequalify/submissions/{id}/create-client` endpoint
- Now creates documents in new multi-document system (`id_documents` array)
- Maintains backwards compatibility with legacy `id_file_url` field
- Documents stored in client-specific folder: `/uploads/clients/{client_id}/`

### Test Results
- Backend: 16/17 tests passed (94%)
- Frontend: 100% tests passed
- No white screen issue detected - proper error handling in place

---

## Pending Issues

### P0 - Critical
None currently identified

### P1 - High Priority  
- [ ] Notification navigation for Telemarketers - May not correctly find clients from other users
- [ ] Admin doesn't see all their own clients in "Mis Clientes" filter

### P2 - Medium Priority
- [ ] Twilio SMS - Pending A2P 10DLC campaign approval

### P3 - Technical Debt
- [ ] Refactor `ClientsPage.jsx` (~4500 lines) - Break into smaller components
- [ ] Refactor `server.py` (~6800 lines) - Split into modular routers
- [ ] Delete old admin users from database

### P4 - Enhancements
- [ ] Co-signer comments/notes section
- [ ] Dashboard export to Excel/PDF
- [ ] Advanced analytics dashboard

---

## File Locations

### Backend Structure
```
/app/backend/
├── server.py           # Main entry point (routes still here)
├── config.py           # Configuration & DB
├── auth.py             # Auth utilities
├── models/             # Pydantic models
└── services/           # Email, SMS, PDF services
```

### Frontend Structure
```
/app/frontend/src/
├── pages/              # Page components
│   ├── ClientsPage.jsx # Main clients page (needs refactoring)
│   ├── DashboardPage.jsx # Dashboard with filters
│   └── ...
├── components/
│   └── ui/            # Shadcn UI components
└── context/           # Auth context
```

---

## API Endpoints (Key)

### Dashboard
- `GET /api/dashboard/stats` - Get dashboard statistics
  - Params: `period`, `month`, `user_id` (Admin only)
- `GET /api/dashboard/salesperson-performance` - Get salesperson performance data

### Clients
- `GET /api/clients` - List clients (with owner_filter, search, sort_by)
- `POST /api/clients/{id}/documents/upload` - Upload documents
- `GET /api/clients/{id}/documents/download/{doc_type}` - Download combined PDF

### Pre-Qualify
- `GET /api/prequalify/submissions` - List submissions
- `POST /api/prequalify/submissions/{id}/create-client` - Convert to client

---

## Credentials
- **Admin:** xavier.hernandez.1988@gmail.com / Cali2020
- **Live URL:** https://crm.carplusautosalesgroup.com

## Test Files
- `/app/backend/tests/test_dashboard_role_filtering.py`
- `/app/backend/tests/test_dashboard_user_filter.py`
- `/app/test_reports/iteration_12.json`

## Last Updated
January 27, 2026 - Dashboard user filter for Admin, PreQualify document transfer enhancement
