import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Check, X, Clock, Send, Inbox, Phone, User } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

export default function SolicitudesPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [requests, setRequests] = useState({ sent: [], received: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRequests();
  }, []);

  const fetchRequests = async () => {
    try {
      const res = await axios.get(`${API}/client-requests`);
      setRequests(res.data);
    } catch (error) {
      console.error('Error fetching requests:', error);
    } finally {
      setLoading(false);
    }
  };

  const respondToRequest = async (requestId, action) => {
    try {
      await axios.put(`${API}/client-requests/${requestId}?action=${action}`);
      toast.success(action === 'approved' ? 'Solicitud aprobada' : 'Solicitud rechazada');
      fetchRequests();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al procesar solicitud');
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'pending':
        return <Badge className="bg-yellow-100 text-yellow-700"><Clock className="w-3 h-3 mr-1" /> Pendiente</Badge>;
      case 'approved':
        return <Badge className="bg-green-100 text-green-700"><Check className="w-3 h-3 mr-1" /> Aprobada</Badge>;
      case 'rejected':
        return <Badge className="bg-red-100 text-red-700"><X className="w-3 h-3 mr-1" /> Rechazada</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('es-ES', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="solicitudes-page">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Solicitudes de Clientes</h1>
        <p className="text-slate-500 mt-1">Gestiona las solicitudes de acceso a clientes</p>
      </div>

      <Tabs defaultValue="received" className="space-y-4">
        <TabsList>
          <TabsTrigger value="received" className="flex items-center gap-2">
            <Inbox className="w-4 h-4" />
            Recibidas ({requests.received.filter(r => r.status === 'pending').length})
          </TabsTrigger>
          <TabsTrigger value="sent" className="flex items-center gap-2">
            <Send className="w-4 h-4" />
            Enviadas ({requests.sent.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="received">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Solicitudes Recibidas</CardTitle>
            </CardHeader>
            <CardContent>
              {requests.received.length === 0 ? (
                <p className="text-slate-400 text-center py-8">No tienes solicitudes recibidas</p>
              ) : (
                <div className="space-y-3">
                  {requests.received.map((req) => (
                    <div key={req.id} className="border rounded-lg p-4 hover:bg-slate-50">
                      <div className="flex items-start justify-between">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <User className="w-4 h-4 text-blue-500" />
                            <span className="font-medium">{req.client_name}</span>
                            {getStatusBadge(req.status)}
                          </div>
                          <div className="flex items-center gap-2 text-sm text-slate-500">
                            <Phone className="w-3 h-3" />
                            {req.client_phone}
                          </div>
                          <p className="text-sm text-slate-600">
                            Solicitado por: <span className="font-medium text-blue-600">{req.requester_name}</span>
                          </p>
                          <p className="text-xs text-slate-400">{formatDate(req.created_at)}</p>
                        </div>
                        {req.status === 'pending' && (
                          <div className="flex gap-2">
                            <Button 
                              size="sm" 
                              className="bg-green-600 hover:bg-green-700"
                              onClick={() => respondToRequest(req.id, 'approved')}
                            >
                              <Check className="w-4 h-4 mr-1" /> Aprobar
                            </Button>
                            <Button 
                              size="sm" 
                              variant="outline"
                              className="text-red-600 hover:bg-red-50"
                              onClick={() => respondToRequest(req.id, 'rejected')}
                            >
                              <X className="w-4 h-4 mr-1" /> Rechazar
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="sent">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Solicitudes Enviadas</CardTitle>
            </CardHeader>
            <CardContent>
              {requests.sent.length === 0 ? (
                <p className="text-slate-400 text-center py-8">No has enviado solicitudes</p>
              ) : (
                <div className="space-y-3">
                  {requests.sent.map((req) => (
                    <div key={req.id} className="border rounded-lg p-4 hover:bg-slate-50">
                      <div className="flex items-start justify-between">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <User className="w-4 h-4 text-blue-500" />
                            <span className="font-medium">{req.client_name}</span>
                            {getStatusBadge(req.status)}
                          </div>
                          <div className="flex items-center gap-2 text-sm text-slate-500">
                            <Phone className="w-3 h-3" />
                            {req.client_phone}
                          </div>
                          <p className="text-sm text-slate-600">
                            Propietario: <span className="font-medium">{req.owner_name}</span>
                          </p>
                          <p className="text-xs text-slate-400">{formatDate(req.created_at)}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
