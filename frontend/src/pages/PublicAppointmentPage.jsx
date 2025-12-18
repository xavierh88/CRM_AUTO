import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast, Toaster } from 'sonner';
import { Calendar, Clock, MapPin, CheckCircle2, AlertCircle, Car, Loader2, CalendarX, RefreshCw } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PublicAppointmentPage() {
  const { token } = useParams();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [appointmentInfo, setAppointmentInfo] = useState(null);
  const [clientInfo, setClientInfo] = useState(null);
  const [dealers, setDealers] = useState([]);
  const [error, setError] = useState(null);
  const [mode, setMode] = useState('view'); // 'view', 'reschedule', 'late', 'cancelled', 'confirmed'
  
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
      
      if (response.data.appointment.status === 'cancelado') {
        setMode('cancelled');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Link inválido o expirado');
    } finally {
      setLoading(false);
    }
  };

  const handleReschedule = async (e) => {
    e.preventDefault();
    
    if (!newDate || !newTime) {
      toast.error('Por favor seleccione fecha y hora');
      return;
    }

    setSubmitting(true);
    
    try {
      await axios.put(`${API}/public/appointment/${token}/reschedule`, {
        date: newDate,
        time: newTime,
        dealer: newDealer || appointmentInfo.dealer
      });

      toast.success('¡Cita reprogramada exitosamente!');
      setMode('confirmed');
      
      // Update local state
      setAppointmentInfo(prev => ({
        ...prev,
        date: newDate,
        time: newTime,
        dealer: newDealer || prev.dealer,
        status: 'reagendado'
      }));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al reprogramar la cita');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCancel = async () => {
    if (!window.confirm('¿Está seguro que desea cancelar su cita?')) return;

    setSubmitting(true);
    
    try {
      await axios.put(`${API}/public/appointment/${token}/cancel`);
      toast.success('Cita cancelada');
      setMode('cancelled');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al cancelar la cita');
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirm = async () => {
    setSubmitting(true);
    
    try {
      await axios.put(`${API}/public/appointment/${token}/confirm`);
      toast.success('¡Cita confirmada!');
      setMode('confirmed');
      setAppointmentInfo(prev => ({ ...prev, status: 'confirmado' }));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al confirmar la cita');
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Por definir';
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('es-ES', { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric' 
    });
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
            <h2 className="text-xl font-semibold text-slate-800 mb-2">Link Inválido</h2>
            <p className="text-slate-600">{error}</p>
            <p className="text-sm text-slate-400 mt-4">
              Por favor contacte a su vendedor para obtener un nuevo link.
            </p>
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
            <h2 className="text-xl font-semibold text-slate-800 mb-2">Cita Cancelada</h2>
            <p className="text-slate-600">
              Esta cita ha sido cancelada.
            </p>
            <p className="text-sm text-slate-400 mt-4">
              Si desea programar una nueva cita, por favor contacte a su vendedor.
            </p>
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
            <h2 className="text-xl font-semibold text-slate-800 mb-2">¡Cita Confirmada!</h2>
            <p className="text-slate-600 mb-4">
              Gracias {clientInfo?.first_name}, su cita está confirmada.
            </p>
            
            <div className="bg-green-50 rounded-lg p-4 text-left space-y-2">
              <div className="flex items-center gap-2 text-slate-700">
                <Calendar className="w-4 h-4 text-green-600" />
                <span>{formatDate(appointmentInfo?.date)}</span>
              </div>
              <div className="flex items-center gap-2 text-slate-700">
                <Clock className="w-4 h-4 text-green-600" />
                <span>{appointmentInfo?.time || 'Por definir'}</span>
              </div>
              <div className="flex items-center gap-2 text-slate-700">
                <MapPin className="w-4 h-4 text-green-600" />
                <span>{appointmentInfo?.dealer || 'Por definir'}</span>
              </div>
            </div>

            <p className="text-sm text-slate-400 mt-4">
              ¡Lo esperamos!
            </p>
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
          <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <Car className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-800">DealerCRM</h1>
          <p className="text-slate-500">Gestione su cita</p>
        </div>

        {/* Current Appointment Card */}
        <Card className="mb-4">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="w-5 h-5 text-blue-600" />
              Su Cita Actual
            </CardTitle>
            <CardDescription>
              Hola <strong>{clientInfo?.first_name}</strong>, aquí están los detalles de su cita.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="bg-blue-50 rounded-lg p-4 space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <Calendar className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase">Fecha</p>
                  <p className="font-medium text-slate-800">{formatDate(appointmentInfo?.date)}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <Clock className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase">Hora</p>
                  <p className="font-medium text-slate-800">{appointmentInfo?.time || 'Por definir'}</p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center">
                  <MapPin className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase">Ubicación</p>
                  <p className="font-medium text-slate-800">{appointmentInfo?.dealer || 'Por definir'}</p>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            {mode === 'view' && (
              <div className="flex gap-2 mt-4">
                <Button 
                  onClick={handleConfirm}
                  className="flex-1"
                  disabled={submitting}
                >
                  {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : (
                    <>
                      <CheckCircle2 className="w-4 h-4 mr-1" />
                      Confirmar
                    </>
                  )}
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => setMode('reschedule')}
                  className="flex-1"
                >
                  <RefreshCw className="w-4 h-4 mr-1" />
                  Reprogramar
                </Button>
                <Button 
                  variant="outline" 
                  onClick={handleCancel}
                  className="text-red-600 hover:bg-red-50"
                  disabled={submitting}
                >
                  <CalendarX className="w-4 h-4" />
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Reschedule Form */}
        {mode === 'reschedule' && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <RefreshCw className="w-5 h-5 text-amber-600" />
                Reprogramar Cita
              </CardTitle>
              <CardDescription>
                Seleccione una nueva fecha y hora para su cita.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleReschedule} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="new-date">Nueva Fecha</Label>
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
                  <Label htmlFor="new-time">Nueva Hora</Label>
                  <Select value={newTime} onValueChange={setNewTime}>
                    <SelectTrigger>
                      <SelectValue placeholder="Seleccione hora" />
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
                    <Label htmlFor="new-dealer">Ubicación (opcional)</Label>
                    <Select value={newDealer} onValueChange={setNewDealer}>
                      <SelectTrigger>
                        <SelectValue placeholder="Mantener ubicación actual" />
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
                      'Confirmar Nueva Fecha'
                    )}
                  </Button>
                  <Button 
                    type="button"
                    variant="outline" 
                    onClick={() => setMode('view')}
                  >
                    Cancelar
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Footer */}
        <p className="text-center text-xs text-slate-400 mt-6">
          Si tiene preguntas, contacte a su vendedor.
        </p>
      </div>
    </div>
  );
}
