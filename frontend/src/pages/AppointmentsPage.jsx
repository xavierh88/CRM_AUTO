import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Calendar } from '../components/ui/calendar';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import { format, isToday, isTomorrow, addDays, parseISO, isWithinInterval, startOfDay, endOfDay, isSameDay, startOfWeek, endOfWeek } from 'date-fns';
import { es } from 'date-fns/locale';
import {
  Calendar as CalendarIcon, Clock, MapPin, User, Send, CheckCircle2, XCircle, Phone, AlertTriangle, Bell, MessageSquare,
  ChevronDown, ChevronUp, Edit, Trash2, Eye, Plus, Search, Filter, RefreshCw,
  CheckCircle, XCircle as XCircleIcon, AlertCircle, Loader2
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AppointmentsPage() {
  const { t, i18n } = useTranslation();
  const { user, isAdmin, isBDCManager } = useAuth();
  const navigate = useNavigate();
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [filter, setFilter] = useState('all');
  const [viewMode, setViewMode] = useState('grouped');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [selectedAppointment, setSelectedAppointment] = useState(null);
  const [formData, setFormData] = useState({
    client_id: '', date: format(new Date(), 'yyyy-MM-dd'), time: '10:00',
    dealer: '', type: 'showroom', language: 'en', notes: '', status: 'agendado'
  });
  const [clients, setClients] = useState([]);
  const [submitting, setSubmitting] = useState(false);

  const fetchAppointments = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/appointments/agenda`);
      setAppointments(response.data);
    } catch (error) {
      toast.error('Failed to fetch appointments');
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchClients = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/clients?exclude_sold=false&sort_by=name`);
      setClients(response.data);
    } catch (error) {
      console.error('Failed to fetch clients:', error);
    }
  }, []);

  useEffect(() => {
    fetchAppointments();
    fetchClients();
  }, [fetchAppointments, fetchClients]);

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
      toast.success('Reminder SMS sent');
    } catch (error) {
      toast.error('Failed to send SMS');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (selectedAppointment) {
        await axios.put(`${API}/appointments/${selectedAppointment.id}`, formData);
        toast.success('Appointment updated');
      } else {
        await axios.post(`${API}/appointments`, formData);
        toast.success('Appointment created');
      }
      setShowCreateDialog(false);
      resetForm();
      fetchAppointments();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save appointment');
    } finally {
      setSubmitting(false);
    }
  };

  const resetForm = () => {
    setFormData({
      client_id: '', date: format(new Date(), 'yyyy-MM-dd'), time: '10:00',
      dealer: '', type: 'showroom', language: 'en', notes: '', status: 'agendado'
    });
    setSelectedAppointment(null);
  };

  const handleEdit = (appt) => {
    setSelectedAppointment(appt);
    setFormData({
      client_id: appt.client_id, date: appt.date, time: appt.time,
      dealer: appt.dealer, type: appt.type, language: appt.language,
      notes: appt.notes, status: appt.status
    });
    setShowCreateDialog(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this appointment?')) return;
    try {
      await axios.delete(`${API}/appointments/${id}`);
      toast.success('Appointment deleted');
      fetchAppointments();
    } catch (error) {
      toast.error('Failed to delete');
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

    if (filter !== 'all') {
      filtered = filtered.filter(a => a.status === filter);
    }

    const today = startOfDay(new Date());
    const tomorrow = addDays(today, 1);
    const weekEnd = endOfWeek(today, { weekStartsOn: 1 });

    const grouped = {
      today: filtered.filter(a => a.date && isToday(parseISO(a.date))),
      tomorrow: filtered.filter(a => a.date && isTomorrow(parseISO(a.date))),
      thisWeek: filtered.filter(a => {
        if (!a.date) return false;
        const date = parseISO(a.date);
        return isWithinInterval(date, { start: addDays(today, 2), end: weekEnd });
      }),
      later: filtered.filter(a => {
        if (!a.date) return false;
        const date = parseISO(a.date);
        return date > weekEnd;
      }),
      unconfigured: filtered.filter(a => !a.date || a.status === 'sin_configurar')
    };

    return grouped;
  };

  const getStatusBadge = (status) => {
    const variants = {
      agendado: 'default',
      sin_configurar: 'secondary',
      cambio_hora: 'outline',
      tres_semanas: 'destructive',
      no_show: 'outline',
      cumplido: 'success',
    };
    const labels = {
      agendado: t('status.agendado') || 'Scheduled',
      sin_configurar: t('status.sin_configurar') || 'Not Configured',
      cambio_hora: t('status.cambio_hora') || 'Time Changed',
      tres_semanas: t('status.tres_semanas') || '3 Weeks',
      no_show: t('status.no_show') || 'No Show',
      cumplido: t('status.cumplido') || 'Completed',
    };
    return (
      <Badge variant={variants[status] || 'outline'} className="capitalize">
        {labels[status] || status}
      </Badge>
    );
  };

  const stats = {
    total: appointments.length,
    today: appointments.filter(a => a.date && isToday(parseISO(a.date))).length,
    pending: appointments.filter(a => a.status === 'agendado' || a.status === 'sin_configurar').length,
    completed: appointments.filter(a => a.status === 'cumplido').length,
    noShow: appointments.filter(a => a.status === 'no_show').length,
  };

  const grouped = getFilteredAppointments();
  const selectedDateAppts = getSelectedDateAppointments();
  const dateLocale = i18n.language === 'es' ? es : undefined;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="appointments-page">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('appointments.title')}</h1>
          <p className="text-muted-foreground mt-1">{t('appointments.subtitle') || 'Manage your appointments'}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Select value={viewMode} onValueChange={setViewMode}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="grouped">{t('appointments.groupedView') || 'Grouped View'}</SelectItem>
              <SelectItem value="calendar">{t('appointments.calendarView') || 'Calendar View'}</SelectItem>
              <SelectItem value="list">{t('appointments.listView') || 'List View'}</SelectItem>
            </SelectContent>
          </Select>
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-48" data-testid="status-filter">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('common.all') || 'All Statuses'}</SelectItem>
              <SelectItem value="agendado">{t('status.agendado')}</SelectItem>
              <SelectItem value="sin_configurar">{t('status.sin_configurar')}</SelectItem>
              <SelectItem value="cambio_hora">{t('status.cambio_hora')}</SelectItem>
              <SelectItem value="tres_semanas">{t('status.tres_semanas')}</SelectItem>
              <SelectItem value="no_show">{t('status.no_show')}</SelectItem>
              <SelectItem value="cumplido">{t('status.cumplido')}</SelectItem>
            </SelectContent>
          </Select>
          <Button onClick={() => { resetForm(); setShowCreateDialog(true); }}>
            <Plus className="w-4 h-4 mr-2" />
            {t('appointments.schedule')}
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">Total</p>
            <p className="text-2xl font-bold">{stats.total}</p>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-blue-500">
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">{t('appointments.today')}</p>
            <p className="text-2xl font-bold text-blue-600">{stats.today}</p>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-amber-500">
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">{t('common.pending')}</p>
            <p className="text-2xl font-bold text-amber-600">{stats.pending}</p>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-emerald-500">
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">{t('status.cumplido')}</p>
            <p className="text-2xl font-bold text-emerald-600">{stats.completed}</p>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-red-500">
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground uppercase tracking-wide">{t('status.no_show')}</p>
            <p className="text-2xl font-bold text-red-600">{stats.noShow}</p>
          </CardContent>
        </Card>
      </div>

      {/* Calendar View */}
      {viewMode === 'calendar' && (
        <Card>
          <CardContent className="p-4">
            <Calendar
              mode="single"
              selected={selectedDate}
              onSelect={setSelectedDate}
              locale={dateLocale}
              initialFocus
            />
          </CardContent>
        </Card>
      )}

      {/* Grouped View */}
      {viewMode === 'grouped' && (
        <>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg font-semibold">{t('appointments.today')}</CardTitle>
            </CardHeader>
            <CardContent>
              {grouped.today.length > 0 ? (
                <div className="space-y-3">
                  {grouped.today.map((appt) => (
                    <AppointmentCard key={appt.id} appt={appt} onEdit={handleEdit} onDelete={handleDelete} onStatusChange={updateStatus} onSendSMS={sendReminderSMS} />
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground text-center py-8">No appointments today</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg font-semibold">{t('appointments.tomorrow')}</CardTitle>
            </CardHeader>
            <CardContent>
              {grouped.tomorrow.length > 0 ? (
                <div className="space-y-3">
                  {grouped.tomorrow.map((appt) => (
                    <AppointmentCard key={appt.id} appt={appt} onEdit={handleEdit} onDelete={handleDelete} onStatusChange={updateStatus} onSendSMS={sendReminderSMS} />
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground text-center py-8">No appointments tomorrow</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg font-semibold">{t('appointments.thisWeek')}</CardTitle>
            </CardHeader>
            <CardContent>
              {grouped.thisWeek.length > 0 ? (
                <div className="space-y-3">
                  {grouped.thisWeek.map((appt) => (
                    <AppointmentCard key={appt.id} appt={appt} onEdit={handleEdit} onDelete={handleDelete} onStatusChange={updateStatus} onSendSMS={sendReminderSMS} />
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground text-center py-8">No appointments this week</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-lg font-semibold">{t('appointments.unconfigured')}</CardTitle>
            </CardHeader>
            <CardContent>
              {grouped.unconfigured.length > 0 ? (
                <div className="space-y-3">
                  {grouped.unconfigured.map((appt) => (
                    <AppointmentCard key={appt.id} appt={appt} onEdit={handleEdit} onDelete={handleDelete} onStatusChange={updateStatus} onSendSMS={sendReminderSMS} />
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground text-center py-8">All appointments configured</p>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* List View */}
      {viewMode === 'list' && (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="p-4 text-left font-medium text-muted-foreground">Date</th>
                    <th className="p-4 text-left font-medium text-muted-foreground">Time</th>
                    <th className="p-4 text-left font-medium text-muted-foreground">Client</th>
                    <th className="p-4 text-left font-medium text-muted-foreground">Dealer</th>
                    <th className="p-4 text-left font-medium text-muted-foreground">Type</th>
                    <th className="p-4 text-left font-medium text-muted-foreground">Status</th>
                    <th className="p-4 text-right font-medium text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {appointments.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="p-12 text-center text-muted-foreground">No appointments</td>
                    </tr>
                  ) : (
                    appointments
                      .filter(a => filter === 'all' || a.status === filter)
                      .sort((a, b) => (a.date || '').localeCompare(b.date || '') || (a.time || '').localeCompare(b.time || ''))
                      .map((appt) => (
                        <tr key={appt.id} className="border-b border-border/50 hover:bg-muted/50">
                          <td className="p-4">{appt.date ? format(parseISO(appt.date), 'PPP', { locale: dateLocale }) : 'Not set'}</td>
                          <td className="p-4">{appt.time || '-'}</td>
                          <td className="p-4">
                            <p className="font-medium">{appt.client_name || 'Unknown'}</p>
                            <p className="text-sm text-muted-foreground font-mono">{appt.client_phone || ''}</p>
                          </td>
                          <td className="p-4">{appt.dealer || '-'}</td>
                          <td className="p-4 capitalize">{appt.type || '-'}</td>
                          <td className="p-4">{getStatusBadge(appt.status)}</td>
                          <td className="p-4 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <Button variant="ghost" size="sm" onClick={() => handleEdit(appt)}><Edit className="w-4 h-4" /></Button>
                              <Button variant="ghost" size="sm" onClick={() => sendReminderSMS(appt)}><Send className="w-4 h-4" /></Button>
                              <Button variant="ghost" size="sm" onClick={() => handleDelete(appt.id)} className="text-destructive"><Trash2 className="w-4 h-4" /></Button>
                            </div>
                          </td>
                        </tr>
                      ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Create/Edit Appointment Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedAppointment ? 'Edit Appointment' : t('appointments.schedule')}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="p-4 space-y-4">
            <div>
              <Label htmlFor="client_id">Client *</Label>
              <Select value={formData.client_id} onValueChange={(v) => setFormData({...formData, client_id: v})}>
                <SelectTrigger>
                  <SelectValue placeholder="Select client" />
                </SelectTrigger>
                <SelectContent>
                  {clients.map(c => (
                    <SelectItem key={c.id} value={c.id}>{c.first_name} {c.last_name} - {c.phone}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="date">Date *</Label>
                <Input id="date" type="date" value={formData.date} onChange={(e) => setFormData({...formData, date: e.target.value})} min={format(new Date(), 'yyyy-MM-dd')} />
              </div>
              <div>
                <Label htmlFor="time">Time *</Label>
                <Input id="time" type="time" value={formData.time} onChange={(e) => setFormData({...formData, time: e.target.value})} />
              </div>
            </div>
            <div>
              <Label htmlFor="dealer">Dealer</Label>
              <Input id="dealer" value={formData.dealer} onChange={(e) => setFormData({...formData, dealer: e.target.value})} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="type">Type</Label>
                <Select value={formData.type} onValueChange={(v) => setFormData({...formData, type: v})}>
                  <SelectTrigger><SelectValue placeholder="Type" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="showroom">Showroom</SelectItem>
                    <SelectItem value="test_drive">Test Drive</SelectItem>
                    <SelectItem value="delivery">Delivery</SelectItem>
                    <SelectItem value="service">Service</SelectItem>
                    <SelectItem value="follow_up">Follow Up</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="language">Language</Label>
                <Select value={formData.language} onValueChange={(v) => setFormData({...formData, language: v})}>
                  <SelectTrigger><SelectValue placeholder="Language" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">English</SelectItem>
                    <SelectItem value="es">Español</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="notes">Notes</Label>
              <textarea id="notes" className="w-full min-h-[80px] p-3 border border-border rounded-lg bg-background text-foreground" value={formData.notes} onChange={(e) => setFormData({...formData, notes: e.target.value})} />
            </div>
            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button type="button" variant="outline" onClick={() => { setShowCreateDialog(false); resetForm(); }}>
                {t('common.cancel')}
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : t('common.save')}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function AppointmentCard({ appt, onEdit, onDelete, onStatusChange, onSendSMS }) {
  const { t } = useTranslation();
  const statusColors = {
    agendado: 'border-l-emerald-500 bg-emerald-500/5',
    sin_configurar: 'border-l-amber-500 bg-amber-500/5',
    cambio_hora: 'border-l-blue-500 bg-blue-500/5',
    tres_semanas: 'border-l-rose-500 bg-rose-500/5',
    no_show: 'border-l-slate-500 bg-slate-500/5',
    cumplido: 'border-l-amber-500 bg-amber-500/5',
  };

  const getStatusBadge = (status) => {
    const variants = {
      agendado: 'default',
      sin_configurar: 'secondary',
      cambio_hora: 'outline',
      tres_semanas: 'destructive',
      no_show: 'outline',
      cumplido: 'success',
    };
    const labels = {
      agendado: t('status.agendado') || 'Scheduled',
      sin_configurar: t('status.sin_configurar') || 'Not Configured',
      cambio_hora: t('status.cambio_hora') || 'Time Changed',
      tres_semanas: t('status.tres_semanas') || '3 Weeks',
      no_show: t('status.no_show') || 'No Show',
      cumplido: t('status.cumplido') || 'Completed',
    };
    return (
      <Badge variant={variants[status] || 'outline'} className="text-xs capitalize">
        {labels[status] || status}
      </Badge>
    );
  };

  return (
    <div className={`p-4 border-l-4 rounded-r-lg transition-colors ${statusColors[appt.status] || 'border-l-slate-500'}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="font-medium">{appt.client_name || 'Unknown Client'}</span>
            <span className="text-sm text-muted-foreground font-mono">{appt.client_phone || ''}</span>
            {getStatusBadge(appt.status)}
          </div>
          <div className="flex items-center gap-4 mt-2 text-sm text-muted-foreground flex-wrap">
            <span className="flex items-center gap-1"><Clock className="w-3 h-3" />{appt.time || 'TBD'}</span>
            <span className="flex items-center gap-1"><MapPin className="w-3 h-3" />{appt.dealer || 'TBD'}</span>
            <span className="flex items-center gap-1 capitalize">{appt.type || 'showroom'}</span>
          </div>
          {appt.notes && <p className="text-sm text-muted-foreground mt-2 truncate">{appt.notes}</p>}
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <Button variant="ghost" size="sm" onClick={() => onEdit(appt)}><Edit className="w-4 h-4" /></Button>
          <Button variant="ghost" size="sm" onClick={() => onSendSMS(appt)}><Send className="w-4 h-4" /></Button>
          <Button variant="ghost" size="sm" onClick={() => onDelete(appt.id)} className="text-destructive"><Trash2 className="w-4 h-4" /></Button>
        </div>
      </div>
    </div>
  );
}