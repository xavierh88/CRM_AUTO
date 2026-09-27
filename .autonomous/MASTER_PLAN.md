# DEALER AI OS V2 — AUTONOMOUS COMPLETION

MODE=AUTONOMOUS_UNATTENDED
MAX_BLOCK_STATE=LISTO_PARA_TU_PRUEBA

## OBJETIVO

Continuar automáticamente todo el trabajo pendiente de Dealer AI OS V2.

Ciclo obligatorio:

AUDIT
→ REUSE RESEARCH
→ IMPLEMENT
→ BUILD
→ FUNCTIONAL QA
→ VISUAL QA
→ FIX
→ RETEST
→ REPORT
→ NEXT BLOCK

El sistema puede avanzar automáticamente entre bloques mientras el propietario
está ausente.

NUNCA puede marcar un bloque APROBADO.
La aprobación final pertenece al propietario.

==================================================
SEGURIDAD
==================================================

WORKTREE permitido:

/opt/dealer-ai-v2/worktrees/070-final-product-completion

PROHIBIDO:

- tocar /var/www/carplus
- desplegar producción
- reiniciar producción
- modificar SoyEcua
- merge
- push
- force push
- git reset --hard
- git clean destructivo
- borrar cambios existentes
- imprimir secretos
- modificar secretos innecesariamente
- clientes reales
- documentos reales
- SMS reales
- WhatsApp reales
- mensajes sociales reales
- acciones financieras reales

Usar exclusivamente datos Demo/ficticios.

No desactivar autenticación ni aislamiento multi-dealer para hacer pasar tests.

==================================================
REUSE-FIRST GLOBAL
==================================================

Antes de desarrollar una función importante desde cero:

1. Revisar código existente.
2. Revisar dependencias existentes.
3. Buscar solución reutilizable cuando pueda ahorrar trabajo:

- skills
- componentes existentes
- librerías
- paquetes mantenidos
- SDK oficial
- API oficial
- repositorios open-source
- herramientas self-hosted

Orden de preferencia:

1. funcionalidad existente del proyecto
2. SDK/API oficial
3. librería estable
4. skill/herramienta confiable
5. repositorio open-source mantenido
6. adapter pequeño propio
7. implementación completa propia

Antes de incorporar una solución externa comprobar:

- licencia
- mantenimiento
- seguridad básica
- compatibilidad
- dependencias
- RAM/CPU
- complejidad
- configuración
- documentación

No instalar algo solamente porque existe.

No ejecutar scripts desconocidos como root.

No introducir una dependencia grande para resolver un problema pequeño.

Si investigar cuesta más que implementar una solución pequeña y segura,
implementar directamente.

INSTALADO != FUNCIONANDO
BUILD OK != FUNCION TERMINADA

==================================================
VERIFICACION
==================================================

Cuando sea técnicamente posible verificar:

UI
→ ACTION
→ API
→ BACKEND
→ DATA/PERSISTENCE
→ VISIBLE RESULT

Si una integración externa necesita:

OAuth
QR
token
hardware
cuenta externa
Meta approval
permisos
acción humana

preparar todo lo demás y marcar únicamente:

WAITING_CONFIG

No detener los demás bloques.

Nunca fingir CONNECTED.

==================================================
01 DEALS
==================================================

Estado inicial: EN_DESARROLLO

Ya confirmado por propietario:

- Deals visible
- drag funciona
- abrir Deal funciona
- abre cliente correspondiente

Pendiente:

- persistencia de commercial_stage
- reload
- frontend/backend stages
- edición
- asociación cliente
- vehículo/interés
- precio/monto/down payment cuando corresponda
- board/table
- errores
- empty states
- dealer isolation
- responsive básico

No romper lo ya aprobado.

==================================================
02 CONVERSATIONS
==================================================

Antes de desarrollar integraciones desde cero investigar herramientas,
skills y repositorios existentes.

Evaluar especialmente infraestructura omnicanal reutilizable.

Evaluar Chatwoot u otra alternativa equivalente solamente si reduce
complejidad y recursos.

Dealer AI debe continuar siendo la interfaz principal.

Arquitectura deseada:

Dealer AI
→ Conversation Gateway
→ canales/adapters

Canales:

SMS / Phone
WhatsApp
Facebook Messenger
Instagram DM
TikTok DM
Website Chat

SMS/Teléfono:

Prioridad = Android/physical phone gateway.

Twilio NO debe convertirse en requisito primario.

Investigar Android SMS gateways open-source mantenidos antes de construir
uno desde cero.

Necesidades:

- incoming
- outgoing
- webhook
- delivery state cuando exista
- device health
- authentication
- retry/idempotency
- client mapping
- conversation mapping
- audit trail

No instalar APK desconocido automáticamente.

WhatsApp/Facebook/Instagram:

preferir APIs oficiales y configuración sencilla.

TikTok:

solo funcionalidad soportada oficialmente.

Si no existe acceso real:
NOT_CONFIGURED / WAITING_CONFIG.

AI/HUMAN HANDOFF:

incoming
→ AI/Jarvis
→ respuesta autorizada
→ humano puede tomar control
→ AI se detiene
→ humano puede devolver control a AI

Conservar:

channel
client
timestamp
AI/human author
delivery status
audit log

Configuración ideal dentro de Dealer AI:

Settings
→ Communications
→ Channel
→ Connect
→ Authentication
→ Test
→ Ready

Crear:

.autonomous/reports/CONVERSATIONS_RESEARCH.md

antes de una integración externa importante.

==================================================
03 APPOINTMENTS
==================================================

Verificar:

- list
- create
- edit
- status
- client association
- date/time
- persistence
- cancel/delete según diseño
- dealer isolation
- errors
- empty state
- responsive

Aplicar REUSE-FIRST cuando ayude.

==================================================
04 DOCUMENTS
==================================================

Verificar:

- list
- synthetic upload
- download
- delete
- client association
- permissions
- dealer isolation
- errors
- empty state

Nunca usar documentos reales.

==================================================
05 REPORTS
==================================================

Verificar:

- backend data
- Demo dataset real
- filters
- periods
- totals
- sales
- leads/clients
- opportunities
- empty states
- errors

No inventar números para llenar UI.

==================================================
06 JARVIS
==================================================

Verificar end-to-end:

UI
→ Jarvis
→ authorized tool/action
→ API
→ backend
→ result
→ visible response

Jarvis NO puede:

- inventar resultados
- afirmar acciones no ejecutadas
- saltarse autorización
- escribir directamente DB sin capa autorizada
- realizar comunicaciones externas reales

Investigar skills/tools/libraries reutilizables antes de crear herramientas
complejas desde cero.

==================================================
07 DEMO
==================================================

Verificar:

- fictional data
- Demo identity
- isolation
- navigation
- tour si existe
- safe reset si existe
- no external sends
- no fake integrations

==================================================
08 REGRESSION
==================================================

Revalidar:

Dashboard
Inventory
Leads
Clients
Deals
Conversations
Appointments
Documents
Reports
Jarvis

No rediseñar módulos ya aprobados salvo bug demostrado.

==================================================
09 RESPONSIVE
==================================================

Verificar:

390x844
430x932
768x1024
900x1200
1023x1200
1024x1200
1280x800
1440x900

Buscar:

- horizontal overflow
- clipped buttons
- broken modals
- incorrect navigation
- sidebar errors
- bottom-nav errors
- unusable tables
- overlapping text
- inaccessible actions

==================================================
10 FINAL QA
==================================================

Ejecutar:

build
available tests
API checks
auth
dealer isolation
navigation
critical workflows
Demo safety
regression

Warnings existentes no equivalen automáticamente a build failure,
pero deben documentarse.

==================================================
REPORTING
==================================================

Cada bloque debe crear:

.autonomous/reports/<BLOCK>.md

Formato:

BLOCK=
STATUS=
BUILD=
FUNCTIONAL_QA=
VISUAL_QA=
API=
BACKEND=
PERSISTENCE=
DEALER_ISOLATION=
RESPONSIVE=
REUSE_RESEARCH=
TOOLS_USED=
FIXES=
KNOWN_LIMITATIONS=
BLOCKERS=
FILES_CHANGED=
NEXT=

Estados permitidos:

NO_INICIADO
EN_DESARROLLO
BUILD_OK
FUNCTIONAL_QA
VISUAL_QA
LISTO_PARA_TU_PRUEBA
BLOCKED
FAILED

Nunca APROBADO automáticamente.

Al terminar crear:

.autonomous/reports/FINAL_REPORT.md

y dejar:

AUTONOMOUS_WORK_COMPLETE
WAITING_FOR_OWNER_REVIEW

NO DEPLOY
NO MERGE
NO PUSH
