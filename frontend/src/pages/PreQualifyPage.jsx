import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { toast } from 'sonner';
import { 
  FileText, Clock, CheckCircle2, AlertCircle, User, Phone, Mail, 
  MapPin, Briefcase, DollarSign, Calendar, ExternalLink, Plus,
  MessageSquare, Eye, EyeOff, UserPlus, RefreshCw, Search, Shield
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

export default function PreQualifyPage() {
  const navigate = useNavigate();
  const [submissions, setSubmissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedSubmission, setSelectedSubmission] = useState(null);
  const [detailData, setDetailData] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [filter, setFilter] = useState('all');
  const [showSSN, setShowSSN] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);

  useEffect(() => {
    fetchSubmissions();
    fetchCurrentUser();
  }, []);

  const fetchCurrentUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setCurrentUser(response.data);
    } catch (error) {
      console.error('Error fetching user');
    }
  };

  const isAdmin = currentUser?.role === 'admin';

  const fetchSubmissions = async () => {
    try {
      const response = await axios.get(`${API}/prequalify/submissions`);
      setSubmissions(response.data);
    } catch (error) {
      toast.error('Error al cargar las solicitudes');
    } finally {
      setLoading(false);
    }
  };

  const openDetail = async (submission) => {
    setSelectedSubmission(submission);
    try {
      const response = await axios.get(`${API}/prequalify/submissions/${submission.id}`);
      setDetailData(response.data);
    } catch (error) {
      toast.error('Error al cargar detalles');
    }
  };

  const handleCreateClient = async () => {
    if (!selectedSubmission) return;
    try {
      const response = await axios.post(`${API}/prequalify/submissions/${selectedSubmission.id}/create-client`);
      toast.success(`Cliente creado: ${response.data.client_id}`);
      setSelectedSubmission(null);
      setDetailData(null);
      fetchSubmissions();
      // Navigate to the new client
      navigate(`/clients?search=${selectedSubmission.phone}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al crear cliente');
    }
  };

  const handleAddToNotes = async (recordId) => {
    if (!selectedSubmission) return;
    try {
      await axios.post(`${API}/prequalify/submissions/${selectedSubmission.id}/add-to-notes?record_id=${recordId}`);
      toast.success('Datos agregados a las notas del record');
      setSelectedSubmission(null);
      setDetailData(null);
      fetchSubmissions();
    } catch (error) {
      toast.error('Error al agregar a notas');
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'pending':
        return <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200"><Clock className="w-3 h-3 mr-1" /> Pendiente</Badge>;
      case 'reviewed':
        return <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200"><Eye className="w-3 h-3 mr-1" /> Revisado</Badge>;
      case 'converted':
        return <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-200"><CheckCircle2 className="w-3 h-3 mr-1" /> Convertido</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  const filteredSubmissions = submissions.filter(sub => {
    const matchesSearch = searchTerm === '' || 
      `${sub.firstName} ${sub.lastName}`.toLowerCase().includes(searchTerm.toLowerCase()) ||
      sub.phone?.includes(searchTerm) ||
      sub.email?.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesFilter = filter === 'all' || sub.status === filter;
    
    return matchesSearch && matchesFilter;
  });

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
          <FileText className="w-6 h-6 text-blue-600" />
          Pre-Qualify Submissions
        </h1>
        <p className="text-slate-500">Formularios de pre-calificación recibidos desde el sitio web</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card className="bg-gradient-to-br from-blue-50 to-white">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Total</p>
                <p className="text-2xl font-bold text-blue-600">{submissions.length}</p>
              </div>
              <FileText className="w-8 h-8 text-blue-200" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-amber-50 to-white">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Pendientes</p>
                <p className="text-2xl font-bold text-amber-600">{submissions.filter(s => s.status === 'pending').length}</p>
              </div>
              <Clock className="w-8 h-8 text-amber-200" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-emerald-50 to-white">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Convertidos</p>
                <p className="text-2xl font-bold text-emerald-600">{submissions.filter(s => s.status === 'converted').length}</p>
              </div>
              <CheckCircle2 className="w-8 h-8 text-emerald-200" />
            </div>
          </CardContent>
        </Card>
        <Card className="bg-gradient-to-br from-purple-50 to-white">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-500">Con Cliente Existente</p>
                <p className="text-2xl font-bold text-purple-600">{submissions.filter(s => s.matched_client_id).length}</p>
              </div>
              <User className="w-8 h-8 text-purple-200" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 w-4 h-4" />
              <Input
                placeholder="Buscar por nombre, teléfono o email..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <div className="flex gap-2">
              <Button variant={filter === 'all' ? 'default' : 'outline'} size="sm" onClick={() => setFilter('all')}>
                Todos
              </Button>
              <Button variant={filter === 'pending' ? 'default' : 'outline'} size="sm" onClick={() => setFilter('pending')}>
                Pendientes
              </Button>
              <Button variant={filter === 'reviewed' ? 'default' : 'outline'} size="sm" onClick={() => setFilter('reviewed')}>
                Revisados
              </Button>
              <Button variant={filter === 'converted' ? 'default' : 'outline'} size="sm" onClick={() => setFilter('converted')}>
                Convertidos
              </Button>
              <Button variant="outline" size="sm" onClick={fetchSubmissions}>
                <RefreshCw className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Submissions Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Fecha/Hora</TableHead>
                <TableHead>Nombre</TableHead>
                <TableHead>Teléfono</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Down Payment</TableHead>
                <TableHead>Estado</TableHead>
                <TableHead>Cliente</TableHead>
                <TableHead className="text-right">Acciones</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredSubmissions.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center py-8 text-slate-500">
                    No hay solicitudes de pre-qualify
                  </TableCell>
                </TableRow>
              ) : (
                filteredSubmissions.map((sub) => (
                  <TableRow key={sub.id} className="hover:bg-slate-50">
                    <TableCell className="text-xs text-slate-500">
                      {new Date(sub.created_at).toLocaleString('es-ES', {
                        day: '2-digit', month: '2-digit', year: 'numeric',
                        hour: '2-digit', minute: '2-digit'
                      })}
                    </TableCell>
                    <TableCell className="font-medium">{sub.firstName} {sub.lastName}</TableCell>
                    <TableCell>
                      <span className="flex items-center gap-1 text-sm">
                        <Phone className="w-3 h-3 text-slate-400" />
                        {sub.phone}
                      </span>
                    </TableCell>
                    <TableCell className="text-sm text-slate-500">{sub.email}</TableCell>
                    <TableCell>
                      {sub.estimatedDownPayment && (
                        <span className="text-emerald-600 font-medium">${sub.estimatedDownPayment}</span>
                      )}
                    </TableCell>
                    <TableCell>{getStatusBadge(sub.status)}</TableCell>
                    <TableCell>
                      {sub.matched_client_id ? (
                        <Button 
                          variant="link" 
                          size="sm" 
                          className="p-0 h-auto text-purple-600"
                          onClick={() => navigate(`/clients?search=${sub.phone}`)}
                        >
                          <User className="w-3 h-3 mr-1" />
                          {sub.matched_client_name}
                        </Button>
                      ) : (
                        <span className="text-slate-400 text-sm">Sin coincidencia</span>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button size="sm" variant="outline" onClick={() => openDetail(sub)}>
                        <Eye className="w-4 h-4 mr-1" /> Ver
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Detail Dialog */}
      <Dialog open={!!selectedSubmission} onOpenChange={() => { setSelectedSubmission(null); setDetailData(null); }}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-600" />
              Detalle de Pre-Qualify
            </DialogTitle>
            <DialogDescription>
              Recibido el {selectedSubmission && new Date(selectedSubmission.created_at).toLocaleString('es-ES')}
            </DialogDescription>
          </DialogHeader>

          {detailData && (
            <div className="space-y-6">
              {/* Personal Info */}
              <div className="grid grid-cols-2 gap-4 p-4 bg-slate-50 rounded-lg">
                <div>
                  <label className="text-xs text-slate-500">Nombre Completo</label>
                  <p className="font-medium">{detailData.submission.firstName} {detailData.submission.lastName}</p>
                </div>
                <div>
                  <label className="text-xs text-slate-500">Teléfono</label>
                  <p className="font-medium flex items-center gap-1">
                    <Phone className="w-4 h-4 text-slate-400" />
                    {detailData.submission.phone}
                  </p>
                </div>
                <div>
                  <label className="text-xs text-slate-500">Email</label>
                  <p className="font-medium flex items-center gap-1">
                    <Mail className="w-4 h-4 text-slate-400" />
                    {detailData.submission.email}
                  </p>
                </div>
                <div>
                  <label className="text-xs text-slate-500">Fecha de Nacimiento</label>
                  <p className="font-medium">{detailData.submission.dateOfBirth || 'N/A'}</p>
                </div>
                <div>
                  <label className="text-xs text-slate-500">Tipo de ID</label>
                  <p className="font-medium">{detailData.submission.idType || 'N/A'}</p>
                </div>
                <div>
                  <label className="text-xs text-slate-500">ID/Pasaporte</label>
                  <p className="font-medium">{detailData.submission.idNumber || 'N/A'}</p>
                </div>
              </div>

              {/* Address Info */}
              <div className="p-4 bg-blue-50 rounded-lg">
                <h4 className="font-medium text-blue-700 mb-2 flex items-center gap-1">
                  <MapPin className="w-4 h-4" /> Dirección
                </h4>
                <p className="text-sm">
                  {detailData.submission.address}{detailData.submission.apartment ? `, Apt ${detailData.submission.apartment}` : ''}, {detailData.submission.city}, {detailData.submission.state} {detailData.submission.zipCode}
                </p>
                <div className="grid grid-cols-3 gap-4 mt-2 text-sm">
                  <div>
                    <span className="text-blue-500">Tipo:</span> {detailData.submission.housingType || 'N/A'}
                  </div>
                  <div>
                    <span className="text-blue-500">Renta:</span> {detailData.submission.rentAmount || 'N/A'}
                  </div>
                  <div>
                    <span className="text-blue-500">Tiempo:</span> {
                      (detailData.submission.timeAtAddressYears || detailData.submission.timeAtAddressMonths)
                        ? `${detailData.submission.timeAtAddressYears || 0} años, ${detailData.submission.timeAtAddressMonths || 0} meses`
                        : 'N/A'
                    }
                  </div>
                </div>
              </div>

              {/* Employment Info */}
              <div className="p-4 bg-emerald-50 rounded-lg">
                <h4 className="font-medium text-emerald-700 mb-2 flex items-center gap-1">
                  <Briefcase className="w-4 h-4" /> Empleo e Ingresos
                </h4>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-emerald-600">Empleador:</span> {detailData.submission.employerName || 'N/A'}
                  </div>
                  <div>
                    <span className="text-emerald-600">Tiempo:</span> {
                      (detailData.submission.timeWithEmployerYears || detailData.submission.timeWithEmployerMonths)
                        ? `${detailData.submission.timeWithEmployerYears || 0} años, ${detailData.submission.timeWithEmployerMonths || 0} meses`
                        : 'N/A'
                    }
                  </div>
                  <div>
                    <span className="text-emerald-600">Tipo Ingreso:</span> {detailData.submission.incomeType || 'N/A'}
                  </div>
                  <div>
                    <span className="text-emerald-600">Ingreso Neto:</span> {detailData.submission.netIncome || 'N/A'} / {detailData.submission.incomeFrequency || 'N/A'}
                  </div>
                </div>
                <div className="mt-3 p-2 bg-white rounded border border-emerald-200">
                  <span className="text-emerald-700 font-medium">💰 Down Payment Estimado: {detailData.submission.estimatedDownPayment || 'N/A'}</span>
                </div>
              </div>

              {/* ID Document */}
              {detailData.submission.id_file_url && (
                <div className="p-4 bg-amber-50 rounded-lg">
                  <h4 className="font-medium text-amber-700 mb-2 flex items-center gap-1">
                    📄 Documento de ID Adjunto
                  </h4>
                  <div className="flex items-center gap-3">
                    <a 
                      href={`${process.env.REACT_APP_BACKEND_URL}${detailData.submission.id_file_url}`} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline flex items-center gap-1"
                    >
                      <ExternalLink className="w-4 h-4" />
                      Ver/Descargar Documento
                    </a>
                    {detailData.submission.id_file_url.match(/\.(jpg|jpeg|png)$/i) && (
                      <img 
                        src={`${process.env.REACT_APP_BACKEND_URL}${detailData.submission.id_file_url}`}
                        alt="ID Document"
                        className="max-w-xs max-h-40 rounded border"
                      />
                    )}
                  </div>
                </div>
              )}

              {/* Client Match / Comparison */}
              {detailData.comparison ? (
                <div className="p-4 bg-purple-50 rounded-lg border-2 border-purple-200">
                  <h4 className="font-medium text-purple-700 mb-2 flex items-center gap-1">
                    <User className="w-4 h-4" /> Cliente Existente Encontrado
                  </h4>
                  <p className="text-sm mb-2">
                    <strong>{detailData.comparison.client.first_name} {detailData.comparison.client.last_name}</strong>
                    <Button 
                      variant="link" 
                      size="sm" 
                      className="ml-2"
                      onClick={() => navigate(`/clients?search=${detailData.submission.phone}`)}
                    >
                      <ExternalLink className="w-3 h-3 mr-1" /> Ver Perfil
                    </Button>
                  </p>
                  
                  {detailData.comparison.differences.length > 0 ? (
                    <div className="mt-3">
                      <p className="text-sm text-amber-600 font-medium mb-2">
                        <AlertCircle className="w-4 h-4 inline mr-1" />
                        Diferencias encontradas:
                      </p>
                      <div className="space-y-1">
                        {detailData.comparison.differences.map((diff, idx) => (
                          <div key={idx} className="text-xs bg-white p-2 rounded flex justify-between">
                            <span className="font-medium">{diff.field}:</span>
                            <span className="text-red-500">Pre-qualify: {diff.prequalify}</span>
                            <span className="text-green-500">Cliente: {diff.client}</span>
                          </div>
                        ))}
                      </div>
                      <Button 
                        size="sm" 
                        variant="outline" 
                        className="mt-3"
                        onClick={() => handleAddToNotes(detailData.comparison.client.id)}
                      >
                        <MessageSquare className="w-4 h-4 mr-1" />
                        Agregar diferencias a Notas del Record
                      </Button>
                    </div>
                  ) : (
                    <p className="text-sm text-emerald-600">
                      <CheckCircle2 className="w-4 h-4 inline mr-1" />
                      Los datos coinciden con el perfil del cliente
                    </p>
                  )}
                </div>
              ) : (
                <div className="p-4 bg-amber-50 rounded-lg border-2 border-amber-200">
                  <h4 className="font-medium text-amber-700 mb-2 flex items-center gap-1">
                    <AlertCircle className="w-4 h-4" /> Sin Cliente Existente
                  </h4>
                  <p className="text-sm text-amber-600 mb-3">
                    No se encontró ningún cliente con el teléfono {detailData.submission.phone}
                  </p>
                  <Button onClick={handleCreateClient}>
                    <UserPlus className="w-4 h-4 mr-1" />
                    Crear Cliente con estos datos
                  </Button>
                </div>
              )}

              {/* Actions */}
              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button variant="outline" onClick={() => { setSelectedSubmission(null); setDetailData(null); }}>
                  Cerrar
                </Button>
                {detailData.submission.status !== 'converted' && !detailData.comparison && (
                  <Button onClick={handleCreateClient}>
                    <UserPlus className="w-4 h-4 mr-1" />
                    Crear Cliente
                  </Button>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
