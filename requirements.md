# DealerCRM Pro - Requirements & Architecture

## Original Problem Statement
CRM para Dealer de Carros - Sistema diseñado para dealers de autos que centraliza información de clientes, permite múltiples vendedores por cliente, automatiza la recolección de documentos y gestión de citas.

## User Choices
- **SMS Provider**: Twilio (mocked for now)
- **Authentication**: JWT
- **Language**: Bilingual (English/Spanish)
- **Theme**: Light modern

## Architecture

### Backend (FastAPI + MongoDB)
- **Auth**: JWT authentication with bcrypt password hashing
- **Collections**: users, clients, user_records, appointments, cosigner_relations, sms_logs
- **API Routes**: All prefixed with `/api`

### Frontend (React + Shadcn UI)
- **State Management**: React Context (AuthContext)
- **Routing**: React Router
- **i18n**: i18next for bilingual support
- **Charts**: Recharts for dashboard visualizations

## Implemented Features

### Core Features ✅
1. **Authentication** - JWT login/register with role-based access (admin/salesperson)
2. **Client Management** - CRUD operations, search, document status tracking
3. **User Records (Cartillas)** - Checklist (DL, Checks, SSN, ITIN), vehicle info, sale tracking
4. **Appointments** - Color-coded statuses (Green=scheduled, Orange=not configured, Blue=time changed, Red=3 weeks, White=no-show, Yellow=completed)
5. **Co-Signers** - Link existing clients as co-signers
6. **Dashboard** - Stats cards, appointment pie chart, performance bar chart (admin)
7. **Agenda** - Calendar view with grouped appointments (Today, Tomorrow, Next 7 Days)
8. **Admin Panel** - User management, trash/recycle bin
9. **Bilingual Interface** - Toggle between English and Spanish
10. **SMS Integration** - Mocked endpoints for documents and appointment links

### Appointment Status Colors
- 🟢 Verde (agendado) - Scheduled
- 🟠 Naranja (sin_configurar) - Not Configured
- 🔵 Azul (cambio_hora) - Time Changed
- 🔴 Rojo (tres_semanas) - 3 Weeks No Response
- ⚪ Blanco (no_show) - No Show
- 🟡 Amarillo (cumplido) - Completed

## Next Action Items

### Phase 2 - SMS Integration
1. Configure real Twilio credentials in backend/.env:
   ```
   TWILIO_ACCOUNT_SID=your_sid
   TWILIO_AUTH_TOKEN=your_token
   TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
   ```
2. Implement actual SMS sending instead of mocked responses
3. Set up automated reminder cron jobs (2h before client, 1h before salesperson)

### Phase 3 - External Forms
1. Create public appointment booking form (client-facing)
2. Create document upload form (client-facing)
3. Implement "Shine Time" (delay reporting) functionality

### Phase 4 - Automation
1. Weekly reminder SMS for unconfigured appointments (3 weeks cycle)
2. Auto no-show detection and re-engagement flow
3. 24-hour delay before sending new link after no-show

### Phase 5 - Enhancements
1. Email notifications (optional)
2. Export reports (PDF/Excel)
3. Client notes/comments system
4. Activity timeline per client

## Tech Stack
- Backend: FastAPI, MongoDB (Motor), PyJWT, bcrypt, Twilio SDK
- Frontend: React 19, React Router, Shadcn/UI, Tailwind CSS, Recharts, i18next
- Fonts: Outfit (headings), Plus Jakarta Sans (body)
