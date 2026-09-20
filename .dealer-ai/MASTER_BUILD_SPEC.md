# DEALER AI OS V2 - MASTER BUILD SPEC

## 1. OBJETIVO GENERAL

Transformar el CRM existente en Dealer AI OS V2:
un sistema web profesional para dealers, mobile-first, asistido por IA, con CRM, seguimiento, citas, comunicaciones, prequalify, ventas, finanzas, automatizacion controlada, Jarvis y capacidad de demostracion comercial.

La V2 debe conservar las funciones utiles existentes y mejorar arquitectura, seguridad, UX, automatizacion y capacidad comercial.

---

# 2. ARQUITECTURA BASE

Frontend:
- React
- responsive
- mobile-first
- ES/EN

Backend:
- FastAPI
- APIs modulares
- validacion estricta
- RBAC

Database:
- MongoDB de staging/desarrollo separado
- prohibido usar produccion durante desarrollo

---

# 3. HOME / ACTION CENTER

Home debe priorizar acciones y no ser solo un dashboard estadistico.

Mostrar:
- citas de hoy
- citas sin confirmar
- nuevos leads
- leads sin seguimiento
- leads >48h sin contacto
- prequalifications nuevas
- documentos incompletos
- mensajes pendientes
- no-shows
- deals cerca de cierre

Quick actions:
- Call
- SMS
- Open Customer
- Confirm Appointment
- Create Appointment
- Assign
- Follow Up

---

# 4. MOBILE EXPERIENCE

En telefono usar navegacion inferior:

Home
Leads
+
Agenda
AI

Evitar copiar el sidebar de desktop al telefono.

Optimizar:
- botones tactiles
- formularios
- tablas transformadas a cards
- Customer 360
- agenda
- acciones rapidas
- busqueda

---

# 5. LOGIN Y PASSKEYS

Mantener login normal.

Agregar arquitectura para Passkeys/WebAuthn:
- Face ID
- Touch ID
- Windows Hello
- Android biometrics/PIN

El sistema no almacena biometria.

Debe existir fallback por password.

---

# 6. CUSTOMER 360

Cada cliente debe tener una vista unificada.

Mostrar:
- informacion basica
- lead source
- status
- vehiculo de interes
- citas
- prequalify
- documentos
- mensajes
- llamadas
- notas
- cambios
- historial completo
- timeline
- resumen IA

---

# 7. PIPELINE COMERCIAL

Soportar estados equivalentes a:

NEW LEAD
CONTACTED
ENGAGED
PREQUALIFY
APPLIED
APPROVED
CONDITIONAL
DECLINED
APPOINTMENT
SHOW
NEGOTIATING
PENDING DEAL
STOP/HOLD
SOLD
LOST

No reemplazar a ciegas estados existentes.
Crear capa de mapeo/migracion compatible.

---

# 8. APPOINTMENT GUARDIAN

Automatizar control de citas:

- crear
- confirmar
- recordar
- cambio de hora
- running late
- cancelar
- reprogramar
- no-show
- recovery

Mantener intervencion humana cuando corresponda.

---

# 9. COMMUNICATION HUB

Crear abstraction layer de comunicaciones.

Providers:
- mock provider
- Android SMS Gateway adapter
- futuro WhatsApp adapter
- futuro email provider

Cada mensaje debe guardar:
- customer_id
- channel
- direction
- actor
- text
- timestamp
- delivery status
- provider_message_id

Actores:
CLIENT
HUMAN
AI
SYSTEM

---

# 10. SMS ANDROID GATEWAY

Preparar adapter para telefono Android fisico.

Dashboard de salud:

SMS Gateway Online
SMS Gateway Offline
SMS Gateway Degraded

Guardar:
- heartbeat
- last_seen
- last_error
- provider status

Inbound:
cliente -> telefono -> gateway -> webhook -> CRM

Outbound:
CRM -> communication service -> gateway -> telefono -> cliente

No enviar SMS reales durante desarrollo.

---

# 11. WHATSAPP AI TAKEOVER

Preparar arquitectura.

Flujo:
cliente escribe
-> ventana para humano
-> si humano responde, IA no interviene
-> si no responde, IA puede continuar
-> si humano entra, IA cede

Estado inicial:
WAITING_CONFIG

No asumir API disponible.

---

# 12. JARVIS

Jarvis sera interfaz central para consultar y operar.

Ejemplos de tools:

search_client
get_client_history
create_client
update_client
create_appointment
update_appointment
send_sms
get_sales_report
get_prequalification
assign_lead
get_inventory
match_vehicle
get_financial_summary

Jarvis:
- no acceso DB directo
- permisos
- confirmaciones
- audit log
- validaciones
- errores explicables

---

# 13. USER MODE / ADMIN MODE / DEVELOPER MODE

USER MODE:
acciones CRM autorizadas.

ADMIN MODE:
usuarios, asignaciones, operaciones, reportes.

DEVELOPER MODE:
solo SYSTEM_DEVELOPER.

Puede administrar:
- Custom Fields
- Custom Forms
- Custom Menus
- Custom Modules
- Integrations
- Webhooks
- AI Tools
- Schema Versions

---

# 14. CUSTOM FIELD ENGINE

Crear motor de campos personalizados.

Tipos:
text
long_text
number
phone
email
date
boolean
select
multi_select
money
percentage

Cada campo:
- id
- module
- name
- label
- type
- required
- options
- validation
- created_by
- version
- active

Debe existir SYSTEM_PROTECTED para campos centrales.

---

# 15. CUSTOM MODULE ENGINE

SYSTEM_DEVELOPER puede crear modulos controlados.

Ejemplo:
Trade-Ins

Debe poder definir:
- nombre
- icono
- campos
- permisos
- menu
- formulario
- vista lista
- vista detalle

Nunca permitir codigo arbitrario desde Jarvis.

---

# 16. SCHEMA AUDIT

Registrar cambios estructurales:

who
role
action
module
field
timestamp
old_version
new_version
reason

Agregar Undo/Revert cuando sea seguro.

---

# 17. FINANCIAL PANEL

Agregar modelo financiero profesional.

Por deal/vehiculo:

vehicle_purchase_cost
reconditioning_cost
transport_cost
auction_fees
other_acquisition_cost
total_vehicle_cost
sale_price
contract_amount
down_payment
financed_amount
dealer_reserve
warranty_income
gap_income
other_backend_income
salesperson_commission
bdc_commission
referral_commission
other_expenses
gross_profit
net_profit

KPIs:

units sold
gross sales
contract volume
vehicle cost
front-end gross
back-end gross
gross profit
commissions
other expenses
net profit
avg gross per unit
avg net per unit
days to sale
approval to sale conversion

---

# 18. VEHICLE MATCHING AI

Preparar engine para recomendar vehiculos alternativos segun:

- budget
- down payment
- payment preference
- year
- type
- credit constraints
- inventory

Usar mock inventory hasta integrar inventario real.

---

# 19. LOST LEAD RECOVERY

Detectar:

- stale leads
- no replies
- abandoned prequalify
- no-shows
- leads sin contacto
- leads sin actividad

Clasificar prioridad:
HOT
WARM
COLD

Recomendar acciones.

No enviar mensajes reales automaticamente durante desarrollo.

---

# 20. WEBSITE AI CHAT

Preparar modulo bilingue.

Debe:
- detectar idioma
- preguntar vehiculo
- presupuesto
- down payment
- preferencias
- crear lead
- ofrecer cita
- iniciar prequalify seguro
- evitar pedir SSN en chat libre

---

# 21. ATTRIBUTION

Guardar source:

Facebook
Instagram
Google
Website
AI Chat
Phone
Walk-in
Referral
Existing Client
Manual CRM
Prequalify

Guardar acquisition_type:

AI_ACQUIRED
AI_ASSISTED
HUMAN_ACQUIRED
EXISTING_CUSTOMER

---

# 22. MARKETING AI OS INTEGRATION HUB

Crear API/webhooks preparados para futura plataforma.

Datos permitidos:

customer_id
first_name
preferred_language
authorized phone/email
vehicle_interest
previous_vehicle
lead_source
marketing_consent
last_contact
sales trends
vehicle trends

Nunca exponer:

SSN
ID documents
income documents
bank data
credit documents

---

# 23. PREQUALIFY PROVIDER ADAPTER

Crear interfaz:

PrequalifyProvider

Estado inicial:

PENDING_PROVIDER_INTEGRATION

No hacer scraping ni automatizacion no autorizada del proveedor externo.

---

# 24. DEMO MODE

Crear rol/contexto DEMO.

Debe estar separado logicamente y en backend de datos reales.

Dataset ficticio:

- customers
- leads
- appointments
- vehicles
- conversations
- prequalifications
- sales
- commissions
- tasks
- reports

Debe verse realista pero ser ficticio.

---

# 25. DEMO TOUR

Tour guiado:

Spanish
English

Pasos sugeridos:

1. Welcome
2. Action Center
3. Leads
4. Customer 360
5. Agenda
6. Messages
7. Prequalify
8. Sales
9. Financial Panel
10. Jarvis
11. Finish

Controles:

Next
Previous
Skip
Restart Tour

Mostrar indicador:

DEMO - Fictional Data

Agregar Reset Demo.

---

# 26. DEMO SECURITY TESTS

Probar que DEMO:

- no ve clientes reales
- no puede consultar IDs reales
- no puede abrir documentos reales
- no puede acceder por URL manual
- no puede llamar APIs reales
- no puede enviar SMS reales

Backend debe responder 403/404 segun corresponda.

---

# 27. PASSKEY / SECURITY

Auditar:

- JWT
- expiration
- RBAC
- server-side permissions
- CORS
- uploads
- public tokens
- log redaction
- rate limiting
- sensitive field masking
- file access
- SSN exposure

---

# 28. DOCUMENT SECURITY

No versionar uploads reales.

Agregar protecciones .gitignore.

Preparar migracion futura a almacenamiento privado.

No eliminar documentos reales de produccion durante V2 development.

---

# 29. TESTING

Ejecutar:

backend tests
frontend tests
build
API tests
RBAC tests
Demo isolation tests
Jarvis tool tests
financial calculation tests
mobile responsive tests
SMS adapter tests
security smoke tests

---

# 30. DEFINITION OF DONE

Una funcion solo es PASS cuando:

- implementada
- compila
- prueba correspondiente pasa
- permisos verificados
- no rompe tests existentes
- documentada

Estados permitidos:

PASS
FAIL
BLOCKED
PENDING_EXTERNAL

---

# 31. NIGHTLY REPORT

Generar:

NIGHTLY_REPORT.md

Debe incluir:

Build
Backend
Frontend
Database
Authentication
Mobile
Customer 360
Pipeline
Appointments
Jarvis
Developer Mode
Custom Fields
Custom Modules
Financial Panel
Demo Mode
Demo Tour
Demo Isolation
SMS Gateway
WhatsApp Adapter
Website Adapter
Prequalify Adapter
Marketing API
Security
Tests

Para cada uno:

status
what was implemented
tests
errors
remaining work

