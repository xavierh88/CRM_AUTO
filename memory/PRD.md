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

### User Records (Oportunidades)
- ✅ Nested sales opportunities per client
- ✅ Conditional form with detailed fields
- ✅ Auto Loan multi-select (Paid/Late/On Time)
- ✅ Car Brands dropdown (fixed)
- ✅ Record status: Completed/No-Show
- ✅ Admin-only Commission fields (locks status)
- ✅ Mark as Completed functionality

### Pre-Qualify Module (NEW)
- ✅ Public form for lead capture
- ✅ Admin-only review page (/prequalify)
- ✅ Client matching by phone number
- ✅ Create client or add to existing notes
- ✅ **Email notifications to ALL admins on new submission** (Implemented Jan 9, 2025)

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

## Deployment
- ✅ CRM.zip package created for Hostinger deployment
- ✅ README.md with comprehensive setup instructions
- ✅ .env.example files for both backend and frontend

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
- **Admin:** xadmin / Cali2020
- **Salesperson:** vendedor1@test.com / Test1234

## Last Updated
January 9, 2025 - Added email notifications for Pre-Qualify submissions
