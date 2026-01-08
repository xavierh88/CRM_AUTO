import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const resources = {
  en: {
    translation: {
      // Navigation
      "nav.dashboard": "Dashboard",
      "nav.clients": "Clients",
      "nav.agenda": "Agenda",
      "nav.admin": "Admin",
      "nav.settings": "Settings",
      "nav.logout": "Logout",
      "nav.trash": "Trash",
      "nav.import": "Import",
      
      // Auth
      "auth.login": "Login",
      "auth.register": "Register",
      "auth.email": "Email",
      "auth.password": "Password",
      "auth.name": "Full Name",
      "auth.phone": "Phone",
      "auth.welcome": "Welcome to CARPLUS AUTOSALE",
      "auth.subtitle": "Manage your clients and appointments efficiently",
      
      // Dashboard
      "dashboard.title": "Dashboard",
      "dashboard.totalClients": "Total Clients",
      "dashboard.todayAppointments": "Today's Appointments",
      "dashboard.sales": "Sales",
      "dashboard.documentsComplete": "Documents Complete",
      "dashboard.appointmentsByStatus": "Appointments by Status",
      "dashboard.performance": "Salesperson Performance",
      
      // Agenda
      "agenda.subtitle": "Manage your appointments",
      
      // Clients
      "clients.title": "Clients",
      "clients.addNew": "Add Client",
      "clients.search": "Search clients...",
      "clients.firstName": "First Name",
      "clients.lastName": "Last Name",
      "clients.phone": "Phone",
      "clients.email": "Email",
      "clients.address": "Address",
      "clients.apartment": "Apartment",
      "clients.lastContact": "Last Contact",
      "clients.info": "Client Info",
      "clients.documents": "Documents",
      "clients.idUploaded": "ID Uploaded",
      "clients.incomeProof": "Income Proof",
      "clients.sendDocsSms": "Send Documents SMS",
      "clients.sendApptSms": "Send Appointment SMS",
      
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
      "nav.clients": "Clientes",
      "nav.agenda": "Agenda",
      "nav.admin": "Admin",
      "nav.settings": "Ajustes",
      "nav.logout": "Salir",
      "nav.trash": "Papelera",
      "nav.import": "Importar",
      
      // Auth
      "auth.login": "Iniciar Sesión",
      "auth.register": "Registrarse",
      "auth.email": "Correo Electrónico",
      "auth.password": "Contraseña",
      "auth.name": "Nombre Completo",
      "auth.phone": "Teléfono",
      "auth.welcome": "Bienvenido a CARPLUS AUTOSALE",
      "auth.subtitle": "Gestiona tus clientes y citas eficientemente",
      
      // Dashboard
      "dashboard.title": "Panel",
      "dashboard.totalClients": "Total Clientes",
      "dashboard.todayAppointments": "Citas de Hoy",
      "dashboard.sales": "Ventas",
      "dashboard.documentsComplete": "Documentos Completos",
      "dashboard.appointmentsByStatus": "Citas por Estado",
      "dashboard.performance": "Rendimiento de Vendedores",
      
      // Agenda
      "agenda.subtitle": "Gestiona tus citas",
      
      // Clients
      "clients.title": "Clientes",
      "clients.addNew": "Agregar Cliente",
      "clients.search": "Buscar clientes...",
      "clients.firstName": "Nombre",
      "clients.lastName": "Apellido",
      "clients.phone": "Teléfono",
      "clients.email": "Correo",
      "clients.address": "Dirección",
      "clients.apartment": "Apartamento",
      "clients.lastContact": "Último Contacto",
      "clients.info": "Info del Cliente",
      "clients.documents": "Documentos",
      "clients.idUploaded": "ID Subido",
      "clients.incomeProof": "Comprobante de Ingresos",
      "clients.sendDocsSms": "Enviar SMS Documentos",
      "clients.sendApptSms": "Enviar SMS Cita",
      
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
