# CARPLUS AUTOSALE CRM - Product Requirements Document

## Objetivo Principal
CRM completo para concesionario de autos con funcionalidades de gestión de clientes, precalificaciones, citas, documentos, y comunicación (SMS/Email).

## Roles del Sistema
- **Admin**: Acceso completo a todas las funcionalidades
- **BDC Manager**: Gestión de telemarketers y estadísticas de equipo
- **Telemarketer**: Gestión de clientes propios

## Funcionalidades Implementadas

### Autenticación
- Login/registro de usuarios
- Roles y permisos
- JWT-based auth

### Dashboard (Actualizado 2026-07-30)
- Estadísticas generales del CRM
- **NUEVO**: Estadísticas clickeables - al hacer click muestran lista detallada de datos
- Filtros por período/mes
- Gráficos de performance

### Gestión de Clientes
- CRUD completo de clientes
- Búsqueda y filtrado
- Indicadores de color por estado
- Sistema de documentos (ID, Income, Residence)
- Co-signers
- Notas/comentarios con recordatorios
- **NUEVO**: Botón de exportar a Excel (Nombre, Apellido, Email, Teléfono) - Solo Admin
- **NUEVO**: Botón de información de precalificación - Muestra modal con datos de precalificación vinculada

### Precalificaciones
- Formulario público en /prequalify-FINAL.html
- Matching automático con clientes existentes
- Sincronización de datos a cliente
- Creación de cliente desde precalificación
- **NUEVO**: Campo Employer Phone Number guardado correctamente
- **NUEVO**: Botón de eliminar con confirmación - elimina datos y documentos físicos
- **NUEVO**: Optimización automática de documentos al subir (resize imágenes, conversión a JPEG optimizado)

### Citas y Agenda
- Agendamiento de citas con dealers
- Estados de cita (agendado, cumplido, no show, etc.)
- Recordatorios por SMS/Email
- Vista de agenda calendario

### Comunicación
- SMS vía Twilio (pendiente aprobación A2P 10DLC)
- Email de reportes con adjuntos
- Notificaciones in-app

### Documentos
- Subida de documentos de identidad, ingresos, residencia
- Sistema dual: campos legacy + arrays nuevos
- Descarga de documentos
- Combinación de múltiples archivos en PDF

## Arquitectura Técnica

### Backend
- FastAPI (Python)
- MongoDB (Motor async)
- JWT Authentication
- APScheduler para tareas programadas

### Frontend
- React 18
- Tailwind CSS
- Shadcn/UI components
- i18n (español/inglés)

### Integraciones
- Twilio (SMS)
- SMTP (Email)
- Google Places API (autocompletado de direcciones)

## Endpoints API Nuevos (2026-07-30)

1. `GET /api/clients/{client_id}/prequalify` - Obtener precalificación vinculada a cliente
2. `GET /api/clients/export/excel` - Exportar todos los clientes a Excel
3. `DELETE /api/prequalify/submissions/{submission_id}` - Eliminar precalificación y documentos
4. `GET /api/dashboard/stats/{stat_type}/details` - Obtener detalle de estadística clickeable

## Modelos de Datos Actualizados

### PreQualifySubmission / PreQualifyResponse
- Agregado: `employerPhoneNumber: Optional[str]`

## Credenciales de Prueba
Ver `/app/memory/test_credentials.md`

## Pendientes / Backlog

### Alta Prioridad
- Aprobación campaña Twilio A2P 10DLC (bloqueado externamente)

### Media Prioridad
- Refactorización de server.py en routers modulares
- División de ClientsPage.jsx en componentes más pequeños

### Baja Prioridad
- Migración a object storage para documentos
- Tests E2E automatizados expandidos

## Fecha de Última Actualización
2026-07-30 - Implementación de 7 mejoras solicitadas:
1. Botón info precalificación en clientes
2. Dashboard con estadísticas clickeables
3. Exportar clientes a Excel
4. Corrección campos dirección en precalificación
5. Campo Employer Phone Number
6. Eliminar precalificaciones con confirmación
7. Optimización automática de documentos
