import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Calendar } from '../components/ui/calendar';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { Calendar as CalendarIcon, Clock, MapPin, User, Send, CheckCircle2, XCircle } from 'lucide-react';
import { format, isToday, isTomorrow, addDays, parseISO, isWithinInterval, startOfDay, endOfDay } from 'date-fns';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AgendaPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [filter, setFilter] = useState('all');

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
      toast.success('Reminder SMS sent (mocked)');
    } catch (error) {
      toast.error('Failed to send SMS');
    }
  };

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

  const grouped = getFilteredAppointments();

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
          <p className="text-slate-500 mt-1">Manage your appointments</p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-48" data-testid="status-filter">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Calendar */}
        <Card className="dashboard-card lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <CalendarIcon className="w-5 h-5 text-blue-600" />
              Calendar
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Calendar
              mode="single"
              selected={selectedDate}
              onSelect={setSelectedDate}
              className="rounded-md border"
              modifiers={{
                hasAppointment: appointments
                  .filter(a => a.date)
                  .map(a => parseISO(a.date))
              }}
              modifiersClassNames={{
                hasAppointment: 'bg-blue-100 text-blue-900 font-semibold'
              }}
            />
          </CardContent>
        </Card>

        {/* Appointments List */}
        <div className="lg:col-span-2 space-y-6">
          {/* Today */}
          <AppointmentSection
            title="Today"
            appointments={grouped.today}
            getStatusBadge={getStatusBadge}
            updateStatus={updateStatus}
            sendReminderSMS={sendReminderSMS}
            emptyMessage="No appointments today"
          />

          {/* Tomorrow */}
          <AppointmentSection
            title="Tomorrow"
            appointments={grouped.tomorrow}
            getStatusBadge={getStatusBadge}
            updateStatus={updateStatus}
            sendReminderSMS={sendReminderSMS}
            emptyMessage="No appointments tomorrow"
          />

          {/* This Week */}
          <AppointmentSection
            title="Next 7 Days"
            appointments={grouped.thisWeek}
            getStatusBadge={getStatusBadge}
            updateStatus={updateStatus}
            sendReminderSMS={sendReminderSMS}
            emptyMessage="No upcoming appointments"
          />

          {/* Not Configured */}
          {grouped.unconfigured.length > 0 && (
            <AppointmentSection
              title="Not Configured"
              appointments={grouped.unconfigured}
              getStatusBadge={getStatusBadge}
              updateStatus={updateStatus}
              sendReminderSMS={sendReminderSMS}
              emptyMessage=""
              isWarning
            />
          )}
        </div>
      </div>
    </div>
  );
}

function AppointmentSection({ title, appointments, getStatusBadge, updateStatus, sendReminderSMS, emptyMessage, isWarning }) {
  const { t } = useTranslation();

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
    <Card className={`dashboard-card ${isWarning ? 'border-orange-200' : ''}`}>
      <CardHeader>
        <CardTitle className={`text-lg ${isWarning ? 'text-orange-600' : ''}`}>
          {title} ({appointments.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {appointments.map((appt) => (
          <div
            key={appt.id}
            className={`agenda-item status-${appt.status} bg-white rounded-lg border p-4`}
            data-testid={`appointment-${appt.id}`}
          >
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-3 mb-2">
                  <User className="w-4 h-4 text-slate-400" />
                  <span className="font-semibold text-slate-900">
                    {appt.client?.first_name} {appt.client?.last_name}
                  </span>
                  {getStatusBadge(appt.status)}
                </div>
                <div className="flex flex-wrap gap-4 text-sm text-slate-500">
                  {appt.date && (
                    <div className="flex items-center gap-1">
                      <CalendarIcon className="w-4 h-4" />
                      {format(parseISO(appt.date), 'MMM d, yyyy')}
                    </div>
                  )}
                  {appt.time && (
                    <div className="flex items-center gap-1">
                      <Clock className="w-4 h-4" />
                      {appt.time}
                      {appt.change_time && (
                        <span className="text-blue-600 ml-1">→ {appt.change_time}</span>
                      )}
                    </div>
                  )}
                  {appt.dealer && (
                    <div className="flex items-center gap-1">
                      <MapPin className="w-4 h-4" />
                      {appt.dealer}
                    </div>
                  )}
                </div>
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => sendReminderSMS(appt)}
                  title="Send reminder"
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
                      title={t('appointments.markCompleted')}
                      data-testid={`mark-complete-${appt.id}`}
                    >
                      <CheckCircle2 className="w-4 h-4" />
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      className="text-slate-600 hover:bg-slate-50"
                      onClick={() => updateStatus(appt.id, 'no_show')}
                      title={t('appointments.markNoShow')}
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
