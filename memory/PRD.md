# CARPLUS AUTOSALE CRM - Product Requirements Document

## Overview
CRM completo para concesionarios de autos en español con gestión de clientes, oportunidades de venta, citas, SMS automatizados y notificaciones por email.

## Core Features (Implemented)

### Authentication & Access Control
- ✅ JWT-based authentication
- ✅ Roles: Admin, BDC Manager, Telemarketer
- ✅ Admin approval for new accounts

### Client Management
- ✅ Centralized client list with search/filter
- ✅ Sold clients visible when searching from Agenda/Notifications
- ✅ Document upload and download support

### Dashboard
- ✅ Role-based statistics
- ✅ User filter for Admin (by role or individual)
- ✅ Date period filters

### Legal & Compliance Pages
- ✅ Terms & Conditions - `/terms`
- ✅ Privacy Policy - `/privacy`
- ✅ SMS consent in pre-qualify form

### Communications
- ✅ Twilio SMS integration (A2P campaign submitted)
- ✅ SMTP Email notifications

---

## Session Work Completed (January 27-28, 2026)

### Dashboard User Filter - IMPLEMENTED ✅
- Filters: Todos, Todos Administradores, Todos BDC Managers, Todos Telemarketers
- Individual users grouped by role

### Legal Pages for Twilio A2P - IMPLEMENTED ✅
- `/terms` - Terms & Conditions
- `/privacy` - Privacy Policy
- SMS consent checkbox in pre-qualify form

### Bug Fixes - IMPLEMENTED ✅
1. **Client David Ortega invisible** - Was assigned to deleted user, reassigned to David Arellano
2. **Sold clients not found from Agenda** - Fixed: exclude_sold=false when from_notification
3. **Document download with absolute paths** - Added support for `/var/www/...` paths
4. **Agenda links** - Now include `from_agenda=true` parameter

---

## Pending Issues

### P1 - High Priority  
- [ ] Verify document download works in production
- [ ] Test Agenda to Client navigation for sold clients

### P2 - Medium Priority
- [ ] Twilio A2P campaign approval (submitted, waiting)

### P3 - Technical Debt
- [ ] Refactor `ClientsPage.jsx`
- [ ] Refactor `server.py`

---

## Files Modified This Session
- `/app/frontend/src/pages/DashboardPage.jsx` - User filter dropdown
- `/app/frontend/src/pages/ClientsPage.jsx` - Sold clients in search
- `/app/frontend/src/pages/AgendaPage.jsx` - Link parameters
- `/app/frontend/src/pages/TermsPage.jsx` - NEW
- `/app/frontend/src/pages/PrivacyPage.jsx` - NEW
- `/app/backend/server.py` - Dashboard filter, document download

---

## Credentials
- **Admin:** xavier.hernandez.1988@gmail.com / Cali2020
- **Production:** https://crm.carplusautosalesgroup.com
- **Database:** carplus_db (MongoDB)

## Last Updated
January 28, 2026
