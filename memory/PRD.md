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
- ✅ Time at Address (years/months)
- ✅ Housing Type (Dueño/Renta/Vivo con familiares)
- ✅ Rent Amount (conditional)

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
  - Time at Employment (years/months)
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
- ✅ CRM.zip package created for Hostinger deployment
- ✅ README.md with comprehensive setup instructions
- ✅ .env.example files for both backend and frontend
- ✅ Pre-qualify form HTML for website integration

## Pending/Future Tasks

### P2 - Technical Debt (High Priority)
- [ ] Refactor server.py (>4500 lines) into modular structure
- [ ] Refactor ClientsPage.jsx (monolithic component)

### P3 - Enhancements
- [ ] Co-signer comments/notes section
- [ ] Dashboard export to Excel/PDF

### P4 - Nice to Have
- [ ] Advanced analytics dashboard
- [ ] Bulk operations on clients

## Credentials
- **Admin:** admin@carplus.com / Cali2020
- **Salesperson:** vendedor1@test.com / Test1234

## Last Updated
January 11, 2025 - Added multiple file upload for pre-qualify with PDF merging, document transfer to client
