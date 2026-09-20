# DEALER AI OS V2 - AGENT RULES

## WORKSPACE PERMITIDO
El unico workspace modificable es:

/opt/dealer-ai-v2/app

## PRODUCCION PROHIBIDA
Nunca leer para copiar secretos ni modificar:

/var/www/carplus

Nunca modificar, reiniciar, desplegar, detener o reconfigurar:
- produccion actual
- nginx de produccion
- uvicorn de produccion
- MongoDB de produccion
- servicios Docker de produccion
- rama main

## RAMA PERMITIDA
Trabajar unicamente en:

dealer-ai-v2

Nunca cambiar a main.
Nunca hacer merge a main.
Nunca desplegar a produccion.

## DATOS
No usar datos reales de clientes.
No copiar:
- uploads
- SSN
- identificaciones
- comprobantes de ingresos
- comprobantes de residencia
- documentos reales
- telefonos reales
- emails reales

Para desarrollo y pruebas usar exclusivamente datos ficticios.

## OBJETIVO
Construir Dealer AI OS V2 reutilizando la base funcional existente sin romper funciones actuales.

## METODO DE TRABAJO
Para cada cambio:

1. Analizar codigo actual.
2. Implementar cambio.
3. Ejecutar pruebas.
4. Si falla, corregir.
5. Repetir hasta PASS o bloqueo justificado.
6. Documentar resultado.
7. Continuar con el siguiente requisito.

## REGLAS DE SEGURIDAD
No ejecutar comandos destructivos fuera del workspace.
No usar:
rm -rf /
rm -rf /var/www
docker system prune
docker volume prune
drop database
delete production data

No modificar firewall.
No cambiar credenciales del servidor.
No instalar software innecesario.

## ACCIONES EXTERNAS
No enviar SMS reales.
No enviar WhatsApp reales.
No enviar emails reales.
No ejecutar pagos.
No consultar credito real.
No usar APIs de financiamiento reales.
No publicar contenido real.

Estas funciones deben usar adapters/mock providers hasta que el propietario autorice integraciones.

## AI / JARVIS
Jarvis nunca escribe directamente en MongoDB.
Debe operar mediante herramientas tipadas/API interna con:
- autenticacion
- permisos
- validacion
- confirmacion cuando corresponda
- audit log

## MODO DEVELOPER
Cambios estructurales solo permitidos para SYSTEM_DEVELOPER.

Requieren:
- reautenticacion
- vista previa
- confirmacion explicita
- audit log
- versionado
- rollback cuando sea posible

## DEMO MODE
El usuario DEMO debe estar totalmente aislado de datos reales.

Debe usar:
- clientes ficticios
- leads ficticios
- citas ficticias
- vehiculos ficticios
- SMS simulados
- ventas ficticias
- finanzas ficticias
- prequalifications ficticias

Debe existir:
- tour guiado ES/EN
- indicador DEMO
- reinicio del tour
- reset de datos demo
- bloqueo backend contra acceso a datos reales

## MOBILE FIRST
La experiencia movil es prioritaria.

Mobile nav preferida:
- Home
- Leads
- +
- Agenda
- AI

El usuario debe poder operar las acciones principales con una mano y con pocos toques.

## SMS GATEWAY
Preparar adapter para Android SMS Gateway.

Estados:
ONLINE
OFFLINE
DEGRADED

Si gateway esta offline:
- no enviar
- informar al usuario
- registrar evento
- Jarvis debe reconocer la indisponibilidad

## INTEGRACIONES PENDIENTES
Estas pueden quedar con adapter/mock claramente documentado:

- proveedor externo de prequalify/financiamiento
- WhatsApp real
- website ZIP
- Marketing AI OS
- inventario externo
- Android SMS fisico

## PROHIBICION ABSOLUTA
Nunca declarar una funcion como PASS si no fue probada.

