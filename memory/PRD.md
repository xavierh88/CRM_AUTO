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
- **Estadísticas clickeables** - al hacer click muestran lista detallada de datos
- Filtros por período/mes
- Gráficos de performance

### Gestión de Clientes
- CRUD completo de clientes
- Búsqueda y filtrado
- Indicadores de color por estado
- Sistema de documentos (ID, Income, Residence)
- Co-signers
- Notas/comentarios con recordatorios
- **Botón de exportar a Excel** (Nombre, Apellido, Email, Teléfono) - Solo Admin
- **Botón de información de precalificación** - Muestra modal con datos de precalificación vinculada
- **Responsive mejorado** para móviles

### Precalificaciones (Actualizado 2026-07-30)
- Formulario público en /prequalify-FINAL.html
- Matching automático con clientes existentes
- Sincronización de datos a cliente
- Creación de cliente desde precalificación
- **NUEVO: Múltiples empleos (hasta 4)** - Botón "+ Agregar otro empleo"
- Campo Employer Phone Number guardado correctamente
- Botón de eliminar con confirmación - elimina datos y documentos físicos
- Optimización automática de documentos al subir

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

## Actualizaciones Recientes

### Bug Fix: Creación de Usuarios por Admins (2026-09-05)
- **Problema**: Los administradores no podían crear usuarios directamente, solo podían esperar que se registraran públicamente
- **Solución**: 
  - Nuevo endpoint `POST /api/users/create` para que admins creen usuarios directamente
  - Formulario en AdminPage.jsx con campos: nombre, email, contraseña, teléfono, rol, estado activo
  - El usuario creado puede tener cualquier rol (telemarketer, bdc_manager, admin)
  - Opción de crear usuario ya activo (sin necesidad de activación posterior)
- **Archivos modificados**: 
  - `/app/backend/server.py` (nuevo endpoint y modelo AdminUserCreate)
  - `/app/frontend/src/pages/AdminPage.jsx` (botón y formulario)
- **Estado**: ✅ Verificado por testing

### Bug Fix: Transferencia de Empleos a Clientes (2026-08-03)
- **Problema**: El segundo empleo ingresado en precalificación no se visualizaba en CRM, y al crear/sincronizar cliente los empleos no se transferían
- **Solución**: 
  - Endpoint `create-client` ahora copia el array `employments` completo al cliente
  - Endpoint `sync-to-client` ahora sincroniza el array `employments` al cliente existente
  - Se mantienen campos legacy (employer_name, income_type, etc.) para compatibilidad
- **Archivos modificados**: `/app/backend/server.py` (líneas 7319-7385, 7644-7680)
- **Tests**: `/app/backend/tests/test_multiple_employments.py` (4 tests backend + validación UI)
- **Estado**: ✅ Verificado por testing agent (100% backend, 100% frontend)

### Múltiples Empleos (2026-07-30)
- **Modelo de datos**: Nuevo modelo `Employment` y array `employments` en PreQualifySubmission
- **Backend**: Endpoint `/api/prequalify/submit-with-file` actualizado para recibir hasta 4 empleos
- **Frontend CRM**: PreQualifyPage.jsx y ClientsPage.jsx actualizados para mostrar múltiples empleos
- **Formulario público**: prequalify-FINAL.html con botón "+ Agregar otro empleo"
- Compatible con datos existentes (legacy single employment)

### Responsive Móvil
- Botones de acción con tamaños adaptativos (h-8 en móvil, h-10 en desktop)
- Texto de botón "Excel" en móvil, "Exportar Excel" en desktop
- Contenedores flex con wrap para mejor visualización

## Archivos Modificados

### Backend
- `/app/backend/server.py`:
  - Modelo `Employment` agregado
  - Modelos `PreQualifySubmission`, `PreQualifyResponse`, `ClientResponse` actualizados con array `employments`
  - Endpoint `submit-with-file` actualizado con parámetros para Employment 2, 3, 4
  - Endpoint `create-client` transfiere array employments al cliente
  - Endpoint `sync-to-client` sincroniza array employments al cliente existente
  - Construcción de array de empleos al guardar

### Frontend
- `/app/frontend/src/pages/PreQualifyPage.jsx`: Vista de múltiples empleos en detalle
- `/app/frontend/src/pages/ClientsPage.jsx`: Modal de prequalify con empleos múltiples, responsive
- `/app/frontend/public/prequalify-FINAL.html`: Formulario con múltiples empleos

## Credenciales de Prueba
Ver `/app/memory/test_credentials.md`

## Pendientes / Backlog

### Alta Prioridad
- Aprobación campaña Twilio A2P 10DLC (bloqueado externamente)

### Media Prioridad
- Refactorización de server.py en routers modulares
- División de ClientsPage.jsx en componentes más pequeños
- Validación de flujo completo en producción VPS

### Baja Prioridad
- Migración a object storage para documentos
- Tests E2E automatizados expandidos

## Fecha de Última Actualización
2026-08-03
