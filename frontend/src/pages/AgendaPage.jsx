import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Calendar } from '../components/ui/calendar';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { Calendar as CalendarIcon, Clock, MapPin, User, Send, CheckCircle2, XCircle, Phone, AlertTriangle, Bell, MessageSquare } from 'lucide-react';
import { format, isToday, isTomorrow, addDays, parseISO, isWithinInterval, startOfDay, endOfDay, isSameDay } from 'date-fns';
import { es } from 'date-fns/locale';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AgendaPage() {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [filter, setFilter] = useState('all');
  const [viewMode, setViewMode] = useState('grouped'); // 'grouped' or 'selected'

  useEffect(() => {
    fetchAppointments();
  }, []);

  const fetchAppointments = async () => {
    try {
      const response = await axios.get(`${API}/appointments/agenda`);
      setAppointments(response.data);
    } catch (error) {
      toast.error('Failed to fetch appointments');
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (apptId, status) => {
    try {
      await axios.put(`${API}/appointments/${apptId}/status?status=${status}`);
      fetchAppointments();
      toast.success('Status updated');
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const sendReminderSMS = async (appointment) => {
    try {
      await axios.post(`${API}/sms/send-appointment-link?client_id=${appointment.client_id}&appointment_id=${appointment.id}`);
      toast.success('SMS de recordatorio enviado');
    } catch (error) {
      toast.error('Failed to send SMS');
    }
  };

  // Get appointments for selected date
  const getSelectedDateAppointments = () => {
    return appointments.filter(a => {
      if (!a.date) return false;
      return isSameDay(parseISO(a.date), selectedDate);
    });
  };

  // Get dates that have appointments (for calendar highlighting)
  const appointmentDates = appointments
    .filter(a => a.date)
    .map(a => parseISO(a.date));

  const getFilteredAppointments = () => {
    let filtered = appointments;

    // Filter by status
    if (filter !== 'all') {
      filtered = filtered.filter(a => a.status === filter);
    }

    // Group by date
    const today = startOfDay(new Date());
    const tomorrow = addDays(today, 1);
    const weekEnd = addDays(today, 7);

    const grouped = {
      today: filtered.filter(a => a.date && isToday(parseISO(a.date))),
      tomorrow: filtered.filter(a => a.date && isTomorrow(parseISO(a.date))),
      thisWeek: filtered.filter(a => {
        if (!a.date) return false;
        const date = parseISO(a.date);
        return isWithinInterval(date, { start: addDays(today, 2), end: weekEnd });
      }),
      unconfigured: filtered.filter(a => !a.date || a.status === 'sin_configurar')
    };

    return grouped;
  };

  const getStatusBadge = (status) => (
    <span className={`status-badge status-${status}`}>
      <span className={`w-2 h-2 rounded-full mr-2 dot-${status}`}></span>
      {t(`status.${status}`)}
    </span>
  );

  // Calculate stats
  const stats = {
    total: appointments.length,
    today: appointments.filter(a => a.date && isToday(parseISO(a.date))).length,
    pending: appointments.filter(a => a.status === 'agendado' || a.status === 'sin_configurar').length,
    completed: appointments.filter(a => a.status === 'cumplido').length,
    noShow: appointments.filter(a => a.status === 'no_show').length,
    runningLate: appointments.filter(a => a.running_late).length,
    reminders: appointments.filter(a => a.type === 'reminder').length
  };

  const grouped = getFilteredAppointments();
  const selectedDateAppts = getSelectedDateAppointments();
  const dateLocale = i18n.language === 'es' ? es : undefined;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="agenda-page">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{t('nav.agenda')}</h1>
          <p className="text-slate-500 mt-1">{t('agenda.subtitle') || 'Manage your appointments'}</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={viewMode} onValueChange={setViewMode}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="grouped">Vista Agrupada</SelectItem>
              <SelectItem value="selected">Vista por Día</SelectItem>
            </SelectContent>
          </Select>
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-48" data-testid="status-filter">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todos los Estados</SelectItem>
              <SelectItem value="agendado">{t('status.agendado')}</SelectItem>
              <SelectItem value="sin_configurar">{t('status.sin_configurar')}</SelectItem>
              <SelectItem value="cambio_hora">{t('status.cambio_hora')}</SelectItem>
              <SelectItem value="tres_semanas">{t('status.tres_semanas')}</SelectItem>
              <SelectItem value="no_show">{t('status.no_show')}</SelectItem>
              <SelectItem value="cumplido">{t('status.cumplido')}</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <Card className="dashboard-card">
          <CardContent className="p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide">Total</p>
            <p className="text-2xl font-bold text-slate-900">{stats.total}</p>
          </CardContent>
        </Card>
        <Card className="dashboard-card border-l-4 border-l-blue-500">
          <CardContent className="p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide">Hoy</p>
            <p className="text-2xl font-bold text-blue-600">{stats.today}</p>
          </CardContent>
        </Card>
        <Card className="dashboard-card border-l-4 border-l-amber-500">
          <CardContent className="p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide">Pendientes</p>
            <p className="text-2xl font-bold text-amber-600">{stats.pending}</p>
          </CardContent>
        </Card>
        <Card className="dashboard-card border-l-4 border-l-emerald-500">
          <CardContent className="p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide">Cumplidas</p>
            <p className="text-2xl font-bold text-emerald-600">{stats.completed}</p>
          </CardContent>
        </Card>
        <Card className="dashboard-card border-l-4 border-l-slate-400">
          <CardContent className="p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wide">No Show</p>
            <p className="text-2xl font-bold text-slate-500">{stats.noShow}</p>
          </CardContent>
        </Card>
        {stats.runningLate > 0 && (
          <Card className="dashboard-card border-l-4 border-l-orange-500 bg-orange-50">
            <CardContent className="p-4">
              <p className="text-xs text-orange-600 uppercase tracking-wide flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                Llegando Tarde
              </p>
              <p className="text-2xl font-bold text-orange-600">{stats.runningLate}</p>
            </CardContent>
          </Card>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Calendar */}
        <Card className="dashboard-card lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <CalendarIcon className="w-5 h-5 text-blue-600" />
              Calendario
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Calendar
              mode="single"
              selected={selectedDate}
              onSelect={(date) => {
                setSelectedDate(date || new Date());
                setViewMode('selected');
              }}
              className="rounded-md border"
              locale={dateLocale}
              modifiers={{
                hasAppointment: appointmentDates
              }}
              modifiersClassNames={{
                hasAppointment: 'bg-blue-100 text-blue-900 font-semibold'
              }}
            />
            {viewMode === 'selected' && (
              <div className="mt-4 p-3 bg-slate-50 rounded-lg">
                <p className="text-sm font-medium text-slate-700">
                  {format(selectedDate, "EEEE, d 'de' MMMM", { locale: dateLocale })}
                </p>
                <p className="text-xs text-slate-500">
                  {selectedDateAppts.length} {selectedDateAppts.length === 1 ? 'cita' : 'citas'}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Appointments List */}
        <div className="lg:col-span-2 space-y-6">
          {viewMode === 'selected' ? (
            // View by selected date
            <AppointmentSection
              title={format(selectedDate, "EEEE, d 'de' MMMM yyyy", { locale: dateLocale })}
              appointments={selectedDateAppts}
              getStatusBadge={getStatusBadge}
              updateStatus={updateStatus}
              sendReminderSMS={sendReminderSMS}
              emptyMessage="No hay citas para esta fecha"
            />
          ) : (
            // Grouped view
            <>
              {/* Today */}
              <AppointmentSection
                title={`Hoy (${format(new Date(), 'd MMM', { locale: dateLocale })})`}
                appointments={grouped.today}
                getStatusBadge={getStatusBadge}
                updateStatus={updateStatus}
                sendReminderSMS={sendReminderSMS}
                emptyMessage="No hay citas hoy"
                highlight
              />

              {/* Tomorrow */}
              <AppointmentSection
                title={`Mañana (${format(addDays(new Date(), 1), 'd MMM', { locale: dateLocale })})`}
                appointments={grouped.tomorrow}
                getStatusBadge={getStatusBadge}
                updateStatus={updateStatus}
                sendReminderSMS={sendReminderSMS}
                emptyMessage="No hay citas mañana"
              />

              {/* This Week */}
              <AppointmentSection
                title="Próximos 7 Días"
                appointments={grouped.thisWeek}
                getStatusBadge={getStatusBadge}
                updateStatus={updateStatus}
                sendReminderSMS={sendReminderSMS}
                emptyMessage="No hay citas próximas"
              />

              {/* Not Configured */}
              {grouped.unconfigured.length > 0 && (
                <AppointmentSection
                  title="Sin Configurar"
                  appointments={grouped.unconfigured}
                  getStatusBadge={getStatusBadge}
                  updateStatus={updateStatus}
                  sendReminderSMS={sendReminderSMS}
                  emptyMessage=""
                  isWarning
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function AppointmentSection({ title, appointments, getStatusBadge, updateStatus, sendReminderSMS, emptyMessage, isWarning, highlight }) {
  const { t, i18n } = useTranslation();
  const dateLocale = i18n.language === 'es' ? es : undefined;

  if (appointments.length === 0 && emptyMessage) {
    return (
      <Card className="dashboard-card">
        <CardHeader>
          <CardTitle className="text-lg">{title}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-slate-400 text-center py-4">{emptyMessage}</p>
        </CardContent>
      </Card>
    );
  }

  if (appointments.length === 0) return null;

  return (
    <Card className={`dashboard-card ${isWarning ? 'border-orange-200 bg-orange-50/30' : ''} ${highlight ? 'border-blue-200 bg-blue-50/30' : ''}`}>
      <CardHeader className="pb-2">
        <CardTitle className={`text-lg flex items-center justify-between ${isWarning ? 'text-orange-600' : ''} ${highlight ? 'text-blue-700' : ''}`}>
          <span>{title}</span>
          <Badge variant="secondary" className={`${highlight ? 'bg-blue-100 text-blue-700' : ''}`}>
            {appointments.length}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {appointments.map((appt) => (
          <div
            key={appt.id}
            className={`agenda-item status-${appt.status} bg-white rounded-lg border p-4 ${appt.running_late ? 'border-l-4 border-l-orange-500' : ''}`}
            data-testid={`appointment-${appt.id}`}
          >
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2 flex-wrap">
                  <User className="w-4 h-4 text-slate-400" />
                  <Link 
                    to={`/clients?search=${encodeURIComponent(appt.client?.phone || '')}`}
                    className="font-semibold text-blue-600 hover:text-blue-800 underline"
                    onClick={(e) => e.stopPropagation()}
                    data-testid={`agenda-client-link-${appt.id}`}
                  >
                    {appt.client?.first_name} {appt.client?.last_name}
                  </Link>
                  {getStatusBadge(appt.status)}
                  {appt.running_late && (
                    <Badge variant="outline" className="text-orange-600 border-orange-300 bg-orange-50">
                      <AlertTriangle className="w-3 h-3 mr-1" />
                      Llegando tarde
                    </Badge>
                  )}
                  {/* Show salesperson name for admins viewing all appointments */}
                  {appt.salesperson?.name && (
                    <Badge variant="outline" className="text-purple-600 border-purple-200 bg-purple-50 text-xs">
                      👤 {appt.salesperson.name}
                    </Badge>
                  )}
                </div>
                <div className="flex flex-wrap gap-4 text-sm text-slate-500">
                  {appt.date && (
                    <div className="flex items-center gap-1">
                      <CalendarIcon className="w-4 h-4" />
                      {format(parseISO(appt.date), 'd MMM', { locale: dateLocale })}
                    </div>
                  )}
                  {appt.time && (
                    <div className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      <span className={appt.change_time ? 'line-through text-slate-400' : ''}>
                        {appt.time}
                      </span>
                      {appt.change_time && (
                        <span className="text-blue-600 font-medium">→ {appt.change_time}</span>
                      )}
                    </div>
                  )}
                  {appt.dealer && (
                    <div className="flex items-center gap-1">
                      <MapPin className="w-4 h-4" />
                      {appt.dealer}
                    </div>
                  )}
                  {appt.client?.phone && (
                    <div className="flex items-center gap-1">
                      <Phone className="w-4 h-4" />
                      <a href={`tel:${appt.client.phone}`} className="hover:text-blue-600">
                        {appt.client.phone}
                      </a>
                    </div>
                  )}
                </div>
                {appt.notes && (
                  <p className="mt-2 text-sm text-slate-600 bg-slate-50 p-2 rounded">
                    {appt.notes}
                  </p>
                )}
              </div>
              <div className="flex gap-2 flex-shrink-0">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => sendReminderSMS(appt)}
                  title="Enviar recordatorio SMS"
                  data-testid={`send-reminder-${appt.id}`}
                >
                  <Send className="w-4 h-4" />
                </Button>
                {appt.status !== 'cumplido' && appt.status !== 'no_show' && (
                  <>
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-emerald-600 hover:bg-emerald-50"
                      onClick={() => updateStatus(appt.id, 'cumplido')}
                      title="Marcar como cumplida"
                      data-testid={`mark-complete-${appt.id}`}
                    >
                      <CheckCircle2 className="w-4 h-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-slate-600 hover:bg-slate-50"
                      onClick={() => updateStatus(appt.id, 'no_show')}
                      title="Marcar como No Show"
                      data-testid={`mark-noshow-${appt.id}`}
                    >
                      <XCircle className="w-4 h-4" />
                    </Button>
                  </>
                )}
              </div>
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
