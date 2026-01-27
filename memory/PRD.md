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
- ✅ **ID Type field** - Admin only
- ✅ **ID Number field** - Admin only
- ✅ **SSN/ITIN fields** - Admin only

### Document Management
- ✅ Multi-document upload support (multiple files per type)
- ✅ Document types: ID, Income Proof, Residence Proof
- ✅ Combined PDF download for all documents of a type
- ✅ Individual document download/delete
- ✅ Pre-Qualify to Client document transfer

### Dashboard
- ✅ Role-based statistics (Admin sees all, BDC Manager excludes admin data, Telemarketer sees own)
- ✅ Date period filters (All time, Last 6 months, This month, Specific month)
- ✅ **User filter for Admin** - Can view stats for specific users
- ✅ Sales performance chart by salesperson
- ✅ Appointment status breakdown

### Legal & Compliance Pages
- ✅ **Terms & Conditions** - `/terms`
- ✅ **Privacy Policy** - `/privacy`
- ✅ SMS consent checkbox in pre-qualify form
- ✅ Links to legal pages in footer

### Notifications System
- ✅ In-app notifications
- ✅ Note reminder notifications
- ✅ Appointment reminder notifications

### Communications
- ✅ Twilio SMS integration (pending A2P approval)
- ✅ SMTP Email notifications (Gmail)

## Technical Stack
- **Backend:** FastAPI + MongoDB + Pydantic
- **Frontend:** React + Shadcn/UI + Tailwind CSS + i18next
- **Auth:** JWT tokens
- **SMS:** Twilio (A2P 10DLC pending)
- **Email:** SMTP (Gmail)

---

## Session Work Completed (January 27, 2026)

### Dashboard User Filter - IMPLEMENTED ✅
- Added `user_id` parameter to `/api/dashboard/stats` endpoint
- Admin can filter statistics by specific user
- Test: 16/17 backend tests passed (94%)

### Legal Pages for Twilio A2P Compliance - IMPLEMENTED ✅
- Created `/terms` - Terms & Conditions page
- Created `/privacy` - Privacy Policy page
- Both pages are public (no authentication required)
- Includes SMS consent language required by Twilio/carriers

### Pre-Qualify Form Updated - IMPLEMENTED ✅
- Added SMS consent checkbox with full disclosure text
- Added Terms & Privacy acceptance checkbox
- Added footer links to legal pages
- Added "Message and data rates may apply" disclosure
- Added STOP instruction for opt-out

---

## Pending Issues

### P1 - High Priority  
- [ ] Notification navigation for Telemarketers
- [ ] Admin doesn't see all their own clients in "Mis Clientes" filter

### P2 - Medium Priority
- [ ] Twilio SMS - Update campaign with new compliance URLs

### P3 - Technical Debt
- [ ] Refactor `ClientsPage.jsx` (~4500 lines)
- [ ] Refactor `server.py` (~6800 lines)

---

## Twilio A2P Campaign Update Checklist

To update the campaign for approval:

1. **Campaign Details:**
   - Sample Message 1: `Hola {nombre}, su cita en CARPLUS está confirmada para el {fecha} a las {hora}. Responda STOP para cancelar SMS.`
   - Sample Message 2: `Recordatorio: Mañana tiene cita en CARPLUS AUTOSALE a las {hora}. Tarifas de datos pueden aplicar. STOP para cancelar.`

2. **Message Flow / Opt-In:**
   - Opt-in Type: Website form
   - Opt-in URL: `https://carplusautosalesgroup.com/prequalify.html`
   - Description: `Users provide phone number and check consent box agreeing to receive SMS about appointments, reminders and updates. Message frequency up to 5/week. Rates may apply. Reply STOP to cancel.`

3. **Compliance URLs:**
   - Terms URL: `https://crm.carplusautosalesgroup.com/terms`
   - Privacy URL: `https://crm.carplusautosalesgroup.com/privacy`
   - Opt-out: STOP, UNSUBSCRIBE, CANCEL
   - Help: HELP, INFO

---

## File Locations

### New Files Created
- `/app/frontend/src/pages/TermsPage.jsx` - Terms & Conditions
- `/app/frontend/src/pages/PrivacyPage.jsx` - Privacy Policy

### Updated Files
- `/app/frontend/src/App.js` - Added routes for /terms and /privacy
- `/app/frontend/public/prequalify-FINAL.html` - Added SMS consent
- `/app/backend/server.py` - Added user_id parameter to dashboard stats

---

## Credentials
- **Admin:** xavier.hernandez.1988@gmail.com / Cali2020
- **Live URL:** https://crm.carplusautosalesgroup.com

## Last Updated
January 27, 2026 - Legal pages for Twilio A2P compliance
