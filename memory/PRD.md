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

### User Records (Oportunidades)
- ✅ Nested sales opportunities per client
- ✅ Conditional form with detailed fields
- ✅ Auto Loan multi-select (Paid/Late/On Time)
- ✅ Car Brands dropdown (fixed)
- ✅ Record status: Completed/No-Show
- ✅ Admin-only Commission fields (locks status)
- ✅ Mark as Completed functionality
- ✅ Employment section with:
  - Employment Type (Company/Retired/Unemployed/Self employed)
  - Company/Business Name
  - Time at Employment (years/months) - FIXED mapping from Pre-Qualify
  - Income Frequency (Semanal/Cada dos semanas/Dos veces al mes/Mensual)
  - Net Income Amount

### Pre-Qualify Module
- ✅ Public form for lead capture
- ✅ Admin-only review page (/prequalify)
- ✅ Client matching by phone number
- ✅ Create client or add to existing notes
- ✅ Email notifications to ALL admins on new submission
- ✅ **Multiple file upload support** (combines into single PDF)
- ✅ **Document preview in Pre-Qualify panel**
- ✅ **Automatic document transfer when converting to client**
- ✅ **Time fields separated (years/months) - FIXED**
- ✅ **Notes include formatted time strings (e.g., "2 años, 6 meses")**

### Public Document Upload
- ✅ When client already has ID from pre-qualify, shows message:
  "Ya tiene un documento de ID previamente subido. Puede subir uno nuevo si lo desea."

### Co-Signers
- ✅ Link co-signers to client records

### Appointments
- ✅ Internal appointment scheduling
- ✅ Public forms for document uploads
- ✅ Dealer address management (Admin)

### Communications
- ✅ Twilio SMS integration (pending A2P approval)
- ✅ Two-way SMS inbox
- ✅ Automated marketing campaigns
- ✅ SMTP Email notifications (Gmail)
- ✅ Send Report feature (Admin-only)

### Admin Panel
- ✅ User management
- ✅ Dynamic dropdown lists management
- ✅ Dealer address management

### Branding
- ✅ Logo: CARPLUS AUTOSALE
- ✅ Slogan: Friendly Brokerage
- ✅ Light-themed modern UI

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
- ✅ Pre-qualify form HTML for website integration

## Recently Fixed (January 11, 2025)

### Pre-Qualify to Client Data Mapping - FIXED
- ✅ Backend endpoint `/prequalify/submit-with-file` now accepts separated time fields:
  - `timeAtAddressYears`, `timeAtAddressMonths`
  - `timeWithEmployerYears`, `timeWithEmployerMonths`
- ✅ Create client endpoint maps these fields correctly:
  - Client: `time_at_address_years`, `time_at_address_months`
  - Record: `employment_time_years`, `employment_time_months`
- ✅ Notes contain formatted time strings (e.g., "3 años, 4 meses")

### UI Modal Layout Issues - FIXED
- ✅ "Add Client" modal now uses responsive grid (1 col mobile, 2 cols desktop)
- ✅ "Client Info" modal fixed with proper spacing
- ✅ No more element overlap issues
- ✅ Scrollable content with max-height

### Direct Client Creation - FIXED
- ✅ `/api/clients` POST endpoint now saves all new fields:
  - `date_of_birth`, `time_at_address_years`, `time_at_address_months`
  - `housing_type`, `rent_amount`

## Pending/Future Tasks

### P2 - Technical Debt (High Priority)
- [ ] Refactor server.py (>4500 lines) into modular structure
- [ ] Refactor ClientsPage.jsx (monolithic component)

### P2 - Website Integration
- [ ] Create integrated website package with pre-qualify form matching site design

### P3 - Enhancements
- [ ] Co-signer comments/notes section
- [ ] Dashboard export to Excel/PDF

### P4 - Nice to Have
- [ ] Advanced analytics dashboard
- [ ] Bulk operations on clients

## Credentials
- **Admin:** admin@carplus.com / Cali2020
- **Salesperson:** vendedor1@test.com / Test1234

## Test Files
- `/app/tests/test_prequalify_and_clients.py` - Comprehensive test suite for pre-qualify and client functionality

## Last Updated
January 11, 2025 - Fixed Pre-Qualify data mapping with separated time fields, UI modal layouts, and direct client creation endpoint
