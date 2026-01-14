import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast, Toaster } from 'sonner';
import { Calendar, Clock, MapPin, CheckCircle2, AlertCircle, Car, Loader2, CalendarX, RefreshCw, Globe } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Translations
const translations = {
  en: {
    title: "CARPLUS AUTOSALE",
    subtitle: "Manage your appointment",
    yourAppointment: "Your Appointment",
    hello: "Hello",
    appointmentDetails: "here are your appointment details.",
    date: "DATE",
    time: "TIME",
    location: "LOCATION",
    toBeConfirmed: "To be confirmed",
    confirm: "Confirm",
    runningLate: "Running Late",
    reschedule: "Reschedule",
    cancel: "Cancel",
    // Late form
    lateTitle: "Running Late",
    lateDescription: "Select your new arrival time. The salesperson will be notified automatically.",
    originalAppointment: "Your original appointment:",
    at: "at",
    whatTimeArrive: "What time will you arrive?",
    selectNewTime: "Select new time",
    notifySalesperson: "Notify Salesperson",
    // Reschedule form
    rescheduleTitle: "Reschedule Appointment",
    rescheduleDescription: "Select a new date and time for your appointment.",
    newDate: "New Date",
    newTime: "New Time",
    selectTime: "Select time",
    locationOptional: "Location (optional)",
    keepCurrentLocation: "Keep current location",
    confirmNewDate: "Confirm New Date",
    // Messages
    invalidLink: "Invalid Link",
    invalidLinkDesc: "Invalid or expired link",
    contactSalesperson: "Please contact your salesperson to get a new link.",
    appointmentCancelled: "Appointment Cancelled",
    appointmentCancelledDesc: "This appointment has been cancelled.",
    toScheduleNew: "If you want to schedule a new appointment, please contact your salesperson.",
    appointmentConfirmed: "Appointment Confirmed!",
    thankYou: "Thank you",
    yourAppointmentConfirmed: "your appointment is confirmed.",
    seeYouThere: "We'll see you there!",
    questions: "If you have questions, contact your salesperson.",
    // Language
    languagePreference: "Language Preference",
    languageNote: "This also indicates your preferred language for the appointment",
    english: "English",
    spanish: "Spanish"
  },
  es: {
    title: "CARPLUS AUTOSALE",
    subtitle: "Gestione su cita",
    yourAppointment: "Su Cita",
    hello: "Hola",
    appointmentDetails: "aquí están los detalles de su cita.",
    date: "FECHA",
    time: "HORA",
    location: "UBICACIÓN",
    toBeConfirmed: "Por confirmar",
    confirm: "Confirmar",
    runningLate: "Llegaré Tarde",
    reschedule: "Reprogramar",
    cancel: "Cancelar",
    // Late form
    lateTitle: "Llegaré Tarde",
    lateDescription: "Seleccione su nueva hora de llegada. El vendedor será notificado automáticamente.",
    originalAppointment: "Su cita original:",
    at: "a las",
    whatTimeArrive: "¿A qué hora llegará?",
    selectNewTime: "Seleccione nueva hora",
    notifySalesperson: "Notificar al Vendedor",
    // Reschedule form
    rescheduleTitle: "Reprogramar Cita",
    rescheduleDescription: "Seleccione una nueva fecha y hora para su cita.",
    newDate: "Nueva Fecha",
    newTime: "Nueva Hora",
    selectTime: "Seleccione hora",
    locationOptional: "Ubicación (opcional)",
    keepCurrentLocation: "Mantener ubicación actual",
    confirmNewDate: "Confirmar Nueva Fecha",
    // Messages
    invalidLink: "Link Inválido",
    invalidLinkDesc: "Link inválido o expirado",
    contactSalesperson: "Por favor contacte a su vendedor para obtener un nuevo link.",
    appointmentCancelled: "Cita Cancelada",
    appointmentCancelledDesc: "Esta cita ha sido cancelada.",
    toScheduleNew: "Si desea programar una nueva cita, por favor contacte a su vendedor.",
    appointmentConfirmed: "¡Cita Confirmada!",
    thankYou: "Gracias",
    yourAppointmentConfirmed: "su cita está confirmada.",
    seeYouThere: "¡Lo esperamos!",
    questions: "Si tiene preguntas, contacte a su vendedor.",
    // Language
    languagePreference: "Preferencia de Idioma",
    languageNote: "Esto también indica su idioma preferido para la cita",
    english: "Inglés",
    spanish: "Español"
  }
};

export default function PublicAppointmentPage() {
  const { token } = useParams();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [appointmentInfo, setAppointmentInfo] = useState(null);
  const [clientInfo, setClientInfo] = useState(null);
  const [dealers, setDealers] = useState([]);
  const [error, setError] = useState(null);
  const [mode, setMode] = useState('view'); // 'view', 'reschedule', 'late', 'cancelled', 'confirmed'
  
  // Language - default English
  const [language, setLanguage] = useState('en');
  const t = translations[language];
  
  // Reschedule form
  const [newDate, setNewDate] = useState('');
  const [newTime, setNewTime] = useState('');
  const [newDealer, setNewDealer] = useState('');
  
  // Late arrival
  const [lateTime, setLateTime] = useState('');

  useEffect(() => {
    validateToken();
  }, [token]);

  const validateToken = async () => {
    try {
      const response = await axios.get(`${API}/public/appointment/${token}`);
      setAppointmentInfo(response.data.appointment);
      setClientInfo(response.data.client);
      setDealers(response.data.dealers || []);
      
      // Set language from appointment if available
      if (response.data.appointment?.preferred_language) {
        setLanguage(response.data.appointment.preferred_language);
      }
      
      if (response.data.appointment.status === 'cancelado') {
        setMode('cancelled');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid or expired link');
    } finally {
      setLoading(false);
    }
  };

  const handleLanguageChange = async (newLang) => {
    setLanguage(newLang);
    
    // Save language preference to backend
    try {
      await axios.put(`${API}/public/appointment/${token}/language`, {
        language: newLang
      });
    } catch (err) {
      console.error('Failed to save language preference:', err);
    }
  };

  const handleReschedule = async (e) => {
    e.preventDefault();
    
    if (!newDate || !newTime) {
      toast.error(language === 'es' ? 'Por favor seleccione fecha y hora' : 'Please select date and time');
      return;
    }

    setSubmitting(true);
    
    try {
      await axios.put(`${API}/public/appointment/${token}/reschedule`, {
        date: newDate,
        time: newTime,
        dealer: newDealer || appointmentInfo.dealer
      });

      toast.success(language === 'es' ? '¡Cita reprogramada exitosamente!' : 'Appointment rescheduled successfully!');
      setMode('confirmed');
      
      setAppointmentInfo(prev => ({
        ...prev,
        date: newDate,
        time: newTime,
        dealer: newDealer || prev.dealer,
        status: 'reagendado'
      }));
    } catch (err) {
      toast.error(err.response?.data?.detail || (language === 'es' ? 'Error al reprogramar la cita' : 'Error rescheduling appointment'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = async () => {
    const confirmMsg = language === 'es' ? '¿Está seguro que desea cancelar su cita?' : 'Are you sure you want to cancel your appointment?';
    if (!window.confirm(confirmMsg)) return;

    setSubmitting(true);
    
    try {
      await axios.put(`${API}/public/appointment/${token}/cancel`);
      toast.success(language === 'es' ? 'Cita cancelada' : 'Appointment cancelled');
      setMode('cancelled');
    } catch (err) {
      toast.error(err.response?.data?.detail || (language === 'es' ? 'Error al cancelar la cita' : 'Error cancelling appointment'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirm = async () => {
    setSubmitting(true);
    
    try {
      await axios.put(`${API}/public/appointment/${token}/confirm`);
      toast.success(language === 'es' ? '¡Cita confirmada!' : 'Appointment confirmed!');
      setMode('confirmed');
      setAppointmentInfo(prev => ({ ...prev, status: 'confirmado' }));
    } catch (err) {
      toast.error(err.response?.data?.detail || (language === 'es' ? 'Error al confirmar la cita' : 'Error confirming appointment'));
    } finally {
      setSubmitting(false);
    }
  };

  const handleLateArrival = async (e) => {
    e.preventDefault();
    
    if (!lateTime) {
      toast.error(language === 'es' ? 'Por favor seleccione la nueva hora de llegada' : 'Please select your new arrival time');
      return;
    }

    setSubmitting(true);
    
    try {
      await axios.put(`${API}/public/appointment/${token}/late`, {
        new_time: lateTime
      });

      toast.success(language === 'es' ? '¡Notificación enviada! El vendedor ha sido informado.' : 'Notification sent! The salesperson has been informed.');
      setMode('confirmed');
      setAppointmentInfo(prev => ({
        ...prev,
        time: lateTime,
        status: 'llegará tarde'
      }));
    } catch (err) {
      toast.error(err.response?.data?.detail || (language === 'es' ? 'Error al notificar' : 'Error sending notification'));
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return t.toBeConfirmed;
    const date = new Date(dateStr + 'T00:00:00');
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString(language === 'es' ? 'es-ES' : 'en-US', options);
  };

  const getMinDate = () => {
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    return tomorrow.toISOString().split('T')[0];
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-slate-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-slate-100 flex items-center justify-center p-4">
        <Card className="max-w-md w-full">
          <CardContent className="pt-6 text-center">
            <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-slate-800 mb-2">{t.invalidLink}</h2>
            <p className="text-slate-600">{t.invalidLinkDesc}</p>
            <p className="text-sm text-slate-400 mt-4">{t.contactSalesperson}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (mode === 'cancelled') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
        <Card className="max-w-md w-full">
          <CardContent className="pt-6 text-center">
            <CalendarX className="w-16 h-16 text-slate-400 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-slate-800 mb-2">{t.appointmentCancelled}</h2>
            <p className="text-slate-600">{t.appointmentCancelledDesc}</p>
            <p className="text-sm text-slate-400 mt-4">{t.toScheduleNew}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (mode === 'confirmed') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-slate-100 flex items-center justify-center p-4">
        <Card className="max-w-md w-full">
          <CardContent className="pt-6 text-center">
            <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-slate-800 mb-2">{t.appointmentConfirmed}</h2>
            <p className="text-slate-600 mb-4">
              {t.thankYou} {clientInfo?.first_name}, {t.yourAppointmentConfirmed}
            </p>
            
            <div className="bg-green-50 rounded-lg p-4 text-left space-y-2">
              <div className="flex items-center gap-2 text-slate-700">
                <Calendar className="w-4 h-4 text-green-600" />
                <span>{formatDate(appointmentInfo?.date)}</span>
              </div>
              <div className="flex items-center gap-2 text-slate-700">
                <Clock className="w-4 h-4 text-green-600" />
                <span>{appointmentInfo?.time || t.toBeConfirmed}</span>
              </div>
              <div className="flex items-center gap-2 text-slate-700">
                <MapPin className="w-4 h-4 text-green-600" />
                <span>{appointmentInfo?.dealer_address || appointmentInfo?.dealer || t.toBeConfirmed}</span>
              </div>
            </div>

            <p className="text-sm text-slate-400 mt-4">{t.seeYouThere}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-slate-100 py-8 px-4">
      <Toaster position="top-center" richColors />
      
      <div className="max-w-lg mx-auto">
        {/* Header */}
        <div className="text-center mb-6">
          <img src="/logo.png" alt="CARPLUS AUTOSALE" className="w-20 h-20 object-contain mx-auto mb-3" />
          <h1 className="text-2xl font-bold text-slate-800">{t.title}</h1>
          <p className="text-red-500 font-semibold text-sm">Friendly Brokerage</p>
          <p className="text-slate-500 mt-1">{t.subtitle}</p>
        </div>

        {/* Language Selector */}
        <Card className="mb-4">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Globe className="w-5 h-5 text-blue-600" />
                <div>
                  <p className="font-medium text-sm text-slate-700">{t.languagePreference}</p>
                  <p className="text-xs text-slate-400">{t.languageNote}</p>
                </div>
              </div>
              <Select value={language} onValueChange={handleLanguageChange}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="en">🇺🇸 {t.english}</SelectItem>
                  <SelectItem value="es">🇲🇽 {t.spanish}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Current Appointment Card */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-blue-600" />
              {t.yourAppointment}
            </CardTitle>
            <CardDescription>
              {t.hello} <strong>{clientInfo?.first_name}</strong>, {t.appointmentDetails}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="bg-blue-50 rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <Calendar className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase">{t.date}</p>
                  <p className="font-medium text-slate-800">{formatDate(appointmentInfo?.date)}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <Clock className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase">{t.time}</p>
                  <p className="font-medium text-slate-800">{appointmentInfo?.time || t.toBeConfirmed}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <MapPin className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase">{t.location}</p>
                  <p className="font-medium text-slate-800">{appointmentInfo?.dealer || t.toBeConfirmed}</p>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            {mode === 'view' && (
              <div className="space-y-2 mt-4">
                <div className="flex gap-2">
                  <Button 
                    onClick={handleConfirm}
                    className="flex-1"
                    disabled={submitting}
                  >
                    {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : (
                      <>
                        <CheckCircle2 className="w-4 h-4 mr-1" />
                        {t.confirm}
                      </>
                    )}
                  </Button>
                  <Button 
                    variant="outline" 
                    onClick={() => setMode('late')}
                    className="flex-1 text-amber-600 hover:bg-amber-50 border-amber-200"
                  >
                    <Clock className="w-4 h-4 mr-1" />
                    {t.runningLate}
                  </Button>
                </div>
                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    onClick={() => setMode('reschedule')}
                    className="flex-1"
                  >
                    <RefreshCw className="w-4 h-4 mr-1" />
                    {t.reschedule}
                  </Button>
                  <Button 
                    variant="outline" 
                    onClick={handleCancel}
                    className="text-red-600 hover:bg-red-50"
                    disabled={submitting}
                  >
                    <CalendarX className="w-4 h-4 mr-1" />
                    {t.cancel}
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Late Arrival Form */}
        {mode === 'late' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-amber-600" />
                {t.lateTitle}
              </CardTitle>
              <CardDescription>{t.lateDescription}</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleLateArrival} className="space-y-4">
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
                  <p className="font-medium">{t.originalAppointment}</p>
                  <p>{appointmentInfo?.date} {t.at} {appointmentInfo?.time}</p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="late-time">{t.whatTimeArrive}</Label>
                  <Select value={lateTime} onValueChange={setLateTime}>
                    <SelectTrigger>
                      <SelectValue placeholder={t.selectNewTime} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="09:30">9:30 AM</SelectItem>
                      <SelectItem value="10:00">10:00 AM</SelectItem>
                      <SelectItem value="10:30">10:30 AM</SelectItem>
                      <SelectItem value="11:00">11:00 AM</SelectItem>
                      <SelectItem value="11:30">11:30 AM</SelectItem>
                      <SelectItem value="12:00">12:00 PM</SelectItem>
                      <SelectItem value="12:30">12:30 PM</SelectItem>
                      <SelectItem value="13:00">1:00 PM</SelectItem>
                      <SelectItem value="13:30">1:30 PM</SelectItem>
                      <SelectItem value="14:00">2:00 PM</SelectItem>
                      <SelectItem value="14:30">2:30 PM</SelectItem>
                      <SelectItem value="15:00">3:00 PM</SelectItem>
                      <SelectItem value="15:30">3:30 PM</SelectItem>
                      <SelectItem value="16:00">4:00 PM</SelectItem>
                      <SelectItem value="16:30">4:30 PM</SelectItem>
                      <SelectItem value="17:00">5:00 PM</SelectItem>
                      <SelectItem value="17:30">5:30 PM</SelectItem>
                      <SelectItem value="18:00">6:00 PM</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex gap-2 pt-2">
                  <Button 
                    type="submit" 
                    className="flex-1 bg-amber-600 hover:bg-amber-700"
                    disabled={submitting}
                  >
                    {submitting ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      t.notifySalesperson
                    )}
                  </Button>
                  <Button 
                    type="button"
                    variant="outline" 
                    onClick={() => setMode('view')}
                  >
                    {t.cancel}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Reschedule Form */}
        {mode === 'reschedule' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <RefreshCw className="w-5 h-5 text-blue-600" />
                {t.rescheduleTitle}
              </CardTitle>
              <CardDescription>{t.rescheduleDescription}</CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleReschedule} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="new-date">{t.newDate}</Label>
                  <Input
                    id="new-date"
                    type="date"
                    min={getMinDate()}
                    value={newDate}
                    onChange={(e) => setNewDate(e.target.value)}
                    required
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="new-time">{t.newTime}</Label>
                  <Select value={newTime} onValueChange={setNewTime}>
                    <SelectTrigger>
                      <SelectValue placeholder={t.selectTime} />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="09:00">9:00 AM</SelectItem>
                      <SelectItem value="10:00">10:00 AM</SelectItem>
                      <SelectItem value="11:00">11:00 AM</SelectItem>
                      <SelectItem value="12:00">12:00 PM</SelectItem>
                      <SelectItem value="13:00">1:00 PM</SelectItem>
                      <SelectItem value="14:00">2:00 PM</SelectItem>
                      <SelectItem value="15:00">3:00 PM</SelectItem>
                      <SelectItem value="16:00">4:00 PM</SelectItem>
                      <SelectItem value="17:00">5:00 PM</SelectItem>
                      <SelectItem value="18:00">6:00 PM</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {dealers.length > 0 && (
                  <div className="space-y-2">
                    <Label htmlFor="new-dealer">{t.locationOptional}</Label>
                    <Select value={newDealer} onValueChange={setNewDealer}>
                      <SelectTrigger>
                        <SelectValue placeholder={t.keepCurrentLocation} />
                      </SelectTrigger>
                      <SelectContent>
                        {dealers.map((dealer) => (
                          <SelectItem key={dealer.id} value={dealer.name}>
                            {dealer.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                <div className="flex gap-2 pt-2">
                  <Button 
                    type="submit" 
                    className="flex-1"
                    disabled={submitting}
                  >
                    {submitting ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      t.confirmNewDate
                    )}
                  </Button>
                  <Button 
                    type="button"
                    variant="outline" 
                    onClick={() => setMode('view')}
                  >
                    {t.cancel}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Footer */}
        <p className="text-center text-xs text-slate-400 mt-6">{t.questions}</p>
      </div>
    </div>
  );
}
