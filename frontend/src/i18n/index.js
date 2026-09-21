import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: {
    translation: {
      // Navigation
      "nav.dashboard": "Dashboard",
      "nav.inventory": "Inventory",
      "nav.leads": "Leads",
      "nav.customers": "Customers",
      "nav.deals": "Deals",
      "nav.conversations": "Conversations",
      "nav.appointments": "Appointments",
      "nav.documents": "Documents",
      "nav.reports": "Reports",
      "nav.jarvis": "Jarvis",
      "nav.settings": "Settings",
      "nav.logout": "Logout",
      "nav.trash": "Trash",
      "nav.import": "Import",
      "nav.more": "More",
      "nav.developer": "Developer",
      
      // Header
      "header.search": "Search clients, vehicles, appointments...",
      
      // Auth
      "auth.login": "Login",
      "auth.register": "Register",
      "auth.email": "Email",
      "auth.password": "Password",
      "auth.name": "Full Name",
      "auth.phone": "Phone",
      "auth.welcome": "Welcome to CARPLUS AUTOSALE",
      "auth.subtitle": "Manage your clients and appointments efficiently",
      
      // Dashboard / Action Center
      "dashboard.title": "Action Center",
      "dashboard.subtitle": "Your operational priorities for today",
      "dashboard.todayAppointments": "Today's Appointments",
      "dashboard.awaitingConfirmation": "Awaiting Confirmation",
      "dashboard.newLeads": "New Leads (24h)",
      "dashboard.leadsOver48h": "Leads > 48h",
      "dashboard.staleLeads": "Stale Leads",
      "dashboard.unreadConversations": "Unread Conversations",
      "dashboard.incompleteDocs": "Incomplete Documents",
      "dashboard.prequalStatus": "Prequal Status",
      "dashboard.nearCloseDeals": "Near-Close Deals",
      "dashboard.followupsDue": "Follow-ups Due",
      "dashboard.inventoryAttention": "Inventory Attention",
      "dashboard.quickActions": "Quick Actions",
      "dashboard.call": "Call",
      "dashboard.sms": "SMS",
      "dashboard.openLead": "Open Lead",
      "dashboard.confirmAppt": "Confirm Appt",
      "dashboard.createAppt": "Create Appt",
      "dashboard.addLead": "Add Lead",
      "dashboard.addVehicle": "Add Vehicle",
      "dashboard.noActionItems": "No action items — you're all caught up!",
      
      // Inventory
      "inventory.title": "Inventory",
      "inventory.addVehicle": "Add Vehicle",
      "inventory.search": "Search inventory...",
      "inventory.filters": "Filters",
      "inventory.status": "Status",
      "inventory.make": "Make",
      "inventory.model": "Model",
      "inventory.year": "Year",
      "inventory.price": "Price",
      "inventory.vin": "VIN",
      "inventory.mileage": "Mileage",
      "inventory.color": "Color",
      "inventory.daysOnLot": "Days on Lot",
      "inventory.noVehicles": "No vehicles found",
      
      // Leads
      "leads.title": "Leads",
      "leads.addLead": "Add Lead",
      "leads.search": "Search leads...",
      "leads.source": "Source",
      "leads.status": "Status",
      "leads.salesperson": "Salesperson",
      "leads.vehicleInterest": "Vehicle Interest",
      "leads.followUp": "Follow-up",
      "leads.attribution": "Attribution",
      "leads.score": "Score",
      "leads.noLeads": "No leads found",
      
      // Customers
      "customers.title": "Customers",
      "customers.addCustomer": "Add Customer",
      "customers.search": "Search customers...",
      "customers.info": "Customer Info",
      "customers.documents": "Documents",
      "customers.idUploaded": "ID Uploaded",
      "customers.incomeProof": "Income Proof",
      "customers.sendDocsSms": "Send Documents SMS",
      "customers.sendApptSms": "Send Appointment SMS",
      "customers.lastContact": "Last Contact",
      "customers.noCustomers": "No customers found",
      
      // Deals
      "deals.title": "Deals",
      "deals.pipeline": "Pipeline",
      "deals.addDeal": "Add Deal",
      "deals.stage": "Stage",
      "deals.value": "Value",
      "deals.probability": "Probability",
      "deals.closeDate": "Close Date",
      "deals.noDeals": "No deals found",
      
      // Conversations
      "conversations.title": "Conversations",
      "conversations.search": "Search conversations...",
      "conversations.channel": "Channel",
      "conversations.unread": "Unread",
      "conversations.lastMessage": "Last Message",
      "conversations.noConversations": "No conversations",
      
      // Appointments
      "appointments.title": "Appointments",
      "appointments.schedule": "Schedule Appointment",
      "appointments.date": "Date",
      "appointments.time": "Time",
      "appointments.dealer": "Dealer",
      "appointments.language": "Language",
      "appointments.changeTime": "Change Time",
      "appointments.status": "Status",
      "appointments.markCompleted": "Mark as Completed",
      "appointments.markNoShow": "Mark as No-Show",
      "appointments.today": "Today",
      "appointments.tomorrow": "Tomorrow",
      "appointments.thisWeek": "This Week",
      "appointments.unconfigured": "Unconfigured",
      "appointments.noAppointments": "No appointments",
      
      // Documents
      "documents.title": "Documents",
      "documents.search": "Search documents...",
      "documents.type": "Type",
      "documents.status": "Status",
      "documents.uploaded": "Uploaded",
      "documents.pending": "Pending",
      "documents.complete": "Complete",
      "documents.noDocuments": "No documents",
      
      // Reports
      "reports.title": "Reports",
      "reports.sales": "Sales Report",
      "reports.leads": "Leads Report",
      "reports.appointments": "Appointments Report",
      "reports.closeRate": "Close Rate",
      "reports.attribution": "Attribution",
      "reports.inventory": "Inventory Report",
      "reports.financial": "Financial Summary",
      "reports.period": "Period",
      "reports.export": "Export",
      
      // Jarvis
      "jarvis.title": "Jarvis Assistant",
      "jarvis.placeholder": "Ask Jarvis anything...",
      "jarvis.thinking": "Jarvis is thinking...",
      "jarvis.suggestions": "Try asking:",
      "jarvis.demoNotice": "Demo mode — responses are simulated",
      
      // Status
      "status.agendado": "Scheduled",
      "status.sin_configurar": "Not Configured",
      "status.cambio_hora": "Time Changed",
      "status.tres_semanas": "3 Weeks No Response",
      "status.no_show": "No Show",
      "status.cumplido": "Completed",
      
      // Co-Signer
      "cosigner.title": "Co-Signers",
      "cosigner.add": "Add Co-Signer",
      "cosigner.new": "New Co-Signer",
      "cosigner.existing": "Link Existing",
      "cosigner.searchPhone": "Search by phone...",
      
      // User Records
      "records.title": "User Records",
      "records.addNew": "Add Record",
      "records.checklist": "Checklist",
      "records.dl": "DL",
      "records.checks": "Checks",
      "records.ssn": "SSN",
      "records.itin": "ITIN",
      "records.auto": "Auto",
      "records.credit": "Credit",
      "records.bank": "Bank",
      "records.autoLoan": "Auto Loan",
      "records.downPayment": "Down Payment",
      "records.dealer": "Dealer",
      "records.sold": "Sold",
      "records.vehicleMake": "Vehicle Make",
      "records.vehicleYear": "Vehicle Year",
      "records.saleDate": "Sale Date",
      
      // Common
      "common.save": "Save",
      "common.cancel": "Cancel",
      "common.delete": "Delete",
      "common.edit": "Edit",
      "common.view": "View",
      "common.restore": "Restore",
      "common.loading": "Loading...",
      "common.noData": "No data available",
      "common.success": "Success",
      "common.error": "Error",
      "common.confirm": "Confirm",
      "common.actions": "Actions",
      "common.pending": "Pending Integration",
      "common.disabled": "Disabled",
      "common.demoData": "Demo data — fictional",
      
      // Admin
      "admin.users": "Users",
      "admin.trash": "Trash",
      "admin.deletedClients": "Deleted Clients",
      "admin.deletedRecords": "Deleted Records",
      "admin.permanentDelete": "Delete Permanently"
    }
  },
  es: {
    translation: {
      // Navigation
      "nav.dashboard": "Panel",
      "nav.inventory": "Inventario",
      "nav.leads": "Leads",
      "nav.customers": "Clientes",
      "nav.deals": "Negocios",
      "nav.conversations": "Conversaciones",
      "nav.appointments": "Citas",
      "nav.documents": "Documentos",
      "nav.reports": "Reportes",
      "nav.jarvis": "Jarvis",
      "nav.settings": "Ajustes",
      "nav.logout": "Salir",
      "nav.trash": "Papelera",
      "nav.import": "Importar",
      "nav.more": "Más",
      "nav.developer": "Desarrollador",
      
      // Header
      "header.search": "Buscar clientes, vehículos, citas...",
      
      // Auth
      "auth.login": "Iniciar Sesión",
      "auth.register": "Registrarse",
      "auth.email": "Correo Electrónico",
      "auth.password": "Contraseña",
      "auth.name": "Nombre Completo",
      "auth.phone": "Teléfono",
      "auth.welcome": "Bienvenido a CARPLUS AUTOSALE",
      "auth.subtitle": "Gestiona tus clientes y citas eficientemente",
      
      // Dashboard / Action Center
      "dashboard.title": "Centro de Acciones",
      "dashboard.subtitle": "Tus prioridades operativas para hoy",
      "dashboard.todayAppointments": "Citas de Hoy",
      "dashboard.awaitingConfirmation": "Pendientes de Confirmar",
      "dashboard.newLeads": "Leads Nuevos (24h)",
      "dashboard.leadsOver48h": "Leads > 48h",
      "dashboard.staleLeads": "Leads Estancados",
      "dashboard.unreadConversations": "Conversaciones Sin Leer",
      "dashboard.incompleteDocs": "Documentos Incompletos",
      "dashboard.prequalStatus": "Estado Precalificación",
      "dashboard.nearCloseDeals": "Negocios Próximos al Cierre",
      "dashboard.followupsDue": "Seguimientos Pendientes",
      "dashboard.inventoryAttention": "Inventario Requiere Atención",
      "dashboard.quickActions": "Acciones Rápidas",
      "dashboard.call": "Llamar",
      "dashboard.sms": "SMS",
      "dashboard.openLead": "Abrir Lead",
      "dashboard.confirmAppt": "Confirmar Cita",
      "dashboard.createAppt": "Crear Cita",
      "dashboard.addLead": "Agregar Lead",
      "dashboard.addVehicle": "Agregar Vehículo",
      "dashboard.noActionItems": "¡Sin acciones pendientes — todo al día!",
      
      // Inventory
      "inventory.title": "Inventario",
      "inventory.addVehicle": "Agregar Vehículo",
      "inventory.search": "Buscar inventario...",
      "inventory.filters": "Filtros",
      "inventory.status": "Estado",
      "inventory.make": "Marca",
      "inventory.model": "Modelo",
      "inventory.year": "Año",
      "inventory.price": "Precio",
      "inventory.vin": "VIN",
      "inventory.mileage": "Kilometraje",
      "inventory.color": "Color",
      "inventory.daysOnLot": "Días en Lote",
      "inventory.noVehicles": "No se encontraron vehículos",
      
      // Leads
      "leads.title": "Leads",
      "leads.addLead": "Agregar Lead",
      "leads.search": "Buscar leads...",
      "leads.source": "Origen",
      "leads.status": "Estado",
      "leads.salesperson": "Vendedor",
      "leads.vehicleInterest": "Interés en Vehículo",
      "leads.followUp": "Seguimiento",
      "leads.attribution": "Atribución",
      "leads.score": "Puntuación",
      "leads.noLeads": "No se encontraron leads",
      
      // Customers
      "customers.title": "Clientes",
      "customers.addCustomer": "Agregar Cliente",
      "customers.search": "Buscar clientes...",
      "customers.info": "Info del Cliente",
      "customers.documents": "Documentos",
      "customers.idUploaded": "ID Subido",
      "customers.incomeProof": "Comprobante de Ingresos",
      "customers.sendDocsSms": "Enviar SMS Documentos",
      "customers.sendApptSms": "Enviar SMS Cita",
      "customers.lastContact": "Último Contacto",
      "customers.noCustomers": "No se encontraron clientes",
      
      // Deals
      "deals.title": "Negocios",
      "deals.pipeline": "Pipeline",
      "deals.addDeal": "Agregar Negocio",
      "deals.stage": "Etapa",
      "deals.value": "Valor",
      "deals.probability": "Probabilidad",
      "deals.closeDate": "Fecha de Cierre",
      "deals.noDeals": "No se encontraron negocios",
      
      // Conversations
      "conversations.title": "Conversaciones",
      "conversations.search": "Buscar conversaciones...",
      "conversations.channel": "Canal",
      "conversations.unread": "Sin Leer",
      "conversations.lastMessage": "Último Mensaje",
      "conversations.noConversations": "No hay conversaciones",
      
      // Appointments
      "appointments.title": "Citas",
      "appointments.schedule": "Programar Cita",
      "appointments.date": "Fecha",
      "appointments.time": "Hora",
      "appointments.dealer": "Concesionario",
      "appointments.language": "Idioma",
      "appointments.changeTime": "Cambiar Hora",
      "appointments.status": "Estado",
      "appointments.markCompleted": "Marcar Completada",
      "appointments.markNoShow": "Marcar No Asistió",
      "appointments.today": "Hoy",
      "appointments.tomorrow": "Mañana",
      "appointments.thisWeek": "Esta Semana",
      "appointments.unconfigured": "Sin Configurar",
      "appointments.noAppointments": "No hay citas",
      
      // Documents
      "documents.title": "Documentos",
      "documents.search": "Buscar documentos...",
      "documents.type": "Tipo",
      "documents.status": "Estado",
      "documents.uploaded": "Subido",
      "documents.pending": "Pendiente",
      "documents.complete": "Completo",
      "documents.noDocuments": "No hay documentos",
      
      // Reports
      "reports.title": "Reportes",
      "reports.sales": "Reporte de Ventas",
      "reports.leads": "Reporte de Leads",
      "reports.appointments": "Reporte de Citas",
      "reports.closeRate": "Tasa de Cierre",
      "reports.attribution": "Atribución",
      "reports.inventory": "Reporte de Inventario",
      "reports.financial": "Resumen Financiero",
      "reports.period": "Período",
      "reports.export": "Exportar",
      
      // Jarvis
      "jarvis.title": "Asistente Jarvis",
      "jarvis.placeholder": "Pregúntale a Jarvis...",
      "jarvis.thinking": "Jarvis está pensando...",
      "jarvis.suggestions": "Prueba preguntando:",
      "jarvis.demoNotice": "Modo demo — respuestas simuladas",
      
      // Status
      "status.agendado": "Agendado",
      "status.sin_configurar": "Sin Configurar",
      "status.cambio_hora": "Cambio de Hora",
      "status.tres_semanas": "3 Semanas Sin Respuesta",
      "status.no_show": "No Asistió",
      "status.cumplido": "Cumplido",
      
      // Co-Signer
      "cosigner.title": "Co-Firmantes",
      "cosigner.add": "Agregar Co-Firmante",
      "cosigner.new": "Nuevo Co-Firmante",
      "cosigner.existing": "Vincular Existente",
      "cosigner.searchPhone": "Buscar por teléfono...",
      
      // User Records
      "records.title": "Cartillas",
      "records.addNew": "Agregar Cartilla",
      "records.checklist": "Lista de Verificación",
      "records.dl": "DL",
      "records.checks": "Cheques",
      "records.ssn": "SSN",
      "records.itin": "ITIN",
      "records.auto": "Auto",
      "records.credit": "Crédito",
      "records.bank": "Banco",
      "records.autoLoan": "Préstamo Auto",
      "records.downPayment": "Enganche",
      "records.dealer": "Concesionario",
      "records.sold": "Vendido",
      "records.vehicleMake": "Marca del Vehículo",
      "records.vehicleYear": "Año del Vehículo",
      "records.saleDate": "Fecha de Venta",
      
      // Common
      "common.save": "Guardar",
      "common.cancel": "Cancelar",
      "common.delete": "Eliminar",
      "common.edit": "Editar",
      "common.view": "Ver",
      "common.restore": "Restaurar",
      "common.loading": "Cargando...",
      "common.noData": "Sin datos disponibles",
      "common.success": "Éxito",
      "common.error": "Error",
      "common.confirm": "Confirmar",
      "common.actions": "Acciones",
      "common.pending": "Integración Pendiente",
      "common.disabled": "Deshabilitado",
      "common.demoData": "Datos demo — ficticios",
      
      // Admin
      "admin.users": "Usuarios",
      "admin.trash": "Papelera",
      "admin.deletedClients": "Clientes Eliminados",
      "admin.deletedRecords": "Cartillas Eliminadas",
      "admin.permanentDelete": "Eliminar Permanentemente"
    }
  }
};

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: localStorage.getItem('language') || 'en',
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false
    }
  });

export default i18n;