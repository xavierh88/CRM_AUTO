import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { Checkbox } from '../components/ui/checkbox';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '../components/ui/collapsible';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { 
  Plus, Search, Info, Calendar, ChevronDown, ChevronRight, 
  Send, Trash2, CheckCircle2, XCircle, UserPlus, Phone, RefreshCw, MessageSquare,
  X, FileText, MessageCircle, Upload, Download, Home, Mail, Users
} from 'lucide-react';
import AddressAutocomplete from '../components/AddressAutocomplete';
import SmsInboxDialog from '../components/SmsInboxDialog';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ClientsPage() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedClient, setSelectedClient] = useState(null);
  const [showAddClient, setShowAddClient] = useState(false);
  const [expandedClients, setExpandedClients] = useState({});
  const [userRecords, setUserRecords] = useState({});
  const [appointments, setAppointments] = useState({});
  const [cosigners, setCosigners] = useState({});
  const [inboxClient, setInboxClient] = useState(null); // For SMS inbox dialog
  
  // Client notes/comments state
  const [notesClient, setNotesClient] = useState(null);
  const [clientNotes, setClientNotes] = useState([]);
  const [newClientNote, setNewClientNote] = useState('');
  const [loadingNotes, setLoadingNotes] = useState(false);
  
  // Salespersons list for collaborator selection
  const [salespersons, setSalespersons] = useState([]);
  
  // Config lists for dropdowns (shared across components)
  const [configLists, setConfigLists] = useState({ 
    banks: [], dealers: [], cars: [], 
    id_type: [], poi_type: [], por_type: [] 
  });
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const clientsPerPage = 10;
  
  const isAdmin = user?.role === 'admin';
  
  // Fetch config lists on mount
  useEffect(() => {
    const fetchConfigLists = async () => {
      try {
        const [banksRes, dealersRes, carsRes, idTypesRes, poiTypesRes, porTypesRes, salespersonsRes] = await Promise.all([
          axios.get(`${API}/config-lists/bank`),
          axios.get(`${API}/config-lists/dealer`),
          axios.get(`${API}/config-lists/car`),
          axios.get(`${API}/config-lists/id_type`).catch(() => ({ data: [] })),
          axios.get(`${API}/config-lists/poi_type`).catch(() => ({ data: [] })),
          axios.get(`${API}/config-lists/por_type`).catch(() => ({ data: [] })),
          axios.get(`${API}/salespersons`).catch(() => ({ data: [] }))
        ]);
        setConfigLists({
          banks: banksRes.data,
          dealers: dealersRes.data,
          cars: carsRes.data,
          id_type: idTypesRes.data,
          poi_type: poiTypesRes.data,
          por_type: porTypesRes.data
        });
        setSalespersons(salespersonsRes.data);
      } catch (error) {
        console.error('Failed to fetch config lists:', error);
      }
    };
    fetchConfigLists();
  }, []);
  
  const deleteClient = async (clientId) => {
    if (!window.confirm('¿Está seguro de eliminar este cliente? Se moverá a la papelera.')) return;
    try {
      await axios.delete(`${API}/clients/${clientId}`);
      toast.success('Cliente movido a la papelera');
      fetchClients();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al eliminar cliente');
    }
  };

  // Client notes functions
  const openClientNotes = async (client) => {
    setNotesClient(client);
    setLoadingNotes(true);
    try {
      const response = await axios.get(`${API}/clients/${client.id}/comments`);
      setClientNotes(response.data);
    } catch (error) {
      console.error('Error loading client notes:', error);
      setClientNotes([]);
    } finally {
      setLoadingNotes(false);
    }
  };

  const addClientNote = async () => {
    if (!newClientNote.trim() || !notesClient) return;
    try {
      const formData = new FormData();
      formData.append('comment', newClientNote);
      await axios.post(`${API}/clients/${notesClient.id}/comments`, formData);
      setNewClientNote('');
      // Reload notes
      const response = await axios.get(`${API}/clients/${notesClient.id}/comments`);
      setClientNotes(response.data);
      toast.success('Nota agregada');
    } catch (error) {
      toast.error('Error al agregar nota');
    }
  };

  const deleteClientNote = async (noteId) => {
    if (!window.confirm('¿Eliminar esta nota?')) return;
    try {
      await axios.delete(`${API}/clients/${notesClient.id}/comments/${noteId}`);
      const response = await axios.get(`${API}/clients/${notesClient.id}/comments`);
      setClientNotes(response.data);
      toast.success('Nota eliminada');
    } catch (error) {
      toast.error('Error al eliminar nota');
    }
  };

  const [newClient, setNewClient] = useState({
    first_name: '', last_name: '', phone: '', email: '', address: '', apartment: '',
    time_at_address_years: '', time_at_address_months: '',
    housing_type: '', rent_amount: ''
  });

  useEffect(() => {
    fetchClients();
  }, []);

  const fetchClients = async (search = '') => {
    try {
      const url = search ? `${API}/clients?search=${encodeURIComponent(search)}` : `${API}/clients`;
      const response = await axios.get(url);
      setClients(response.data);
    } catch (error) {
      toast.error('Failed to fetch clients');
    } finally {
      setLoading(false);
    }
  };

  const fetchClientRecords = async (clientId) => {
    try {
      const [recordsRes, cosignersRes] = await Promise.all([
        axios.get(`${API}/user-records?client_id=${clientId}`),
        axios.get(`${API}/cosigners/${clientId}`)
      ]);
      setUserRecords(prev => ({ ...prev, [clientId]: recordsRes.data }));
      setCosigners(prev => ({ ...prev, [clientId]: cosignersRes.data }));

      // Fetch appointments for each record
      for (const record of recordsRes.data) {
        const apptRes = await axios.get(`${API}/appointments?client_id=${clientId}`);
        const recordAppts = apptRes.data.filter(a => a.user_record_id === record.id);
        setAppointments(prev => ({ ...prev, [record.id]: recordAppts[0] || null }));
      }
    } catch (error) {
      console.error('Failed to fetch records:', error);
    }
  };

  const handleAddClient = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post(`${API}/clients`, newClient);
      setClients([response.data, ...clients]);
      setShowAddClient(false);
      setNewClient({ first_name: '', last_name: '', phone: '', email: '', address: '', apartment: '', time_at_address_years: '', time_at_address_months: '', housing_type: '', rent_amount: '' });
      toast.success(t('common.success'));
    } catch (error) {
      toast.error(error.response?.data?.detail || t('common.error'));
    }
  };

  const toggleClientExpand = (clientId) => {
    const isExpanding = !expandedClients[clientId];
    setExpandedClients(prev => ({ ...prev, [clientId]: isExpanding }));
    if (isExpanding && !userRecords[clientId]) {
      fetchClientRecords(clientId);
    }
  };

  const sendDocumentsSMS = async (clientId) => {
    try {
      await axios.post(`${API}/sms/send-documents-link?client_id=${clientId}`);
      toast.success('Documents SMS sent (mocked)');
    } catch (error) {
      toast.error('Failed to send SMS');
    }
  };

  const sendDocumentsEmail = async (client) => {
    if (!client.email) {
      toast.error('El cliente no tiene email registrado');
      return;
    }
    try {
      await axios.post(`${API}/email/send-documents-link?client_id=${client.id}`);
      toast.success(`Link de documentos enviado a ${client.email}`);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al enviar email');
    }
  };

  const sendAppointmentSMS = async (clientId, appointmentId) => {
    try {
      await axios.post(`${API}/sms/send-appointment-link?client_id=${clientId}&appointment_id=${appointmentId}`);
      toast.success('Appointment SMS sent (mocked)');
    } catch (error) {
      toast.error('Failed to send SMS');
    }
  };

  const sendAppointmentEmail = async (clientId, appointmentId) => {
    try {
      await axios.post(`${API}/email/send-appointment-link?client_id=${clientId}&appointment_id=${appointmentId}`);
      toast.success('Email de cita enviado exitosamente');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al enviar email');
    }
  };

  // Search with debounce
  useEffect(() => {
    const timer = setTimeout(() => {
      if (searchTerm) {
        fetchClients(searchTerm);
      } else {
        fetchClients();
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm]);

  const filteredClients = clients; // Search is now done server-side
  
  // Pagination logic
  const totalPages = Math.ceil(filteredClients.length / clientsPerPage);
  const indexOfLastClient = currentPage * clientsPerPage;
  const indexOfFirstClient = indexOfLastClient - clientsPerPage;
  const currentClients = filteredClients.slice(indexOfFirstClient, indexOfLastClient);
  
  // Reset to page 1 when search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [searchTerm]);

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString();
  };

  const getStatusBadge = (status) => {
    return (
      <span className={`status-badge status-${status}`}>
        <span className={`w-2 h-2 rounded-full mr-2 dot-${status}`}></span>
        {t(`status.${status}`)}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="clients-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{t('clients.title')}</h1>
          <p className="text-slate-500 mt-1">{clients.length} total clients</p>
        </div>
        <Dialog open={showAddClient} onOpenChange={setShowAddClient}>
          <DialogTrigger asChild>
            <Button className="bg-slate-900 hover:bg-slate-800" data-testid="add-client-btn">
              <Plus className="w-4 h-4 mr-2" />
              {t('clients.addNew')}
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>{t('clients.addNew')}</DialogTitle>
              <p className="text-sm text-slate-500">Enter client information below</p>
            </DialogHeader>
            <form onSubmit={handleAddClient} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="form-label">{t('clients.firstName')}</Label>
                  <Input
                    value={newClient.first_name}
                    onChange={(e) => setNewClient({ ...newClient, first_name: e.target.value })}
                    required
                    data-testid="client-first-name"
                  />
                </div>
                <div>
                  <Label className="form-label">{t('clients.lastName')}</Label>
                  <Input
                    value={newClient.last_name}
                    onChange={(e) => setNewClient({ ...newClient, last_name: e.target.value })}
                    required
                    data-testid="client-last-name"
                  />
                </div>
              </div>
              <div>
                <Label className="form-label">{t('clients.phone')}</Label>
                <Input
                  type="tel"
                  value={newClient.phone}
                  onChange={(e) => setNewClient({ ...newClient, phone: e.target.value })}
                  placeholder="(213) 462-9914"
                  required
                  data-testid="client-phone"
                />
                <p className="text-xs text-slate-400 mt-1">
                  Formato: 10 dígitos (ej: 2134629914) - Se agregará +1 automáticamente
                </p>
              </div>
              <div>
                <Label className="form-label">{t('clients.email')}</Label>
                <Input
                  type="email"
                  value={newClient.email}
                  onChange={(e) => setNewClient({ ...newClient, email: e.target.value })}
                  data-testid="client-email"
                />
              </div>
              <div>
                <Label className="form-label">{t('clients.address')}</Label>
                <AddressAutocomplete
                  value={newClient.address}
                  onChange={(value) => setNewClient({ ...newClient, address: value })}
                  data-testid="client-address"
                  placeholder="Start typing an address..."
                />
              </div>
              <div>
                <Label className="form-label">{t('clients.apartment')}</Label>
                <Input
                  value={newClient.apartment}
                  onChange={(e) => setNewClient({ ...newClient, apartment: e.target.value })}
                  data-testid="client-apartment"
                />
              </div>
              {/* Time at Address */}
              <div>
                <Label className="form-label">Time at Address</Label>
                <div className="flex gap-2">
                  <div className="flex-1">
                    <Input
                      type="number"
                      placeholder="Years"
                      value={newClient.time_at_address_years}
                      onChange={(e) => setNewClient({ ...newClient, time_at_address_years: e.target.value })}
                      data-testid="client-time-years"
                    />
                  </div>
                  <div className="flex-1">
                    <Input
                      type="number"
                      placeholder="Months"
                      value={newClient.time_at_address_months}
                      onChange={(e) => setNewClient({ ...newClient, time_at_address_months: e.target.value })}
                      data-testid="client-time-months"
                    />
                  </div>
                </div>
              </div>
              {/* Housing Type */}
              <div>
                <Label className="form-label">Housing Type</Label>
                <Select value={newClient.housing_type} onValueChange={(v) => setNewClient({ ...newClient, housing_type: v, rent_amount: v !== 'Renta' ? '' : newClient.rent_amount })}>
                  <SelectTrigger data-testid="client-housing-type">
                    <SelectValue placeholder="Select housing type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Dueño">Dueño</SelectItem>
                    <SelectItem value="Renta">Renta</SelectItem>
                    <SelectItem value="Vivo con familiares">Vivo con familiares</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {/* Rent Amount - only show if Renta selected */}
              {newClient.housing_type === 'Renta' && (
                <div>
                  <Label className="form-label">Rent Amount</Label>
                  <Input
                    placeholder="$"
                    value={newClient.rent_amount}
                    onChange={(e) => setNewClient({ ...newClient, rent_amount: e.target.value })}
                    data-testid="client-rent-amount"
                  />
                </div>
              )}
              <div className="flex gap-3 pt-2">
                <Button type="button" variant="outline" onClick={() => setShowAddClient(false)} className="flex-1">
                  {t('common.cancel')}
                </Button>
                <Button type="submit" className="flex-1 bg-slate-900" data-testid="save-client-btn">
                  {t('common.save')}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <Input
          placeholder={t('clients.search')}
          className="pl-10 max-w-md"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          data-testid="search-clients"
        />
      </div>

      {/* Client List */}
      <div className="space-y-3">
        {currentClients.length === 0 ? (
          <Card className="dashboard-card">
            <CardContent className="py-12 text-center text-slate-400">
              {t('common.noData')}
            </CardContent>
          </Card>
        ) : (
          currentClients.map((client) => {
            // Calculate progress and sold cars
            // Progress is based on COMPLETED records, NOT documents
            // Each completed record (record_status='completed') counts as a star
            // Progress resets with each new opportunity
            const soldCount = client.sold_count || 0;
            const hasRecords = !!client.last_record_date;
            
            // Progress: If any record is completed, show 100% (sale done for current opportunity)
            // Stars indicate number of completed sales across all opportunities
            let progress = 0;
            if (soldCount > 0) {
              progress = 100; // If there's at least one completed record, progress is 100%
            } else if (hasRecords) {
              progress = 50; // Has records but not completed yet
            }
            // Documents are shown as indicators but don't affect progress
            const docsUploaded = [client.id_uploaded, client.income_proof_uploaded, client.residence_proof_uploaded].filter(Boolean).length;
            
            return (
            <Card key={client.id} className="dashboard-card overflow-hidden" data-testid={`client-card-${client.id}`}>
              <Collapsible open={expandedClients[client.id]} onOpenChange={() => toggleClientExpand(client.id)}>
                <CollapsibleTrigger asChild>
                  <div className="flex items-center justify-between p-4 hover:bg-slate-50 cursor-pointer w-full" role="button" tabIndex={0}>
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-semibold relative">
                        {client.first_name.charAt(0)}
                        {/* Sold cars indicator */}
                        {soldCount > 0 && (
                          <div className="absolute -bottom-1 -right-1 bg-amber-400 text-white text-xs rounded-full px-1 flex items-center gap-0.5" title={`${soldCount} venta(s)`}>
                            🚗{soldCount > 1 && <span className="font-bold">{soldCount}</span>}
                          </div>
                        )}
                      </div>
                      <div className="text-left">
                        <div className="flex items-center gap-2">
                          <p className="font-semibold text-slate-900">
                            {client.first_name} {client.last_name}
                          </p>
                          {/* Sold badges - show stars based on sold count */}
                          {soldCount > 0 && (
                            <div className="flex items-center gap-1">
                              {[...Array(Math.min(soldCount, 5))].map((_, idx) => (
                                <span key={idx} className="text-amber-500" title={`Venta #${idx + 1}`}>
                                  ⭐
                                </span>
                              ))}
                              {soldCount > 5 && <span className="text-amber-500 text-xs font-bold">+{soldCount - 5}</span>}
                            </div>
                          )}
                        </div>
                        <p className="text-sm text-slate-500">{client.phone}</p>
                        {/* Progress bar */}
                        <div className="flex items-center gap-2 mt-1">
                          <div className="w-24 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                            <div 
                              className={`h-full rounded-full transition-all ${
                                progress >= 100 ? 'bg-green-500' : 
                                progress >= 66 ? 'bg-blue-500' : 
                                progress >= 33 ? 'bg-amber-500' : 'bg-slate-400'
                              }`}
                              style={{ width: `${progress}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-400">{progress}%</span>
                          {/* Document indicators */}
                          <div className="flex items-center gap-0.5 ml-1">
                            <span className={`text-xs ${client.id_uploaded ? 'text-green-500' : 'text-slate-300'}`} title="ID">📄</span>
                            <span className={`text-xs ${client.income_proof_uploaded ? 'text-green-500' : 'text-slate-300'}`} title="Ingresos">💵</span>
                            <span className={`text-xs ${client.residence_proof_uploaded ? 'text-green-500' : 'text-slate-300'}`} title="Residencia">🏠</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      {client.last_record_date && (
                        <div className="text-right hidden sm:block">
                          <p className="text-xs text-slate-400">{t('clients.lastContact')}</p>
                          <p className="text-sm font-medium text-slate-600">{formatDate(client.last_record_date)}</p>
                        </div>
                      )}
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedClient(client);
                        }}
                        data-testid={`client-info-btn-${client.id}`}
                      >
                        <Info className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                          e.stopPropagation();
                          setInboxClient(client);
                        }}
                        data-testid={`client-inbox-btn-${client.id}`}
                        title="SMS Inbox"
                        className="text-blue-500 hover:text-blue-700 hover:bg-blue-50"
                      >
                        <MessageSquare className="w-4 h-4" />
                      </Button>
                      {isAdmin && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteClient(client.id);
                          }}
                          className="text-red-400 hover:text-red-600 hover:bg-red-50"
                          data-testid={`delete-client-btn-${client.id}`}
                          title="Delete client"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      )}
                      {expandedClients[client.id] ? (
                        <ChevronDown className="w-5 h-5 text-slate-400" />
                      ) : (
                        <ChevronRight className="w-5 h-5 text-slate-400" />
                      )}
                    </div>
                  </div>
                </CollapsibleTrigger>

                <CollapsibleContent>
                  <div className="border-t border-slate-100 p-4 bg-slate-50/50">
                    {/* User Records */}
                    <UserRecordsSection 
                      clientId={client.id}
                      records={userRecords[client.id] || []}
                      appointments={appointments}
                      onRefresh={() => { fetchClientRecords(client.id); fetchClients(); }}
                      sendAppointmentSMS={sendAppointmentSMS}
                      sendAppointmentEmail={sendAppointmentEmail}
                      configLists={configLists}
                      salespersons={salespersons}
                    />

                    {/* Co-Signers */}
                    <CoSignersSection 
                      clientId={client.id}
                      cosigners={cosigners[client.id] || []}
                      onRefresh={() => { fetchClientRecords(client.id); fetchClients(); }}
                      configLists={configLists}
                    />
                  </div>
                </CollapsibleContent>
              </Collapsible>
            </Card>
            );
          })
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t">
          <p className="text-sm text-slate-500">
            Mostrando {indexOfFirstClient + 1}-{Math.min(indexOfLastClient, filteredClients.length)} de {filteredClients.length} clientes
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
              disabled={currentPage === 1}
            >
              Anterior
            </Button>
            <div className="flex items-center gap-1">
              {[...Array(totalPages)].map((_, i) => (
                <Button
                  key={i + 1}
                  variant={currentPage === i + 1 ? "default" : "outline"}
                  size="sm"
                  className="w-8 h-8 p-0"
                  onClick={() => setCurrentPage(i + 1)}
                >
                  {i + 1}
                </Button>
              ))}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
              disabled={currentPage === totalPages}
            >
              Siguiente
            </Button>
          </div>
        </div>
      )}

      {/* Client Info Modal */}
      {selectedClient && (
        <ClientInfoModal 
          client={selectedClient} 
          onClose={() => setSelectedClient(null)}
          onSendDocsSMS={() => sendDocumentsSMS(selectedClient.id)}
          onSendDocsEmail={() => sendDocumentsEmail(selectedClient)}
          onRefresh={fetchClients}
          isAdmin={isAdmin}
        />
      )}

      {/* SMS Inbox Dialog */}
      <SmsInboxDialog
        open={!!inboxClient}
        onOpenChange={(open) => !open && setInboxClient(null)}
        client={inboxClient}
        onMessageSent={fetchClients}
      />

      {/* Client Notes Dialog */}
      {notesClient && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setNotesClient(null)}>
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b bg-amber-50 rounded-t-xl">
              <div>
                <h3 className="font-semibold text-lg text-amber-800 flex items-center gap-2">
                  <MessageCircle className="w-5 h-5" />
                  Notas / Reseñas
                </h3>
                <p className="text-sm text-amber-600">{notesClient.first_name} {notesClient.last_name}</p>
              </div>
              <Button variant="ghost" size="icon" onClick={() => setNotesClient(null)}>
                <X className="w-5 h-5" />
              </Button>
            </div>

            {/* Add Note */}
            <div className="p-4 border-b">
              <div className="flex gap-2">
                <Input
                  placeholder="Escribir una nota o reseña..."
                  value={newClientNote}
                  onChange={(e) => setNewClientNote(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && addClientNote()}
                  className="flex-1"
                />
                <Button onClick={addClientNote} disabled={!newClientNote.trim()}>
                  Agregar
                </Button>
              </div>
            </div>

            {/* Notes List */}
            <div className="flex-1 overflow-y-auto p-4">
              {loadingNotes ? (
                <p className="text-center text-slate-400">Cargando notas...</p>
              ) : clientNotes.length === 0 ? (
                <p className="text-center text-slate-400 italic">No hay notas aún para este cliente</p>
              ) : (
                <div className="space-y-3">
                  {clientNotes.map((note) => (
                    <div key={note.id} className="bg-slate-50 rounded-lg p-3 border">
                      <p className="text-slate-700">{note.comment}</p>
                      <div className="flex items-center justify-between mt-2">
                        <p className="text-xs text-slate-400">
                          <span className="font-medium text-amber-600">{note.user_name}</span>
                          {' • '}
                          {new Date(note.created_at).toLocaleString('es-ES', { 
                            day: '2-digit', month: 'short', year: 'numeric', 
                            hour: '2-digit', minute: '2-digit' 
                          })}
                        </p>
                        {(note.user_id === user?.id || isAdmin) && (
                          <Button 
                            size="sm" 
                            variant="ghost" 
                            onClick={() => deleteClientNote(note.id)}
                            className="h-6 w-6 p-0"
                          >
                            <Trash2 className="w-3 h-3 text-red-400" />
                          </Button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// User Records Section Component
function UserRecordsSection({ clientId, records, appointments, onRefresh, sendAppointmentSMS, sendAppointmentEmail, configLists, salespersons }) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const [showAddRecord, setShowAddRecord] = useState(false);
  const [showNewOpportunity, setShowNewOpportunity] = useState(false);
  const [addingToOpportunity, setAddingToOpportunity] = useState(null);
  const [showAppointmentForm, setShowAppointmentForm] = useState(null); // record_id to show form for
  const [appointmentData, setAppointmentData] = useState({
    date: '', time: '', dealer: '', language: 'en'
  });
  const [expandedOpportunity, setExpandedOpportunity] = useState(null); // which opportunity is expanded
  const [editingRecord, setEditingRecord] = useState(null); // record being edited
  const [editRecordData, setEditRecordData] = useState(null);

  const emptyRecord = {
    // Legacy checkbox fields (now remapped)
    dl: false, checks: false, ssn: false, itin: false,
    // New ID fields
    has_id: false, id_type: '',
    // New POI fields  
    has_poi: false, poi_type: '',
    // New POR fields
    has_por: false, por_types: [],
    // Employment fields (replaces self_employed)
    self_employed: false,  // Legacy
    employment_type: '', employment_company_name: '', 
    employment_time_years: '', employment_time_months: '',
    // Bank info
    bank: '', bank_deposit_type: '', direct_deposit_amount: '',
    // Vehicle & finance
    auto: '', credit: '', 
    // Auto Loan fields
    auto_loan_status: '', auto_loan_bank: '', auto_loan_amount: '',
    // Down payment (now supports multiple selections)
    down_payment: '', down_payment_types: [], down_payment_cash: '', down_payment_card: '',
    // Trade-in details
    trade_make: '', trade_model: '', trade_year: '', trade_title: '', 
    trade_miles: '', trade_plate: '', trade_estimated_value: '',
    // Dealer
    dealer: '',
    // Finance status
    finance_status: 'no', vehicle_make: '', vehicle_year: '',
    sale_month: '', sale_day: '', sale_year: ''
  };

  const [newRecord, setNewRecord] = useState({ ...emptyRecord });

  const handleCreateAppointment = async (sendMethod = 'sms') => {
    if (!appointmentData.date || !appointmentData.time) {
      toast.error('Por favor complete fecha y hora');
      return;
    }
    try {
      const response = await axios.post(`${API}/appointments`, {
        user_record_id: showAppointmentForm,
        client_id: clientId,
        date: appointmentData.date,
        time: appointmentData.time,
        dealer: appointmentData.dealer,
        language: appointmentData.language
      });
      
      // Send notification based on method selected
      if (sendMethod === 'email') {
        await axios.post(`${API}/email/send-appointment-link?client_id=${clientId}&appointment_id=${response.data.id}`);
        toast.success('Cita creada y email enviado al cliente');
      } else {
        await axios.post(`${API}/sms/send-appointment-link?client_id=${clientId}&appointment_id=${response.data.id}`);
        toast.success('Cita creada y SMS enviado al cliente');
      }
      
      setShowAppointmentForm(null);
      setAppointmentData({ date: '', time: '', dealer: '', language: 'en' });
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al crear la cita');
    }
  };

  const handleUpdateAppointment = async () => {
    if (!appointmentData.date || !appointmentData.time) {
      toast.error('Por favor complete fecha y hora');
      return;
    }
    try {
      const existingAppt = appointments[showAppointmentForm];
      await axios.put(`${API}/appointments/${existingAppt.id}`, {
        date: appointmentData.date,
        time: appointmentData.time,
        dealer: appointmentData.dealer,
        language: appointmentData.language
      });
      
      toast.success('Cita actualizada exitosamente');
      setShowAppointmentForm(null);
      setAppointmentData({ date: '', time: '', dealer: '', language: 'en' });
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al actualizar la cita');
    }
  };

  // Function to open appointment form - loads existing data if appointment exists
  const openAppointmentForm = (recordId) => {
    const existingAppt = appointments[recordId];
    if (existingAppt) {
      setAppointmentData({
        date: existingAppt.date || '',
        time: existingAppt.time || '',
        dealer: existingAppt.dealer || '',
        language: existingAppt.language || 'en'
      });
    } else {
      setAppointmentData({ date: '', time: '', dealer: '', language: 'en' });
    }
    setShowAppointmentForm(recordId);
  };

  const handleEditRecord = (record) => {
    setEditingRecord(record.id);
    setEditRecordData({
      // New ID fields
      has_id: record.has_id || false,
      id_type: record.id_type || '',
      // New POI fields
      has_poi: record.has_poi || false,
      poi_type: record.poi_type || '',
      // Other checks
      ssn: record.ssn || false,
      itin: record.itin || false,
      self_employed: record.self_employed || false,
      // Employment fields
      employment_type: record.employment_type || '',
      employment_company_name: record.employment_company_name || '',
      employment_time_years: record.employment_time_years || '',
      employment_time_months: record.employment_time_months || '',
      // New POR fields
      has_por: record.has_por || false,
      por_types: record.por_types || [],
      // Bank info
      bank: record.bank || '',
      bank_deposit_type: record.bank_deposit_type || '',
      direct_deposit_amount: record.direct_deposit_amount || '',
      // Other fields
      auto: record.auto || '',
      credit: record.credit || '',
      // Auto Loan fields
      auto_loan_status: record.auto_loan_status || '',
      auto_loan_bank: record.auto_loan_bank || '',
      auto_loan_amount: record.auto_loan_amount || '',
      // Down Payment - support for multi-select
      down_payment_type: record.down_payment_type || '',
      down_payment_types: record.down_payment_types || (record.down_payment_type ? record.down_payment_type.split(', ').filter(t => t) : []),
      down_payment_cash: record.down_payment_cash || '',
      down_payment_card: record.down_payment_card || '',
      // Trade-in
      trade_make: record.trade_make || '',
      trade_model: record.trade_model || '',
      trade_year: record.trade_year || '',
      trade_title: record.trade_title || '',
      trade_miles: record.trade_miles || '',
      trade_plate: record.trade_plate || '',
      trade_estimated_value: record.trade_estimated_value || '',
      // Dealer
      dealer: record.dealer || '',
      // Finance status
      finance_status: record.finance_status || 'no',
      vehicle_make: record.vehicle_make || '',
      vehicle_year: record.vehicle_year || '',
      sale_month: record.sale_month?.toString() || '',
      sale_day: record.sale_day?.toString() || '',
      sale_year: record.sale_year?.toString() || '',
      // Collaborator
      collaborator_id: record.collaborator_id || null,
      collaborator_name: record.collaborator_name || null,
      // Commission fields
      commission_percentage: record.commission_percentage || '',
      commission_value: record.commission_value || '',
      // Legacy fields for backward compatibility
      dl: record.dl || false,
      checks: record.checks || false,
      down_payment: record.down_payment || ''
    });
  };

  const handleSaveEditRecord = async () => {
    try {
      const newCollaborator = editRecordData.collaborator_id;
      
      // If admin is saving commission data, lock the record status
      const shouldLock = isAdmin && editRecordData.commission_percentage && editRecordData.commission_value;
      
      await axios.put(`${API}/user-records/${editingRecord}`, {
        client_id: clientId,
        ...editRecordData,
        sale_month: editRecordData.sale_month ? parseInt(editRecordData.sale_month) : null,
        sale_day: editRecordData.sale_day ? parseInt(editRecordData.sale_day) : null,
        sale_year: editRecordData.sale_year ? parseInt(editRecordData.sale_year) : null,
        commission_percentage: editRecordData.commission_percentage ? parseFloat(editRecordData.commission_percentage) : null,
        commission_value: editRecordData.commission_value ? parseFloat(editRecordData.commission_value) : null,
        commission_locked: shouldLock
      });
      
      // Send notification to collaborator if there's one assigned
      if (newCollaborator) {
        try {
          await axios.post(`${API}/notifications/collaborator?record_id=${editingRecord}&action=record_updated`);
        } catch (e) {
          console.log('Notification failed:', e);
        }
      }
      
      setEditingRecord(null);
      setEditRecordData(null);
      onRefresh();
      toast.success('Record updated');
    } catch (error) {
      toast.error('Failed to update record');
    }
  };

  const handleMarkRecordStatus = async (recordId, status) => {
    try {
      await axios.put(`${API}/user-records/${recordId}`, {
        client_id: clientId,
        record_status: status
      });
      onRefresh();
      const statusText = status === 'completed' ? 'Completado' : status === 'no_show' ? 'No-Show' : 'Sin estado';
      toast.success(`Record marcado como ${statusText}`);
    } catch (error) {
      toast.error('Error al actualizar el estado del record');
    }
  };

  const handleDeleteRecord = async (recordId) => {
    if (!window.confirm('Are you sure you want to delete this record?')) return;
    try {
      await axios.delete(`${API}/user-records/${recordId}`);
      onRefresh();
      toast.success('Record deleted');
    } catch (error) {
      toast.error('Failed to delete record');
    }
  };

  const toggleOpportunity = (oppNum) => {
    setExpandedOpportunity(expandedOpportunity === oppNum ? null : oppNum);
  };

  const handleAddRecord = async (previousRecordId = null) => {
    try {
      await axios.post(`${API}/user-records`, { 
        client_id: clientId, 
        ...newRecord,
        previous_record_id: previousRecordId,
        sale_month: newRecord.sale_month ? parseInt(newRecord.sale_month) : null,
        sale_day: newRecord.sale_day ? parseInt(newRecord.sale_day) : null,
        sale_year: newRecord.sale_year ? parseInt(newRecord.sale_year) : null
      });
      setShowAddRecord(false);
      setShowNewOpportunity(false);
      setAddingToOpportunity(null);
      setNewRecord({ ...emptyRecord });
      onRefresh();
      toast.success(t('common.success'));
    } catch (error) {
      toast.error(error.response?.data?.detail || t('common.error'));
    }
  };

  const createAppointment = async (recordId) => {
    try {
      await axios.post(`${API}/appointments`, { user_record_id: recordId, client_id: clientId });
      onRefresh();
      toast.success('Appointment created');
    } catch (error) {
      toast.error(t('common.error'));
    }
  };

  const updateAppointmentStatus = async (apptId, status) => {
    try {
      await axios.put(`${API}/appointments/${apptId}/status?status=${status}`);
      onRefresh();
      toast.success('Status updated');
    } catch (error) {
      toast.error(t('common.error'));
    }
  };

  const getStatusBadge = (status) => (
    <span className={`status-badge status-${status}`}>
      <span className={`w-2 h-2 rounded-full mr-2 dot-${status}`}></span>
      {t(`status.${status}`)}
    </span>
  );

  // Group ALL records by opportunity number (show all records, not just user's)
  // All users can see all records, but can only delete their own
  const opportunityGroups = {};
  records.forEach(record => {
    const oppNum = record.opportunity_number || 1;
    if (!opportunityGroups[oppNum]) opportunityGroups[oppNum] = [];
    opportunityGroups[oppNum].push(record);
  });
  
  // Get my records for checking if I can create new opportunity
  const myRecords = records.filter(r => r.salesperson_id === user.id);
  const myOpportunityGroups = {};
  myRecords.forEach(record => {
    const oppNum = record.opportunity_number || 1;
    if (!myOpportunityGroups[oppNum]) myOpportunityGroups[oppNum] = [];
    myOpportunityGroups[oppNum].push(record);
  });
  
  // Get the highest opportunity number and check if current user can create more
  const maxOpportunity = Math.max(...Object.keys(opportunityGroups).map(Number), 0);
  const myMaxOpportunity = Math.max(...Object.keys(myOpportunityGroups).map(Number), 0);
  const latestRecordInMyLastOpp = myOpportunityGroups[myMaxOpportunity]?.[0];
  const canCreateNewOpportunity = myMaxOpportunity < 5 && latestRecordInMyLastOpp && 
    (latestRecordInMyLastOpp.finance_status === 'financiado' || latestRecordInMyLastOpp.finance_status === 'lease');

  const opportunityColors = ['blue', 'purple', 'emerald', 'amber', 'rose'];
  
  // Auto-expand the latest opportunity with records, or first if none
  const defaultExpanded = maxOpportunity > 0 ? maxOpportunity : 1;
  const currentExpanded = expandedOpportunity ?? defaultExpanded;

  return (
    <div className="mb-4">
      {/* Render each opportunity (1-5) */}
      {[1, 2, 3, 4, 5].map((oppNum) => {
        const oppRecords = opportunityGroups[oppNum] || [];
        const isFirst = oppNum === 1;
        const shouldShow = isFirst || oppRecords.length > 0 || (showNewOpportunity && oppNum === maxOpportunity + 1);
        const isExpanded = currentExpanded === oppNum;
        
        if (!shouldShow) return null;

        return (
          <div key={oppNum} className={`mb-2 ${oppNum > 1 ? 'mt-4 pt-3 border-t-2 border-slate-100' : ''}`}>
            {/* Collapsible Header */}
            <div 
              className={`flex items-center justify-between p-3 rounded-lg cursor-pointer transition-colors ${
                isExpanded 
                  ? isFirst ? 'bg-blue-50' : oppNum === 2 ? 'bg-purple-50' : oppNum === 3 ? 'bg-emerald-50' : oppNum === 4 ? 'bg-amber-50' : 'bg-rose-50'
                  : 'bg-slate-50 hover:bg-slate-100'
              }`}
              onClick={() => toggleOpportunity(oppNum)}
            >
              <h4 className={`font-semibold ${isFirst ? 'text-slate-700' : oppNum === 2 ? 'text-purple-700' : oppNum === 3 ? 'text-emerald-700' : oppNum === 4 ? 'text-amber-700' : 'text-rose-700'} flex items-center gap-2`}>
                <span className={`w-6 h-6 ${isFirst ? 'bg-blue-600' : oppNum === 2 ? 'bg-purple-600' : oppNum === 3 ? 'bg-emerald-600' : oppNum === 4 ? 'bg-amber-600' : 'bg-rose-600'} text-white rounded-full flex items-center justify-center text-xs`}>
                  {oppNum}
                </span>
                {isFirst ? 'Oportunidad #1' : `Nueva Oportunidad #${oppNum}`}
                <span className="text-xs text-slate-400 font-normal">
                  ({oppRecords.length} record{oppRecords.length !== 1 ? 's' : ''})
                </span>
              </h4>
              <div className="flex items-center gap-2">
                {isExpanded && (
                  <Button 
                    size="sm" 
                    variant="outline" 
                    onClick={(e) => { e.stopPropagation(); setShowAddRecord(true); setAddingToOpportunity(oppNum); }}
                    data-testid={`add-record-btn-${oppNum}`}
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    Add
                  </Button>
                )}
                {isExpanded ? (
                  <ChevronDown className="w-5 h-5 text-slate-400" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-slate-400" />
                )}
              </div>
            </div>

            {/* Collapsible Content */}
            {isExpanded && (
              <div className="space-y-3 mt-3 pl-2">
                {oppRecords.map((record) => (
                  <RecordCard 
                    key={record.id}
                    record={record}
                    appointments={appointments}
                    getStatusBadge={getStatusBadge}
                    sendAppointmentSMS={sendAppointmentSMS}
                    sendAppointmentEmail={sendAppointmentEmail}
                    clientId={clientId}
                    createAppointment={createAppointment}
                    updateAppointmentStatus={updateAppointmentStatus}
                    t={t}
                    isPurple={oppNum > 1}
                    onOpenAppointmentForm={openAppointmentForm}
                    currentUserId={user.id}
                    onEdit={handleEditRecord}
                    onDelete={handleDeleteRecord}
                    isEditing={editingRecord === record.id}
                    editData={editRecordData}
                    setEditData={setEditRecordData}
                    onSaveEdit={handleSaveEditRecord}
                    onCancelEdit={() => { setEditingRecord(null); setEditRecordData(null); }}
                    configLists={configLists}
                    salespersons={salespersons}
                    onMarkRecordStatus={handleMarkRecordStatus}
                    isAdmin={isAdmin}
                  />
                ))}
                
                {oppRecords.length === 0 && isFirst && !showAddRecord && (
                  <p className="text-sm text-slate-400 text-center py-4">No records yet. Click &quot;Add&quot; to create one.</p>
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* Button to create New Opportunity (up to 5) */}
      {canCreateNewOpportunity && !showNewOpportunity && (
        <div className="mt-4 pt-4 border-t border-dashed border-slate-200">
          <Button 
            variant="outline"
            className="w-full text-purple-600 hover:bg-purple-50 border-purple-200 border-dashed"
            onClick={() => { setShowNewOpportunity(true); setAddingToOpportunity(maxOpportunity + 1); }}
            data-testid="new-opportunity-btn"
          >
            <Plus className="w-4 h-4 mr-2" />
            Crear Nueva Oportunidad #{maxOpportunity + 1}
          </Button>
        </div>
      )}

      {/* Appointment Form Modal - Create or Edit */}
      {showAppointmentForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md m-4">
            <h3 className="text-lg font-semibold mb-4">
              {appointments[showAppointmentForm] ? '📅 Modificar Cita' : '📅 Agendar Cita'}
            </h3>
            <div className="space-y-4">
              <div>
                <Label className="form-label">Fecha *</Label>
                <Input 
                  type="date" 
                  value={appointmentData.date}
                  onChange={(e) => setAppointmentData({ ...appointmentData, date: e.target.value })}
                />
              </div>
              <div>
                <Label className="form-label">Hora *</Label>
                <Input 
                  type="time" 
                  value={appointmentData.time}
                  onChange={(e) => setAppointmentData({ ...appointmentData, time: e.target.value })}
                />
              </div>
              <div>
                <Label className="form-label">Dealer</Label>
                <Input 
                  placeholder="Ubicación del dealer"
                  value={appointmentData.dealer}
                  onChange={(e) => setAppointmentData({ ...appointmentData, dealer: e.target.value })}
                />
              </div>
              <div>
                <Label className="form-label">Idioma del Cliente</Label>
                <Select value={appointmentData.language} onValueChange={(value) => setAppointmentData({ ...appointmentData, language: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">English</SelectItem>
                    <SelectItem value="es">Español</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-slate-400 mt-1">El cliente recibirá la notificación en este idioma</p>
              </div>
              
              {/* Show different buttons based on whether we're editing or creating */}
              {appointments[showAppointmentForm] ? (
                <div className="space-y-2 pt-2">
                  <div className="flex gap-2">
                    <Button variant="outline" onClick={() => { setShowAppointmentForm(null); setAppointmentData({ date: '', time: '', dealer: '', language: 'en' }); }} className="flex-1">
                      Cancelar
                    </Button>
                    <Button onClick={() => handleUpdateAppointment()} className="flex-1">
                      💾 Guardar Cambios
                    </Button>
                  </div>
                  <div className="flex gap-2 border-t pt-2">
                    <Button onClick={() => sendAppointmentSMS(clientId, appointments[showAppointmentForm].id)} variant="outline" className="flex-1" size="sm">
                      <Send className="w-4 h-4 mr-1" />
                      Reenviar SMS
                    </Button>
                    <Button onClick={() => sendAppointmentEmail(clientId, appointments[showAppointmentForm].id)} className="flex-1 bg-green-600 hover:bg-green-700" size="sm">
                      <Mail className="w-4 h-4 mr-1" />
                      Reenviar Email
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex gap-2 pt-2">
                  <Button variant="outline" onClick={() => setShowAppointmentForm(null)} className="flex-1">
                    Cancelar
                  </Button>
                  <Button onClick={() => handleCreateAppointment('sms')} variant="outline" className="flex-1">
                    <Send className="w-4 h-4 mr-1" />
                    Crear + SMS
                  </Button>
                  <Button onClick={() => handleCreateAppointment('email')} className="flex-1 bg-green-600 hover:bg-green-700">
                    <Mail className="w-4 h-4 mr-1" />
                    Crear + Email
                  </Button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Add Record Form */}
      {(showAddRecord || showNewOpportunity) && (
        <div className="bg-white rounded-lg border border-blue-200 p-4 mt-3">
          <h5 className="font-medium text-slate-700 mb-3">New Record</h5>
          
          {/* ID Section */}
          <div className="space-y-3 mb-4">
            <div className="flex items-center gap-3">
              <Checkbox
                checked={newRecord.has_id}
                onCheckedChange={(checked) => setNewRecord({ ...newRecord, has_id: checked, id_type: checked ? newRecord.id_type : '' })}
                id="new-has_id"
              />
              <Label htmlFor="new-has_id" className="font-medium">ID</Label>
            </div>
            {newRecord.has_id && (
              <Select value={newRecord.id_type} onValueChange={(value) => setNewRecord({ ...newRecord, id_type: value })}>
                <SelectTrigger className="max-w-xs">
                  <SelectValue placeholder="Seleccionar tipo de ID" />
                </SelectTrigger>
                <SelectContent>
                  {configLists.id_type.map((item) => (
                    <SelectItem key={item.id} value={item.name}>{item.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {/* POI Section (Proof of Income) */}
          <div className="space-y-3 mb-4">
            <div className="flex items-center gap-3">
              <Checkbox
                checked={newRecord.has_poi}
                onCheckedChange={(checked) => setNewRecord({ ...newRecord, has_poi: checked, poi_type: checked ? newRecord.poi_type : '' })}
                id="new-has_poi"
              />
              <Label htmlFor="new-has_poi" className="font-medium">POI (Proof of Income)</Label>
            </div>
            {newRecord.has_poi && (
              <Select value={newRecord.poi_type} onValueChange={(value) => setNewRecord({ ...newRecord, poi_type: value })}>
                <SelectTrigger className="max-w-xs">
                  <SelectValue placeholder="Seleccionar tipo de POI" />
                </SelectTrigger>
                <SelectContent>
                  {configLists.poi_type.map((item) => (
                    <SelectItem key={item.id} value={item.name}>{item.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>

          {/* Other Checkboxes */}
          <div className="flex flex-wrap gap-4 mb-4">
            <div className="flex items-center gap-2">
              <Checkbox
                checked={newRecord.ssn}
                onCheckedChange={(checked) => setNewRecord({ ...newRecord, ssn: checked })}
                id="new-ssn"
              />
              <Label htmlFor="new-ssn">SSN</Label>
            </div>
            <div className="flex items-center gap-2">
              <Checkbox
                checked={newRecord.itin}
                onCheckedChange={(checked) => setNewRecord({ ...newRecord, itin: checked })}
                id="new-itin"
              />
              <Label htmlFor="new-itin">ITIN</Label>
            </div>
          </div>

          {/* Employment Section */}
          <div className="space-y-3 mb-4">
            <Label className="font-medium">Employment</Label>
            <Select value={newRecord.employment_type} onValueChange={(value) => setNewRecord({ ...newRecord, employment_type: value, employment_company_name: '' })}>
              <SelectTrigger className="max-w-xs">
                <SelectValue placeholder="Select employment type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Company">Company</SelectItem>
                <SelectItem value="Retired/workcomp/SSN/SDI">Retired/workcomp/SSN/SDI</SelectItem>
                <SelectItem value="Unemployed">Unemployed</SelectItem>
                <SelectItem value="Self employed">Self employed</SelectItem>
              </SelectContent>
            </Select>
            
            {/* Company name field - show for Company or Self employed */}
            {(newRecord.employment_type === 'Company' || newRecord.employment_type === 'Self employed') && (
              <div>
                <Label className="form-label mb-1 block">
                  {newRecord.employment_type === 'Company' ? 'Company Name' : 'Business Name'}
                </Label>
                <Input
                  value={newRecord.employment_company_name}
                  onChange={(e) => setNewRecord({ ...newRecord, employment_company_name: e.target.value })}
                  placeholder="Enter name"
                />
              </div>
            )}
            
            {/* Time at employment - show for any employment type */}
            {newRecord.employment_type && (
              <div>
                <Label className="form-label mb-1 block">Time at Employment</Label>
                <div className="flex gap-2 max-w-xs">
                  <Input
                    type="number"
                    placeholder="Years"
                    value={newRecord.employment_time_years}
                    onChange={(e) => setNewRecord({ ...newRecord, employment_time_years: e.target.value })}
                  />
                  <Input
                    type="number"
                    placeholder="Months"
                    value={newRecord.employment_time_months}
                    onChange={(e) => setNewRecord({ ...newRecord, employment_time_months: e.target.value })}
                  />
                </div>
              </div>
            )}
          </div>

          {/* POR Section (Proof of Residence) */}
          <div className="space-y-3 mb-4">
            <div className="flex items-center gap-3">
              <Checkbox
                checked={newRecord.has_por}
                onCheckedChange={(checked) => setNewRecord({ ...newRecord, has_por: checked, por_types: checked ? newRecord.por_types : [] })}
                id="new-has_por"
              />
              <Label htmlFor="new-has_por" className="font-medium">POR (Proof of Residence)</Label>
            </div>
            {newRecord.has_por && (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 ml-6">
                {configLists.por_type.map((item) => (
                  <div key={item.id} className="flex items-center gap-2">
                    <Checkbox
                      checked={(newRecord.por_types || []).includes(item.name)}
                      onCheckedChange={(checked) => {
                        const current = newRecord.por_types || [];
                        setNewRecord({
                          ...newRecord,
                          por_types: checked 
                            ? [...current, item.name]
                            : current.filter(t => t !== item.name)
                        });
                      }}
                      id={`new-por_${item.id}`}
                    />
                    <Label htmlFor={`new-por_${item.id}`} className="text-sm">{item.name}</Label>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Bank Section */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
            <div>
              <Label className="form-label mb-1 block">Bank</Label>
              <Select value={newRecord.bank} onValueChange={(value) => setNewRecord({ ...newRecord, bank: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar banco" />
                </SelectTrigger>
                <SelectContent className="max-h-60">
                  {configLists.banks.map((bank) => (
                    <SelectItem key={bank.id} value={bank.name}>{bank.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="form-label mb-1 block">Tipo de Depósito</Label>
              <Select value={newRecord.bank_deposit_type} onValueChange={(value) => setNewRecord({ ...newRecord, bank_deposit_type: value, direct_deposit_amount: value !== 'Deposito Directo' ? '' : newRecord.direct_deposit_amount })}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar tipo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Deposito Directo">Deposito Directo</SelectItem>
                  <SelectItem value="No deposito directo">No deposito directo</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Direct Deposit Amount - shown when Deposito Directo is selected */}
          {newRecord.bank_deposit_type === 'Deposito Directo' && (
            <div className="mb-4">
              <Label className="form-label mb-1 block">Monto de Depósito Directo</Label>
              <Input
                placeholder="$0.00"
                value={newRecord.direct_deposit_amount || ''}
                onChange={(e) => setNewRecord({ ...newRecord, direct_deposit_amount: e.target.value })}
                className="max-w-xs"
              />
            </div>
          )}

          {/* Cosigner Alert */}
          {newRecord.bank_deposit_type === 'No deposito directo' && newRecord.has_poi && newRecord.poi_type === 'Cash' && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4 flex items-start gap-2">
              <span className="text-amber-600 text-lg">⚠️</span>
              <div>
                <p className="font-medium text-amber-800">Atención</p>
                <p className="text-sm text-amber-700">Va a necesitar un Cosigner o probar ingreso adicional.</p>
              </div>
            </div>
          )}

          {/* Auto, Credit, Auto Loan */}
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
            <div>
              <Label className="form-label mb-1 block">Auto</Label>
              <Select value={newRecord.auto} onValueChange={(value) => setNewRecord({ ...newRecord, auto: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Seleccionar auto" />
                </SelectTrigger>
                <SelectContent className="max-h-60">
                  {configLists.cars.map((car) => (
                    <SelectItem key={car.id} value={car.name}>{car.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="form-label mb-1 block">Credit</Label>
              <Input placeholder="Score" value={newRecord.credit} onChange={(e) => setNewRecord({ ...newRecord, credit: e.target.value })} />
            </div>
          </div>

          {/* Auto Loan Section */}
          <div className="border rounded-lg p-3 mb-4">
            <Label className="form-label mb-2 block font-medium">Auto Loan</Label>
            <div className="flex flex-wrap gap-4 mb-3">
              {['Paid', 'Late', 'On Time'].map((status) => (
                <div key={status} className="flex items-center gap-2">
                  <Checkbox
                    checked={newRecord.auto_loan_status === status}
                    onCheckedChange={(checked) => {
                      setNewRecord({ 
                        ...newRecord, 
                        auto_loan_status: checked ? status : null,
                        auto_loan_bank: checked && status === 'On Time' ? newRecord.auto_loan_bank : '',
                        auto_loan_amount: checked && status === 'On Time' ? newRecord.auto_loan_amount : ''
                      });
                    }}
                  />
                  <span className="text-sm">{status}</span>
                </div>
              ))}
            </div>
            {newRecord.auto_loan_status === 'On Time' && (
              <div className="grid grid-cols-2 gap-3 mt-2">
                <div>
                  <Label className="form-label mb-1 block text-xs">Banco</Label>
                  <Select value={newRecord.auto_loan_bank || ''} onValueChange={(value) => setNewRecord({ ...newRecord, auto_loan_bank: value })}>
                    <SelectTrigger><SelectValue placeholder="Seleccionar banco" /></SelectTrigger>
                    <SelectContent>
                      {configLists.banks.map((bank) => (
                        <SelectItem key={bank.id} value={bank.name}>{bank.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="form-label mb-1 block text-xs">Monto</Label>
                  <Input placeholder="$0.00" value={newRecord.auto_loan_amount || ''} onChange={(e) => setNewRecord({ ...newRecord, auto_loan_amount: e.target.value })} />
                </div>
              </div>
            )}
          </div>

          {/* Down Payment Section - Multi-select */}
          <div className="border rounded-lg p-3 mb-4">
            <Label className="form-label mb-2 block font-medium">Down Payment (puede seleccionar varios)</Label>
            <div className="flex flex-wrap gap-4 mb-3">
              {['Cash', 'Tarjeta', 'Trade'].map((type) => (
                <div key={type} className="flex items-center gap-2">
                  <Checkbox
                    checked={(newRecord.down_payment_types || []).includes(type)}
                    onCheckedChange={(checked) => {
                      const currentTypes = newRecord.down_payment_types || [];
                      const newTypes = checked 
                        ? [...currentTypes, type]
                        : currentTypes.filter(t => t !== type);
                      setNewRecord({ 
                        ...newRecord, 
                        down_payment_types: newTypes,
                        down_payment_type: newTypes.join(', '), // For backward compatibility
                        down_payment_cash: !newTypes.includes('Cash') ? '' : newRecord.down_payment_cash,
                        down_payment_card: !newTypes.includes('Tarjeta') ? '' : newRecord.down_payment_card
                      });
                    }}
                    id={`new-dp_${type}`}
                  />
                  <Label htmlFor={`new-dp_${type}`}>{type}</Label>
                </div>
              ))}
            </div>

            {(newRecord.down_payment_types || []).includes('Cash') && (
              <Input
                placeholder="Monto en Cash $0.00"
                value={newRecord.down_payment_cash}
                onChange={(e) => setNewRecord({ ...newRecord, down_payment_cash: e.target.value })}
                className="max-w-xs mb-2"
              />
            )}

            {(newRecord.down_payment_types || []).includes('Tarjeta') && (
              <Input
                placeholder="Monto en Tarjeta $0.00"
                value={newRecord.down_payment_card}
                onChange={(e) => setNewRecord({ ...newRecord, down_payment_card: e.target.value })}
                className="max-w-xs mb-2"
              />
            )}

            {(newRecord.down_payment_types || []).includes('Trade') && (
              <div className="space-y-3 p-3 bg-slate-50 rounded-lg">
                <h5 className="font-medium text-sm flex items-center gap-1">🚗 Vehículo en Trade</h5>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  <Input placeholder="Make" value={newRecord.trade_make} onChange={(e) => setNewRecord({ ...newRecord, trade_make: e.target.value })} />
                  <Input placeholder="Model" value={newRecord.trade_model} onChange={(e) => setNewRecord({ ...newRecord, trade_model: e.target.value })} />
                  <Input placeholder="Year" value={newRecord.trade_year} onChange={(e) => setNewRecord({ ...newRecord, trade_year: e.target.value })} />
                  <Select value={newRecord.trade_title} onValueChange={(value) => setNewRecord({ ...newRecord, trade_title: value })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Title" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Clean Title">Clean Title</SelectItem>
                      <SelectItem value="Salvaged">Salvaged</SelectItem>
                    </SelectContent>
                  </Select>
                  <Input placeholder="Miles" value={newRecord.trade_miles} onChange={(e) => setNewRecord({ ...newRecord, trade_miles: e.target.value })} />
                  <Select value={newRecord.trade_plate} onValueChange={(value) => setNewRecord({ ...newRecord, trade_plate: value })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Plate" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="CA">CA</SelectItem>
                      <SelectItem value="Out of State">Out of State</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <Input placeholder="Estimated Value $0.00" value={newRecord.trade_estimated_value} onChange={(e) => setNewRecord({ ...newRecord, trade_estimated_value: e.target.value })} />
              </div>
            )}
          </div>

          {/* Dealer */}
          <div className="mb-4">
            <Label className="form-label mb-1 block">Dealer</Label>
            <Select value={newRecord.dealer} onValueChange={(value) => setNewRecord({ ...newRecord, dealer: value })}>
              <SelectTrigger className="max-w-xs">
                <SelectValue placeholder="Seleccionar dealer" />
              </SelectTrigger>
              <SelectContent>
                {configLists.dealers.map((dealer) => (
                  <SelectItem key={dealer.id} value={dealer.name}>{dealer.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Sold Status */}
          <div className="mb-4">
            <Label className="form-label mb-1 block">Finance Status</Label>
            <Select value={newRecord.finance_status} onValueChange={(value) => setNewRecord({ ...newRecord, finance_status: value })}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Select option" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="no">No</SelectItem>
                <SelectItem value="financiado">Financiado</SelectItem>
                <SelectItem value="lease">Lease</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Vehicle Info (only when financiado or lease) */}
          {(newRecord.finance_status === 'financiado' || newRecord.finance_status === 'lease') && (
            <div className="bg-blue-50 rounded-lg p-3 mb-4 border border-blue-200">
              <Label className="form-label mb-2 block text-blue-700">Vehicle Information</Label>
              <div className="grid grid-cols-2 gap-3">
                <Input placeholder="Make (Marca)" value={newRecord.vehicle_make} onChange={(e) => setNewRecord({ ...newRecord, vehicle_make: e.target.value })} />
                <Input placeholder="Year (Año)" value={newRecord.vehicle_year} onChange={(e) => setNewRecord({ ...newRecord, vehicle_year: e.target.value })} />
              </div>
              <div className="grid grid-cols-3 gap-3 mt-3">
                <Select value={newRecord.sale_month} onValueChange={(value) => setNewRecord({ ...newRecord, sale_month: value })}>
                  <SelectTrigger>
                    <SelectValue placeholder="Month" />
                  </SelectTrigger>
                  <SelectContent>
                    {[...Array(12)].map((_, i) => (
                      <SelectItem key={i+1} value={String(i+1)}>{new Date(2000, i).toLocaleString('default', { month: 'short' })}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={newRecord.sale_day} onValueChange={(value) => setNewRecord({ ...newRecord, sale_day: value })}>
                  <SelectTrigger>
                    <SelectValue placeholder="Day" />
                  </SelectTrigger>
                  <SelectContent>
                    {[...Array(31)].map((_, i) => (
                      <SelectItem key={i+1} value={String(i+1)}>{i+1}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <Select value={newRecord.sale_year} onValueChange={(value) => setNewRecord({ ...newRecord, sale_year: value })}>
                  <SelectTrigger>
                    <SelectValue placeholder="Year" />
                  </SelectTrigger>
                  <SelectContent>
                    {[2024, 2025, 2026].map((year) => (
                      <SelectItem key={year} value={String(year)}>{year}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => { setShowAddRecord(false); setShowNewOpportunity(false); setAddingToOpportunity(null); }}>{t('common.cancel')}</Button>
            <Button size="sm" onClick={() => handleAddRecord(addingToOpportunity > 1 ? latestRecordInMyLastOpp?.id : null)} data-testid="save-record-btn">{t('common.save')}</Button>
          </div>
        </div>
      )}
    </div>
  );
}

// Record Card Component
function RecordCard({ 
  record, appointments, getStatusBadge, sendAppointmentSMS, sendAppointmentEmail, clientId, createAppointment, 
  updateAppointmentStatus, t, isPurple, onOpenAppointmentForm, currentUserId,
  onEdit, onDelete, isEditing, editData, setEditData, onSaveEdit, onCancelEdit, configLists, salespersons,
  onMarkRecordStatus, isAdmin
}) {
  const isOwner = record.salesperson_id === currentUserId;
  const [showComments, setShowComments] = useState(false);
  const [comments, setComments] = useState([]);
  const [commentsCount, setCommentsCount] = useState(record.comments_count || 0);
  const [newComment, setNewComment] = useState('');
  const [loadingComments, setLoadingComments] = useState(false);

  // Load comment count on mount
  useEffect(() => {
    const fetchCommentsCount = async () => {
      try {
        const response = await axios.get(`${API}/user-records/${record.id}/comments`);
        setCommentsCount(response.data.length);
      } catch (error) {
        console.error('Error fetching comments count:', error);
      }
    };
    fetchCommentsCount();
  }, [record.id]);

  // Email report state
  const [showEmailDialog, setShowEmailDialog] = useState(false);
  const [emailAddresses, setEmailAddresses] = useState('');
  const [sendingEmail, setSendingEmail] = useState(false);
  const [attachDocuments, setAttachDocuments] = useState(false);

  const sendEmailReport = async () => {
    if (!emailAddresses.trim()) {
      toast.error('Por favor ingrese al menos un email');
      return;
    }
    
    const emails = emailAddresses.split(',').map(e => e.trim()).filter(e => e);
    if (emails.length === 0) {
      toast.error('Por favor ingrese emails válidos');
      return;
    }
    
    setSendingEmail(true);
    try {
      const response = await axios.post(`${API}/send-record-report`, {
        emails,
        record_id: record.id,
        client_id: clientId,
        include_documents: true,
        attach_documents: attachDocuments
      });
      const attachMsg = response.data.attachments_count > 0 
        ? ` con ${response.data.attachments_count} documento(s) adjunto(s)` 
        : '';
      toast.success(`Reporte enviado a ${emails.length} destinatario(s)${attachMsg}`);
      setShowEmailDialog(false);
      setEmailAddresses('');
      setAttachDocuments(false);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al enviar el reporte');
    } finally {
      setSendingEmail(false);
    }
  };

  const loadComments = async () => {
    setLoadingComments(true);
    try {
      const response = await axios.get(`${API}/user-records/${record.id}/comments`);
      setComments(response.data);
      setCommentsCount(response.data.length);
    } catch (error) {
      console.error('Error loading comments:', error);
    } finally {
      setLoadingComments(false);
    }
  };

  const openCommentsDialog = () => {
    setShowComments(true);
    loadComments();
  };

  const addComment = async () => {
    if (!newComment.trim()) return;
    try {
      const formData = new FormData();
      formData.append('comment', newComment);
      await axios.post(`${API}/user-records/${record.id}/comments`, formData);
      setNewComment('');
      loadComments();
      toast.success('Comentario agregado');
    } catch (error) {
      toast.error('Error al agregar comentario');
    }
  };

  const deleteComment = async (commentId) => {
    if (!window.confirm('¿Eliminar este comentario?')) return;
    try {
      await axios.delete(`${API}/user-records/${record.id}/comments/${commentId}`);
      loadComments();
      toast.success('Comentario eliminado');
    } catch (error) {
      toast.error('Error al eliminar comentario');
    }
  };

  if (isEditing) {
    return (
      <div className={`bg-white rounded-lg border p-4 ${isPurple ? 'border-purple-200' : 'border-blue-200'}`}>
        <h5 className="font-medium text-slate-700 mb-3">Edit Record</h5>
        
        {/* ID Section */}
        <div className="space-y-2 mb-4">
          <div className="flex items-center gap-3">
            <Checkbox
              checked={editData.has_id}
              onCheckedChange={(checked) => setEditData({ ...editData, has_id: checked, id_type: checked ? editData.id_type : '' })}
              id="edit-has_id"
            />
            <Label htmlFor="edit-has_id" className="font-medium">ID</Label>
          </div>
          {editData.has_id && (
            <Select value={editData.id_type || ''} onValueChange={(value) => setEditData({ ...editData, id_type: value })}>
              <SelectTrigger className="max-w-xs">
                <SelectValue placeholder="Seleccionar tipo de ID" />
              </SelectTrigger>
              <SelectContent>
                {configLists?.id_type?.map((item) => (
                  <SelectItem key={item.id} value={item.name}>{item.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>

        {/* POI Section */}
        <div className="space-y-2 mb-4">
          <div className="flex items-center gap-3">
            <Checkbox
              checked={editData.has_poi}
              onCheckedChange={(checked) => setEditData({ ...editData, has_poi: checked, poi_type: checked ? editData.poi_type : '' })}
              id="edit-has_poi"
            />
            <Label htmlFor="edit-has_poi" className="font-medium">POI (Proof of Income)</Label>
          </div>
          {editData.has_poi && (
            <Select value={editData.poi_type || ''} onValueChange={(value) => setEditData({ ...editData, poi_type: value })}>
              <SelectTrigger className="max-w-xs">
                <SelectValue placeholder="Seleccionar tipo de POI" />
              </SelectTrigger>
              <SelectContent>
                {configLists?.poi_type?.map((item) => (
                  <SelectItem key={item.id} value={item.name}>{item.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>

        {/* Other Checkboxes */}
        <div className="flex flex-wrap gap-4 mb-4">
          <div className="flex items-center gap-2">
            <Checkbox checked={editData.ssn} onCheckedChange={(checked) => setEditData({ ...editData, ssn: checked })} id="edit-ssn" />
            <Label htmlFor="edit-ssn">SSN</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox checked={editData.itin} onCheckedChange={(checked) => setEditData({ ...editData, itin: checked })} id="edit-itin" />
            <Label htmlFor="edit-itin">ITIN</Label>
          </div>
        </div>

        {/* Employment Section */}
        <div className="space-y-3 mb-4">
          <Label className="font-medium">Employment</Label>
          <Select value={editData.employment_type || ''} onValueChange={(value) => setEditData({ ...editData, employment_type: value, employment_company_name: '' })}>
            <SelectTrigger className="max-w-xs">
              <SelectValue placeholder="Select employment type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Company">Company</SelectItem>
              <SelectItem value="Retired/workcomp/SSN/SDI">Retired/workcomp/SSN/SDI</SelectItem>
              <SelectItem value="Unemployed">Unemployed</SelectItem>
              <SelectItem value="Self employed">Self employed</SelectItem>
            </SelectContent>
          </Select>
          
          {/* Company name field */}
          {(editData.employment_type === 'Company' || editData.employment_type === 'Self employed') && (
            <div>
              <Label className="form-label mb-1 block">
                {editData.employment_type === 'Company' ? 'Company Name' : 'Business Name'}
              </Label>
              <Input
                value={editData.employment_company_name || ''}
                onChange={(e) => setEditData({ ...editData, employment_company_name: e.target.value })}
                placeholder="Enter name"
              />
            </div>
          )}
          
          {/* Time at employment */}
          {editData.employment_type && (
            <div>
              <Label className="form-label mb-1 block">Time at Employment</Label>
              <div className="flex gap-2 max-w-xs">
                <Input
                  type="number"
                  placeholder="Years"
                  value={editData.employment_time_years || ''}
                  onChange={(e) => setEditData({ ...editData, employment_time_years: e.target.value })}
                />
                <Input
                  type="number"
                  placeholder="Months"
                  value={editData.employment_time_months || ''}
                  onChange={(e) => setEditData({ ...editData, employment_time_months: e.target.value })}
                />
              </div>
            </div>
          )}
        </div>

        {/* POR Section */}
        <div className="space-y-2 mb-4">
          <div className="flex items-center gap-3">
            <Checkbox
              checked={editData.has_por}
              onCheckedChange={(checked) => setEditData({ ...editData, has_por: checked, por_types: checked ? editData.por_types : [] })}
              id="edit-has_por"
            />
            <Label htmlFor="edit-has_por" className="font-medium">POR (Proof of Residence)</Label>
          </div>
          {editData.has_por && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 ml-6">
              {configLists?.por_type?.map((item) => (
                <div key={item.id} className="flex items-center gap-2">
                  <Checkbox
                    checked={(editData.por_types || []).includes(item.name)}
                    onCheckedChange={(checked) => {
                      const current = editData.por_types || [];
                      setEditData({
                        ...editData,
                        por_types: checked 
                          ? [...current, item.name]
                          : current.filter(t => t !== item.name)
                      });
                    }}
                  />
                  <Label className="text-sm">{item.name}</Label>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Bank Section */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
          <div>
            <Label className="form-label mb-1 block text-xs">Bank</Label>
            <Select value={editData.bank || ''} onValueChange={(value) => setEditData({ ...editData, bank: value })}>
              <SelectTrigger>
                <SelectValue placeholder="Seleccionar banco" />
              </SelectTrigger>
              <SelectContent className="max-h-60">
                {configLists?.banks?.map((bank) => (
                  <SelectItem key={bank.id} value={bank.name}>{bank.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="form-label mb-1 block text-xs">Tipo de Depósito</Label>
            <Select value={editData.bank_deposit_type || ''} onValueChange={(value) => setEditData({ ...editData, bank_deposit_type: value, direct_deposit_amount: value !== 'Deposito Directo' ? '' : editData.direct_deposit_amount })}>
              <SelectTrigger>
                <SelectValue placeholder="Seleccionar tipo" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Deposito Directo">Deposito Directo</SelectItem>
                <SelectItem value="No deposito directo">No deposito directo</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Direct Deposit Amount - shown when Deposito Directo is selected */}
        {editData.bank_deposit_type === 'Deposito Directo' && (
          <div className="mb-4">
            <Label className="form-label mb-1 block text-xs">Monto de Depósito Directo</Label>
            <Input
              placeholder="$0.00"
              value={editData.direct_deposit_amount || ''}
              onChange={(e) => setEditData({ ...editData, direct_deposit_amount: e.target.value })}
              className="max-w-xs"
            />
          </div>
        )}

        {/* Cosigner Alert */}
        {editData.bank_deposit_type === 'No deposito directo' && editData.has_poi && editData.poi_type === 'Cash' && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4 flex items-start gap-2">
            <span className="text-amber-600">⚠️</span>
            <div>
              <p className="font-medium text-amber-800 text-sm">Atención</p>
              <p className="text-xs text-amber-700">Va a necesitar un Cosigner o probar ingreso adicional.</p>
            </div>
          </div>
        )}

        {/* Auto, Credit, Auto Loan */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
          <div>
            <Label className="form-label mb-1 block text-xs">Auto</Label>
            <Select value={editData.auto || ''} onValueChange={(value) => setEditData({ ...editData, auto: value })}>
              <SelectTrigger>
                <SelectValue placeholder="Auto" />
              </SelectTrigger>
              <SelectContent className="max-h-60">
                {configLists?.cars?.map((car) => (
                  <SelectItem key={car.id} value={car.name}>{car.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="form-label mb-1 block text-xs">Credit</Label>
            <Input placeholder="Score" value={editData.credit || ''} onChange={(e) => setEditData({ ...editData, credit: e.target.value })} />
          </div>
        </div>

        {/* Auto Loan Section */}
        <div className="border rounded-lg p-3 mb-4">
          <Label className="form-label mb-2 block font-medium text-sm">Auto Loan</Label>
          <div className="flex flex-wrap gap-4 mb-3">
            {['Paid', 'Late', 'On Time'].map((status) => (
              <div key={status} className="flex items-center gap-2">
                <Checkbox
                  checked={editData.auto_loan_status === status}
                  onCheckedChange={(checked) => {
                    setEditData({ 
                      ...editData, 
                      auto_loan_status: checked ? status : '',
                      auto_loan_bank: checked && status === 'On Time' ? editData.auto_loan_bank : '',
                      auto_loan_amount: checked && status === 'On Time' ? editData.auto_loan_amount : ''
                    });
                  }}
                />
                <span className="text-sm">{status}</span>
              </div>
            ))}
          </div>
          {editData.auto_loan_status === 'On Time' && (
            <div className="grid grid-cols-2 gap-3 mt-2">
              <div>
                <Label className="form-label mb-1 block text-xs">Banco</Label>
                <Select value={editData.auto_loan_bank || ''} onValueChange={(value) => setEditData({ ...editData, auto_loan_bank: value })}>
                  <SelectTrigger><SelectValue placeholder="Seleccionar banco" /></SelectTrigger>
                  <SelectContent>
                    {configLists?.banks?.map((bank) => (
                      <SelectItem key={bank.id} value={bank.name}>{bank.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="form-label mb-1 block text-xs">Monto</Label>
                <Input placeholder="$0.00" value={editData.auto_loan_amount || ''} onChange={(e) => setEditData({ ...editData, auto_loan_amount: e.target.value })} />
              </div>
            </div>
          )}
        </div>

        {/* Down Payment Section - Multi-select */}
        <div className="border rounded-lg p-3 mb-4">
          <Label className="form-label mb-2 block font-medium text-sm">Down Payment (puede seleccionar varios)</Label>
          <div className="flex flex-wrap gap-4 mb-3">
            {['Cash', 'Tarjeta', 'Trade'].map((type) => (
              <div key={type} className="flex items-center gap-2">
                <Checkbox
                  checked={(editData.down_payment_types || (editData.down_payment_type ? editData.down_payment_type.split(', ') : [])).includes(type)}
                  onCheckedChange={(checked) => {
                    const currentTypes = editData.down_payment_types || (editData.down_payment_type ? editData.down_payment_type.split(', ') : []);
                    const newTypes = checked 
                      ? [...currentTypes.filter(t => t), type]
                      : currentTypes.filter(t => t !== type);
                    setEditData({ 
                      ...editData, 
                      down_payment_types: newTypes,
                      down_payment_type: newTypes.join(', '),
                      down_payment_cash: !newTypes.includes('Cash') ? '' : editData.down_payment_cash,
                      down_payment_card: !newTypes.includes('Tarjeta') ? '' : editData.down_payment_card
                    });
                  }}
                />
                <Label>{type}</Label>
              </div>
            ))}
          </div>

          {(editData.down_payment_types || (editData.down_payment_type ? editData.down_payment_type.split(', ') : [])).includes('Cash') && (
            <Input placeholder="Monto en Cash $0.00" value={editData.down_payment_cash || ''} onChange={(e) => setEditData({ ...editData, down_payment_cash: e.target.value })} className="max-w-xs mb-2" />
          )}

          {(editData.down_payment_types || (editData.down_payment_type ? editData.down_payment_type.split(', ') : [])).includes('Tarjeta') && (
            <Input placeholder="Monto en Tarjeta $0.00" value={editData.down_payment_card || ''} onChange={(e) => setEditData({ ...editData, down_payment_card: e.target.value })} className="max-w-xs mb-2" />
          )}

          {(editData.down_payment_types || (editData.down_payment_type ? editData.down_payment_type.split(', ') : [])).includes('Trade') && (
            <div className="space-y-3 p-3 bg-slate-50 rounded-lg">
              <h5 className="font-medium text-sm">🚗 Vehículo en Trade</h5>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                <Input placeholder="Make" value={editData.trade_make || ''} onChange={(e) => setEditData({ ...editData, trade_make: e.target.value })} />
                <Input placeholder="Model" value={editData.trade_model || ''} onChange={(e) => setEditData({ ...editData, trade_model: e.target.value })} />
                <Input placeholder="Year" value={editData.trade_year || ''} onChange={(e) => setEditData({ ...editData, trade_year: e.target.value })} />
                <Select value={editData.trade_title || ''} onValueChange={(value) => setEditData({ ...editData, trade_title: value })}>
                  <SelectTrigger><SelectValue placeholder="Title" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Clean Title">Clean Title</SelectItem>
                    <SelectItem value="Salvaged">Salvaged</SelectItem>
                  </SelectContent>
                </Select>
                <Input placeholder="Miles" value={editData.trade_miles || ''} onChange={(e) => setEditData({ ...editData, trade_miles: e.target.value })} />
                <Select value={editData.trade_plate || ''} onValueChange={(value) => setEditData({ ...editData, trade_plate: value })}>
                  <SelectTrigger><SelectValue placeholder="Plate" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="CA">CA</SelectItem>
                    <SelectItem value="Out of State">Out of State</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <Input placeholder="Estimated Value $0.00" value={editData.trade_estimated_value || ''} onChange={(e) => setEditData({ ...editData, trade_estimated_value: e.target.value })} />
            </div>
          )}
        </div>

        {/* Dealer */}
        <div className="mb-4">
          <Label className="form-label mb-1 block text-xs">Dealer</Label>
          <Select value={editData.dealer || ''} onValueChange={(value) => setEditData({ ...editData, dealer: value })}>
            <SelectTrigger className="max-w-xs">
              <SelectValue placeholder="Seleccionar dealer" />
            </SelectTrigger>
            <SelectContent>
              {configLists?.dealers?.map((dealer) => (
                <SelectItem key={dealer.id} value={dealer.name}>{dealer.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Finance Status */}
        <div className="mb-4">
          <Label className="form-label mb-1 block text-xs">Finance Status</Label>
          <Select value={editData.finance_status || 'no'} onValueChange={(value) => setEditData({ ...editData, finance_status: value })}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="no">No</SelectItem>
              <SelectItem value="financiado">Financiado</SelectItem>
              <SelectItem value="lease">Lease</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Vehicle Info */}
        {(editData.finance_status === 'financiado' || editData.finance_status === 'lease') && (
          <div className="bg-blue-50 rounded-lg p-3 mb-4 border border-blue-200">
            <Label className="form-label mb-2 block text-blue-700 text-sm">Vehicle Information</Label>
            <div className="grid grid-cols-2 gap-3">
              <Input placeholder="Make" value={editData.vehicle_make || ''} onChange={(e) => setEditData({ ...editData, vehicle_make: e.target.value })} />
              <Input placeholder="Year" value={editData.vehicle_year || ''} onChange={(e) => setEditData({ ...editData, vehicle_year: e.target.value })} />
            </div>
            <div className="grid grid-cols-3 gap-3 mt-3">
              <Select value={editData.sale_month || ''} onValueChange={(value) => setEditData({ ...editData, sale_month: value })}>
                <SelectTrigger><SelectValue placeholder="Month" /></SelectTrigger>
                <SelectContent>
                  {[...Array(12)].map((_, i) => (
                    <SelectItem key={i+1} value={String(i+1)}>{new Date(2000, i).toLocaleString('default', { month: 'short' })}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={editData.sale_day || ''} onValueChange={(value) => setEditData({ ...editData, sale_day: value })}>
                <SelectTrigger><SelectValue placeholder="Day" /></SelectTrigger>
                <SelectContent>
                  {[...Array(31)].map((_, i) => (
                    <SelectItem key={i+1} value={String(i+1)}>{i+1}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={editData.sale_year || ''} onValueChange={(value) => setEditData({ ...editData, sale_year: value })}>
                <SelectTrigger><SelectValue placeholder="Year" /></SelectTrigger>
                <SelectContent>
                  {[2024, 2025, 2026].map((year) => (
                    <SelectItem key={year} value={String(year)}>{year}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        )}

        {/* Collaborator Section - Admin Only */}
        {isAdmin && (
          <div className="mb-4 p-3 bg-purple-50 border border-purple-200 rounded-lg">
            <Label className="form-label mb-2 block text-purple-700 text-sm flex items-center gap-2">
              <Users className="w-4 h-4" />
              Colaborador (Usuario compartido)
            </Label>
            <Select 
              value={editData.collaborator_id || 'none'} 
              onValueChange={(value) => {
                const selectedUser = salespersons.find(s => s.id === value);
                setEditData({ 
                  ...editData, 
                  collaborator_id: value === 'none' ? null : value,
                  collaborator_name: value === 'none' ? null : selectedUser?.name || selectedUser?.email
                });
              }}
            >
              <SelectTrigger className="max-w-xs">
                <SelectValue placeholder="Seleccionar colaborador" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Sin colaborador</SelectItem>
                {salespersons.filter(s => s.id !== currentUserId).map((sp) => (
                  <SelectItem key={sp.id} value={sp.id}>{sp.name || sp.email}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-purple-500 mt-1">El colaborador será notificado de los cambios en este record</p>
          </div>
        )}

        {/* Commission Section - Admin Only, shown when record is completed */}
        {isAdmin && record.record_status === 'completed' && (
          <div className="mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
            <Label className="form-label mb-2 block text-amber-700 text-sm flex items-center gap-2">
              💰 Comisión (Solo Admin)
            </Label>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="form-label mb-1 block text-xs">Porcentaje (%)</Label>
                <Input 
                  type="number" 
                  min="0" 
                  max="100" 
                  placeholder="0-100" 
                  value={editData.commission_percentage || ''} 
                  onChange={(e) => setEditData({ ...editData, commission_percentage: e.target.value })} 
                />
              </div>
              <div>
                <Label className="form-label mb-1 block text-xs">Valor ($)</Label>
                <Input 
                  type="number" 
                  placeholder="$0.00" 
                  value={editData.commission_value || ''} 
                  onChange={(e) => setEditData({ ...editData, commission_value: e.target.value })} 
                />
              </div>
              <div>
                <Label className="form-label mb-1 block text-xs">Resultado</Label>
                <div className="h-9 px-3 py-2 bg-white border rounded-md text-sm flex items-center font-medium text-emerald-600">
                  ${((parseFloat(editData.commission_percentage || 0) / 100) * parseFloat(editData.commission_value || 0)).toFixed(2)}
                </div>
              </div>
            </div>
            <p className="text-xs text-amber-600 mt-2">Al guardar, el estado de completado quedará bloqueado para otros usuarios.</p>
          </div>
        )}

        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={onCancelEdit}>Cancel</Button>
          <Button size="sm" onClick={onSaveEdit}>Save Changes</Button>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-lg border p-4 ${isPurple ? 'border-purple-200' : 'border-slate-200'}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-medium ${isPurple ? 'text-purple-600' : 'text-blue-600'}`}>
            Record
          </span>
          <span className="text-xs text-slate-400">by {record.salesperson_name}</span>
          {/* Record completion status badge */}
          {record.record_status === 'completed' && (
            <span className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded text-xs font-medium">
              ✓ Completado
            </span>
          )}
          {record.record_status === 'no_show' && (
            <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-xs font-medium">
              ✗ No-Show
            </span>
          )}
          {record.finance_status && record.finance_status !== 'no' && (
            <span className="bg-amber-100 text-amber-700 px-2 py-0.5 rounded text-xs font-medium uppercase">
              SOLD - {record.finance_status}
            </span>
          )}
          {/* Show collaborator badge if exists */}
          {record.collaborator_name && (
            <span className="bg-purple-100 text-purple-700 px-2 py-0.5 rounded text-xs font-medium flex items-center gap-1">
              <Users className="w-3 h-3" />
              {record.collaborator_name}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {/* Email Report button - Admin Only */}
          {isAdmin && (
            <Button size="sm" variant="ghost" onClick={() => setShowEmailDialog(true)} title="Enviar Reporte por Email" className="relative">
              <Mail className="w-4 h-4 text-green-500" />
            </Button>
          )}
          {/* Comments button with counter */}
          <Button size="sm" variant="ghost" onClick={openCommentsDialog} title="Comentarios" className="relative">
            <MessageCircle className="w-4 h-4 text-blue-400" />
            {commentsCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-blue-500 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
                {commentsCount}
              </span>
            )}
          </Button>
          {/* Edit button - available to all */}
          <Button size="sm" variant="ghost" onClick={() => onEdit(record)} title="Edit">
            <RefreshCw className="w-4 h-4 text-slate-400" />
          </Button>
          {/* Delete button - only for owner */}
          {isOwner && (
            <Button size="sm" variant="ghost" onClick={() => onDelete(record.id)} title="Delete">
              <Trash2 className="w-4 h-4 text-red-400" />
            </Button>
          )}
          {appointments[record.id] ? (
            <div className="flex items-center gap-1">
              {getStatusBadge(appointments[record.id].status)}
              <Button size="sm" variant="ghost" onClick={() => onOpenAppointmentForm(record.id)} title="Editar/Modificar Cita">
                <Calendar className="w-4 h-4 text-purple-500" />
              </Button>
            </div>
          ) : (
            <Button size="sm" variant="outline" onClick={() => onOpenAppointmentForm(record.id)}>
              <Calendar className="w-4 h-4 mr-1" />
              Appt
            </Button>
          )}
        </div>
      </div>

      {/* Comments Dialog */}
      {showComments && (
        <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
          <div className="flex items-center justify-between mb-3">
            <h6 className="font-medium text-blue-700 flex items-center gap-2">
              <MessageCircle className="w-4 h-4" />
              Comentarios ({comments.length})
            </h6>
            <Button size="sm" variant="ghost" onClick={() => setShowComments(false)} className="h-6 w-6 p-0">
              <X className="w-4 h-4" />
            </Button>
          </div>

          {/* Add Comment */}
          <div className="flex gap-2 mb-3">
            <Input
              placeholder="Escribir comentario..."
              value={newComment}
              onChange={(e) => setNewComment(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && addComment()}
              className="flex-1 h-8 text-sm"
            />
            <Button size="sm" onClick={addComment} disabled={!newComment.trim()}>
              Agregar
            </Button>
          </div>

          {/* Comments List */}
          {loadingComments ? (
            <p className="text-sm text-slate-400">Cargando...</p>
          ) : comments.length === 0 ? (
            <p className="text-sm text-slate-400 italic">No hay comentarios aún</p>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {comments.map((comment) => (
                <div key={comment.id} className="bg-white rounded p-2 border border-blue-100">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="text-sm text-slate-700">{comment.comment}</p>
                      <p className="text-xs text-slate-400 mt-1">
                        <span className="font-medium text-blue-600">{comment.user_name}</span>
                        {' • '}
                        {new Date(comment.created_at).toLocaleString('es-ES', { 
                          day: '2-digit', month: 'short', year: 'numeric', 
                          hour: '2-digit', minute: '2-digit' 
                        })}
                      </p>
                    </div>
                    {(comment.user_id === currentUserId) && (
                      <Button 
                        size="sm" 
                        variant="ghost" 
                        onClick={() => deleteComment(comment.id)}
                        className="h-6 w-6 p-0"
                      >
                        <Trash2 className="w-3 h-3 text-red-400" />
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Email Report Dialog */}
      {showEmailDialog && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowEmailDialog(false)}>
          <div className="bg-white rounded-lg p-6 w-full max-w-md mx-4" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Mail className="w-5 h-5 text-green-500" />
                Enviar Reporte por Email
              </h3>
              <Button variant="ghost" size="sm" onClick={() => setShowEmailDialog(false)}>
                <X className="w-4 h-4" />
              </Button>
            </div>
            
            <div className="space-y-4">
              <div>
                <Label className="text-sm font-medium">Destinatarios (separar con comas)</Label>
                <Input
                  placeholder="email1@ejemplo.com, email2@ejemplo.com"
                  value={emailAddresses}
                  onChange={(e) => setEmailAddresses(e.target.value)}
                  className="mt-1"
                />
                <p className="text-xs text-slate-400 mt-1">Puede enviar a múltiples emails separándolos por comas</p>
              </div>
              
              <div className="bg-slate-50 p-3 rounded-lg text-sm">
                <p className="font-medium mb-2">El reporte incluirá:</p>
                <ul className="text-slate-600 space-y-1 text-xs">
                  <li>• Información del cliente (nombre, teléfono, email, dirección)</li>
                  <li>• Datos del record (ID, POI, SSN, banco, crédito, etc.)</li>
                  <li>• Down Payment y detalles de Trade-in</li>
                  <li>• Estado de documentos subidos</li>
                  <li>• Estado de financiamiento</li>
                  <li>• Información de co-firmantes (si hay)</li>
                </ul>
              </div>
              
              {/* Attach Documents Option */}
              <div className="flex items-center space-x-2 p-3 bg-blue-50 rounded-lg border border-blue-200">
                <Checkbox 
                  id="attach-docs" 
                  checked={attachDocuments}
                  onCheckedChange={(checked) => setAttachDocuments(checked)}
                />
                <label htmlFor="attach-docs" className="text-sm cursor-pointer flex-1">
                  <span className="font-medium text-blue-700">📎 Adjuntar documentos del cliente</span>
                  <p className="text-xs text-blue-500 mt-0.5">
                    Se adjuntarán los archivos de ID, ingresos y residencia (si están disponibles)
                  </p>
                </label>
              </div>
              
              <div className="flex gap-2 pt-2">
                <Button variant="outline" onClick={() => setShowEmailDialog(false)} className="flex-1">
                  Cancelar
                </Button>
                <Button onClick={sendEmailReport} disabled={sendingEmail} className="flex-1 bg-green-600 hover:bg-green-700">
                  {sendingEmail ? 'Enviando...' : 'Enviar Reporte'}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Checklist - New format */}
      <div className="flex gap-3 mb-3 flex-wrap">
        {record.has_id && (
          <div className="flex items-center gap-1 bg-emerald-50 text-emerald-700 px-2 py-1 rounded text-xs">
            <span>✓</span> ID: {record.id_type || 'Sí'}
          </div>
        )}
        {record.has_poi && (
          <div className="flex items-center gap-1 bg-emerald-50 text-emerald-700 px-2 py-1 rounded text-xs">
            <span>✓</span> POI: {record.poi_type || 'Sí'}
          </div>
        )}
        {record.ssn && (
          <div className="flex items-center gap-1 bg-emerald-50 text-emerald-700 px-2 py-1 rounded text-xs">
            <span>✓</span> SSN
          </div>
        )}
        {record.itin && (
          <div className="flex items-center gap-1 bg-emerald-50 text-emerald-700 px-2 py-1 rounded text-xs">
            <span>✓</span> ITIN
          </div>
        )}
        {record.self_employed && (
          <div className="flex items-center gap-1 bg-amber-50 text-amber-700 px-2 py-1 rounded text-xs">
            <span>✓</span> Self Employed
          </div>
        )}
        {record.has_por && (
          <div className="flex items-center gap-1 bg-blue-50 text-blue-700 px-2 py-1 rounded text-xs">
            <span>✓</span> POR: {(record.por_types || []).join(', ') || 'Sí'}
          </div>
        )}
        {/* Legacy fields for old records */}
        {!record.has_id && record.dl && (
          <div className="flex items-center gap-1 bg-emerald-50 text-emerald-700 px-2 py-1 rounded text-xs">
            <span>✓</span> DL
          </div>
        )}
        {!record.has_poi && record.checks && (
          <div className="flex items-center gap-1 bg-emerald-50 text-emerald-700 px-2 py-1 rounded text-xs">
            <span>✓</span> CHECKS
          </div>
        )}
      </div>

      {/* Details */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-sm">
        {record.auto && <div><span className="text-slate-400">Auto:</span> {record.auto}</div>}
        {record.credit && <div><span className="text-slate-400">Credit:</span> {record.credit}</div>}
        {record.bank && (
          <div>
            <span className="text-slate-400">Bank:</span> {record.bank}
            {record.bank_deposit_type && <span className="text-xs text-slate-400"> ({record.bank_deposit_type})</span>}
          </div>
        )}
        {record.auto_loan && <div><span className="text-slate-400">Auto Loan:</span> {record.auto_loan}</div>}
        {record.dealer && <div><span className="text-slate-400">Dealer:</span> {record.dealer}</div>}
        {/* Down Payment - supports multiple selections */}
        {record.down_payment_type && (
          <div>
            <span className="text-slate-400">Down:</span> {record.down_payment_type}
            {record.down_payment_type.includes('Cash') && record.down_payment_cash && ` (Cash: $${record.down_payment_cash})`}
            {record.down_payment_type.includes('Tarjeta') && record.down_payment_card && ` (Tarjeta: $${record.down_payment_card})`}
          </div>
        )}
        {/* Direct Deposit Amount */}
        {record.bank_deposit_type === 'Deposito Directo' && record.direct_deposit_amount && (
          <div>
            <span className="text-slate-400">Depósito Directo:</span> ${record.direct_deposit_amount}
          </div>
        )}
        {/* Legacy down_payment for old records */}
        {!record.down_payment_type && record.down_payment && <div><span className="text-slate-400">Down:</span> ${record.down_payment}</div>}
      </div>

      {/* Trade-in Details - supports multi-select */}
      {record.down_payment_type && record.down_payment_type.includes('Trade') && record.trade_make && (
        <div className="mt-2 p-2 bg-slate-50 rounded text-xs">
          <span className="font-medium">Trade:</span> {record.trade_make} {record.trade_model} {record.trade_year}
          {record.trade_title && ` • ${record.trade_title}`}
          {record.trade_miles && ` • ${record.trade_miles} mi`}
          {record.trade_estimated_value && ` • Est: $${record.trade_estimated_value}`}
        </div>
      )}

      {/* Vehicle info for financed/lease */}
      {(record.finance_status === 'financiado' || record.finance_status === 'lease') && record.vehicle_make && (
        <div className="mt-3 pt-3 border-t border-slate-100">
          <div className="flex items-center gap-2 text-sm">
            <span className="bg-amber-100 text-amber-700 px-2 py-1 rounded font-medium">
              {record.vehicle_make} {record.vehicle_year}
            </span>
            {record.sale_month && record.sale_day && record.sale_year && (
              <span className="text-slate-400">
                Sold: {record.sale_month}/{record.sale_day}/{record.sale_year}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Record Status Actions - Always show on all records */}
      <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-slate-100">
        {!record.record_status ? (
          <>
            <Button size="sm" variant="outline" className="text-emerald-600 hover:bg-emerald-50"
              onClick={() => onMarkRecordStatus(record.id, 'completed')}>
              ✓ Marcar como Completado
            </Button>
            <Button size="sm" variant="outline" className="text-slate-500 hover:bg-slate-50"
              onClick={() => onMarkRecordStatus(record.id, 'no_show')}>
              ✗ Mark as No-Show
            </Button>
          </>
        ) : (
          <>
            <span className={`text-sm font-medium flex items-center gap-1 ${record.record_status === 'completed' ? 'text-emerald-600' : 'text-slate-500'}`}>
              {record.record_status === 'completed' ? '✅ Completado' : '❌ No-Show'}
            </span>
            {record.commission_locked && !isAdmin ? (
              <span className="text-xs text-amber-600 flex items-center gap-1">
                🔒 Bloqueado por Admin
              </span>
            ) : (
              <Button size="sm" variant="outline" className="text-slate-400 hover:bg-slate-50"
                onClick={() => onMarkRecordStatus(record.id, null)}>
                ↩ Desmarcar
              </Button>
            )}
          </>
        )}
        {/* Show commission info if available (admin only view) */}
        {isAdmin && record.commission_percentage && record.commission_value && (
          <span className="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded ml-auto">
            💰 {record.commission_percentage}% de ${record.commission_value} = ${((record.commission_percentage / 100) * record.commission_value).toFixed(2)}
          </span>
        )}
      </div>

      {/* Appointment Actions - Only show if has appointment */}
      {appointments[record.id] && appointments[record.id].status === 'scheduled' && (
        <div className="flex gap-2 mt-3 pt-3 border-t border-slate-100">
          <Button size="sm" variant="outline" className="text-emerald-600 hover:bg-emerald-50"
            onClick={() => updateAppointmentStatus(appointments[record.id].id, 'cumplido')}>
            {t('appointments.markCompleted')}
          </Button>
          <Button size="sm" variant="outline" className="text-slate-600 hover:bg-slate-50"
            onClick={() => updateAppointmentStatus(appointments[record.id].id, 'no_show')}>
            {t('appointments.markNoShow')}
          </Button>
        </div>
      )}
    </div>
  );
}

// Co-Signers Section Component
function CoSignersSection({ clientId, cosigners, onRefresh, configLists }) {
  const { t } = useTranslation();
  const [showAdd, setShowAdd] = useState(false);
  const [addMode, setAddMode] = useState('search'); // 'search' or 'new'
  const [searchPhone, setSearchPhone] = useState('');
  const [foundClient, setFoundClient] = useState(null);
  const [newCosigner, setNewCosigner] = useState({
    first_name: '', last_name: '', phone: '', email: '', address: '', apartment: ''
  });
  // Co-signer profile view state
  const [viewingCosigner, setViewingCosigner] = useState(null);
  const [cosignerRecords, setCosignerRecords] = useState([]);
  const [showRecordForm, setShowRecordForm] = useState(false);
  const [newCosignerRecord, setNewCosignerRecord] = useState(null);

  const emptyCosignerRecord = {
    has_id: false, id_type: '',
    has_poi: false, poi_type: '',
    ssn: false, itin: false, self_employed: false,
    has_por: false, por_types: [],
    bank: '', bank_deposit_type: '', direct_deposit_amount: '',
    auto: '', credit: '', auto_loan: '',
    down_payment_type: '', down_payment_types: [], down_payment_cash: '', down_payment_card: '',
    trade_make: '', trade_model: '', trade_year: '', trade_title: '',
    trade_miles: '', trade_plate: '', trade_estimated_value: '',
    dealer: '', finance_status: 'no',
    vehicle_make: '', vehicle_year: '',
    sale_month: '', sale_day: '', sale_year: ''
  };

  const searchByPhone = async () => {
    try {
      const response = await axios.get(`${API}/clients/search/phone/${searchPhone}`);
      setFoundClient(response.data);
    } catch (error) {
      toast.error('Client not found');
      setFoundClient(null);
    }
  };

  const linkCosigner = async () => {
    if (!foundClient) return;
    try {
      await axios.post(`${API}/cosigners`, {
        buyer_client_id: clientId,
        cosigner_client_id: foundClient.id
      });
      setShowAdd(false);
      setSearchPhone('');
      setFoundClient(null);
      onRefresh();
      toast.success('Co-signer linked');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to link co-signer');
    }
  };

  const createAndLinkCosigner = async () => {
    if (!newCosigner.first_name || !newCosigner.last_name || !newCosigner.phone) {
      toast.error('Please fill required fields (Name and Phone)');
      return;
    }
    try {
      const clientRes = await axios.post(`${API}/clients`, newCosigner);
      await axios.post(`${API}/cosigners`, {
        buyer_client_id: clientId,
        cosigner_client_id: clientRes.data.id
      });
      setShowAdd(false);
      setNewCosigner({ first_name: '', last_name: '', phone: '', email: '', address: '', apartment: '' });
      onRefresh();
      toast.success('Co-signer created and linked');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create co-signer');
    }
  };

  const removeCosigner = async (relationId) => {
    if (!window.confirm('Are you sure you want to remove this co-signer?')) return;
    try {
      await axios.delete(`${API}/cosigners/${relationId}`);
      onRefresh();
      toast.success('Co-signer removed');
    } catch (error) {
      toast.error('Failed to remove co-signer');
    }
  };

  // View co-signer profile and load their records
  const viewCosignerProfile = async (cosigner) => {
    setViewingCosigner(cosigner);
    try {
      const response = await axios.get(`${API}/user-records?client_id=${cosigner.id}`);
      setCosignerRecords(response.data);
    } catch (error) {
      console.error('Error loading co-signer records:', error);
      setCosignerRecords([]);
    }
  };

  const closeCosignerProfile = () => {
    setViewingCosigner(null);
    setCosignerRecords([]);
    setShowRecordForm(false);
    setNewCosignerRecord(null);
    setEditingCosignerRecord(null);
    setEditCosignerRecordData(null);
  };

  const openRecordForm = () => {
    setNewCosignerRecord({ ...emptyCosignerRecord });
    setShowRecordForm(true);
    setEditingCosignerRecord(null);
  };

  // Edit co-signer record
  const [editingCosignerRecord, setEditingCosignerRecord] = useState(null);
  const [editCosignerRecordData, setEditCosignerRecordData] = useState(null);

  const startEditCosignerRecord = (record) => {
    setEditingCosignerRecord(record.id);
    setEditCosignerRecordData({
      has_id: record.has_id || false,
      id_type: record.id_type || '',
      has_poi: record.has_poi || false,
      poi_type: record.poi_type || '',
      ssn: record.ssn || false,
      itin: record.itin || false,
      self_employed: record.self_employed || false,
      has_por: record.has_por || false,
      por_types: record.por_types || [],
      bank: record.bank || '',
      bank_deposit_type: record.bank_deposit_type || '',
      direct_deposit_amount: record.direct_deposit_amount || '',
      auto: record.auto || '',
      credit: record.credit || '',
      auto_loan: record.auto_loan || '',
      down_payment_type: record.down_payment_type || '',
      down_payment_types: record.down_payment_types || (record.down_payment_type ? record.down_payment_type.split(', ').filter(t => t) : []),
      down_payment_cash: record.down_payment_cash || '',
      down_payment_card: record.down_payment_card || '',
      trade_make: record.trade_make || '',
      trade_model: record.trade_model || '',
      trade_year: record.trade_year || '',
      trade_title: record.trade_title || '',
      trade_miles: record.trade_miles || '',
      trade_plate: record.trade_plate || '',
      trade_estimated_value: record.trade_estimated_value || '',
      dealer: record.dealer || '',
      finance_status: record.finance_status || 'no',
      vehicle_make: record.vehicle_make || '',
      vehicle_year: record.vehicle_year || '',
      sale_month: record.sale_month?.toString() || '',
      sale_day: record.sale_day?.toString() || '',
      sale_year: record.sale_year?.toString() || ''
    });
    setShowRecordForm(false);
  };

  const saveEditCosignerRecord = async () => {
    if (!editingCosignerRecord || !editCosignerRecordData || !viewingCosigner) return;
    try {
      await axios.put(`${API}/user-records/${editingCosignerRecord}`, {
        client_id: viewingCosigner.id,
        ...editCosignerRecordData,
        sale_month: editCosignerRecordData.sale_month ? parseInt(editCosignerRecordData.sale_month) : null,
        sale_day: editCosignerRecordData.sale_day ? parseInt(editCosignerRecordData.sale_day) : null,
        sale_year: editCosignerRecordData.sale_year ? parseInt(editCosignerRecordData.sale_year) : null
      });
      toast.success('Record actualizado');
      setEditingCosignerRecord(null);
      setEditCosignerRecordData(null);
      // Reload records
      const response = await axios.get(`${API}/user-records?client_id=${viewingCosigner.id}`);
      setCosignerRecords(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al actualizar');
    }
  };

  const cancelEditCosignerRecord = () => {
    setEditingCosignerRecord(null);
    setEditCosignerRecordData(null);
  };

  const deleteCosignerRecord = async (recordId) => {
    if (!window.confirm('¿Está seguro de eliminar este record?')) return;
    try {
      await axios.delete(`${API}/user-records/${recordId}`);
      toast.success('Record eliminado');
      // Reload records
      const response = await axios.get(`${API}/user-records?client_id=${viewingCosigner.id}`);
      setCosignerRecords(response.data);
    } catch (error) {
      toast.error('Error al eliminar record');
    }
  };

  const saveCosignerRecord = async () => {
    if (!viewingCosigner || !newCosignerRecord) return;
    try {
      await axios.post(`${API}/user-records`, {
        client_id: viewingCosigner.id,
        ...newCosignerRecord,
        sale_month: newCosignerRecord.sale_month ? parseInt(newCosignerRecord.sale_month) : null,
        sale_day: newCosignerRecord.sale_day ? parseInt(newCosignerRecord.sale_day) : null,
        sale_year: newCosignerRecord.sale_year ? parseInt(newCosignerRecord.sale_year) : null
      });
      toast.success('Record saved for co-signer');
      setShowRecordForm(false);
      setNewCosignerRecord(null);
      // Reload co-signer records
      const response = await axios.get(`${API}/user-records?client_id=${viewingCosigner.id}`);
      setCosignerRecords(response.data);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save record');
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-semibold text-slate-700">
          {t('cosigner.title')} {cosigners.length > 0 && `(${cosigners.length})`}
        </h4>
        <Button size="sm" variant="outline" onClick={() => { setShowAdd(!showAdd); setAddMode('search'); }} data-testid="add-cosigner-btn">
          <UserPlus className="w-4 h-4 mr-1" />
          {t('cosigner.add')}
        </Button>
      </div>

      {/* Existing Co-Signers */}
      {cosigners.length > 0 && (
        <div className="space-y-2 mb-3">
          {cosigners.map((relation) => (
            <div key={relation.id} className="bg-white rounded-lg border border-purple-200 overflow-hidden">
              {/* Co-signer Header - Clickable */}
              <div 
                className="flex items-center justify-between p-3 cursor-pointer hover:bg-purple-50 transition-colors"
                onClick={() => viewCosignerProfile(relation.cosigner)}
              >
                <div className="flex items-center gap-3">
                  <span className="cosigner-badge">CO-SIGNER</span>
                  <div>
                    <span className="font-medium text-purple-700 hover:underline">
                      {relation.cosigner?.first_name} {relation.cosigner?.last_name}
                    </span>
                    <div className="text-sm text-slate-400">
                      {relation.cosigner?.phone}
                      {relation.cosigner?.email && ` • ${relation.cosigner?.email}`}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <ChevronRight className="w-4 h-4 text-purple-400" />
                  <Button 
                    size="sm" 
                    variant="ghost" 
                    onClick={(e) => { e.stopPropagation(); removeCosigner(relation.id); }}
                  >
                    <Trash2 className="w-4 h-4 text-slate-400" />
                  </Button>
                </div>
              </div>

              {/* Co-signer Profile Expanded View */}
              {viewingCosigner?.id === relation.cosigner?.id && (
                <div className="border-t border-purple-200 bg-purple-50/50 p-4">
                  {/* Profile Header */}
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h5 className="font-semibold text-purple-800">
                        Perfil: {viewingCosigner.first_name} {viewingCosigner.last_name}
                      </h5>
                      <p className="text-sm text-slate-500">
                        {viewingCosigner.phone} • {viewingCosigner.email || 'Sin email'}
                      </p>
                      {viewingCosigner.address && (
                        <p className="text-xs text-slate-400">{viewingCosigner.address}</p>
                      )}
                    </div>
                    <Button size="sm" variant="ghost" onClick={closeCosignerProfile}>
                      <X className="w-4 h-4" />
                    </Button>
                  </div>

                  {/* Co-signer Records Section */}
                  <div className="bg-white rounded-lg border border-purple-200 p-3">
                    <div className="flex items-center justify-between mb-3">
                      <h6 className="font-medium text-slate-700 flex items-center gap-2">
                        <FileText className="w-4 h-4" />
                        Records ({cosignerRecords.length})
                      </h6>
                      {!showRecordForm && (
                        <Button size="sm" variant="outline" onClick={openRecordForm}>
                          <Plus className="w-3 h-3 mr-1" />
                          Agregar Record
                        </Button>
                      )}
                    </div>

                    {/* Existing Records for Co-signer */}
                    {cosignerRecords.length > 0 && !showRecordForm && (
                      <div className="space-y-2 mb-3">
                        {cosignerRecords.map((rec) => (
                          <div key={rec.id}>
                            {editingCosignerRecord === rec.id ? (
                              /* Edit Form for this record */
                              <div className="bg-slate-50 rounded-lg p-3 border border-purple-200">
                                <h6 className="font-medium text-slate-700 text-sm mb-3">Editar Record</h6>
                                
                                {/* ID & POI Row */}
                                <div className="grid grid-cols-2 gap-3 mb-3">
                                  <div className="space-y-2">
                                    <div className="flex items-center gap-2">
                                      <Checkbox
                                        checked={editCosignerRecordData.has_id}
                                        onCheckedChange={(checked) => setEditCosignerRecordData({ ...editCosignerRecordData, has_id: checked })}
                                      />
                                      <Label className="text-sm font-medium">ID</Label>
                                    </div>
                                    {editCosignerRecordData.has_id && (
                                      <Select value={editCosignerRecordData.id_type} onValueChange={(v) => setEditCosignerRecordData({ ...editCosignerRecordData, id_type: v })}>
                                        <SelectTrigger className="h-8 text-sm"><SelectValue placeholder="Tipo ID" /></SelectTrigger>
                                        <SelectContent>
                                          {configLists?.id_type?.map((item) => (
                                            <SelectItem key={item.id} value={item.name}>{item.name}</SelectItem>
                                          ))}
                                        </SelectContent>
                                      </Select>
                                    )}
                                  </div>
                                  <div className="space-y-2">
                                    <div className="flex items-center gap-2">
                                      <Checkbox
                                        checked={editCosignerRecordData.has_poi}
                                        onCheckedChange={(checked) => setEditCosignerRecordData({ ...editCosignerRecordData, has_poi: checked })}
                                      />
                                      <Label className="text-sm font-medium">POI</Label>
                                    </div>
                                    {editCosignerRecordData.has_poi && (
                                      <Select value={editCosignerRecordData.poi_type} onValueChange={(v) => setEditCosignerRecordData({ ...editCosignerRecordData, poi_type: v })}>
                                        <SelectTrigger className="h-8 text-sm"><SelectValue placeholder="Tipo POI" /></SelectTrigger>
                                        <SelectContent>
                                          {configLists?.poi_type?.map((item) => (
                                            <SelectItem key={item.id} value={item.name}>{item.name}</SelectItem>
                                          ))}
                                        </SelectContent>
                                      </Select>
                                    )}
                                  </div>
                                </div>

                                {/* Checkboxes */}
                                <div className="flex flex-wrap gap-3 mb-3">
                                  <div className="flex items-center gap-1">
                                    <Checkbox checked={editCosignerRecordData.ssn} onCheckedChange={(c) => setEditCosignerRecordData({ ...editCosignerRecordData, ssn: c })} />
                                    <Label className="text-xs">SSN</Label>
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <Checkbox checked={editCosignerRecordData.itin} onCheckedChange={(c) => setEditCosignerRecordData({ ...editCosignerRecordData, itin: c })} />
                                    <Label className="text-xs">ITIN</Label>
                                  </div>
                                  <div className="flex items-center gap-1">
                                    <Checkbox checked={editCosignerRecordData.self_employed} onCheckedChange={(c) => setEditCosignerRecordData({ ...editCosignerRecordData, self_employed: c })} />
                                    <Label className="text-xs">Self Employed</Label>
                                  </div>
                                </div>

                                {/* Bank Row */}
                                <div className="grid grid-cols-2 gap-2 mb-3">
                                  <Select value={editCosignerRecordData.bank} onValueChange={(v) => setEditCosignerRecordData({ ...editCosignerRecordData, bank: v })}>
                                    <SelectTrigger className="h-8 text-sm"><SelectValue placeholder="Bank" /></SelectTrigger>
                                    <SelectContent className="max-h-48">
                                      {configLists?.banks?.map((b) => (
                                        <SelectItem key={b.id} value={b.name}>{b.name}</SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                  <Select value={editCosignerRecordData.bank_deposit_type} onValueChange={(v) => setEditCosignerRecordData({ ...editCosignerRecordData, bank_deposit_type: v, direct_deposit_amount: v !== 'Deposito Directo' ? '' : editCosignerRecordData.direct_deposit_amount })}>
                                    <SelectTrigger className="h-8 text-sm"><SelectValue placeholder="Tipo Depósito" /></SelectTrigger>
                                    <SelectContent>
                                      <SelectItem value="Deposito Directo">Deposito Directo</SelectItem>
                                      <SelectItem value="No deposito directo">No deposito directo</SelectItem>
                                    </SelectContent>
                                  </Select>
                                </div>

                                {/* Direct Deposit Amount */}
                                {editCosignerRecordData.bank_deposit_type === 'Deposito Directo' && (
                                  <div className="mb-3">
                                    <Input placeholder="Monto Depósito Directo $" value={editCosignerRecordData.direct_deposit_amount || ''} onChange={(e) => setEditCosignerRecordData({ ...editCosignerRecordData, direct_deposit_amount: e.target.value })} className="h-8 text-sm max-w-xs" />
                                  </div>
                                )}

                                {/* Credit & Auto */}
                                <div className="grid grid-cols-3 gap-2 mb-3">
                                  <Input placeholder="Credit" value={editCosignerRecordData.credit} onChange={(e) => setEditCosignerRecordData({ ...editCosignerRecordData, credit: e.target.value })} className="h-8 text-sm" />
                                  <Select value={editCosignerRecordData.auto} onValueChange={(v) => setEditCosignerRecordData({ ...editCosignerRecordData, auto: v })}>
                                    <SelectTrigger className="h-8 text-sm"><SelectValue placeholder="Auto" /></SelectTrigger>
                                    <SelectContent className="max-h-48">
                                      {configLists?.cars?.map((c) => (
                                        <SelectItem key={c.id} value={c.name}>{c.name}</SelectItem>
                                      ))}
                                    </SelectContent>
                                  </Select>
                                  <Input placeholder="Auto Loan" value={editCosignerRecordData.auto_loan} onChange={(e) => setEditCosignerRecordData({ ...editCosignerRecordData, auto_loan: e.target.value })} className="h-8 text-sm" />
                                </div>

                                {/* Down Payment - Multi-select */}
                                <div className="mb-3">
                                  <div className="flex items-center gap-2 mb-2">
                                    <span className="text-xs text-slate-500">Down (puede seleccionar varios):</span>
                                    {['Cash', 'Tarjeta', 'Trade'].map((type) => (
                                      <div key={type} className="flex items-center gap-1">
                                        <Checkbox
                                          checked={(editCosignerRecordData.down_payment_types || (editCosignerRecordData.down_payment_type ? editCosignerRecordData.down_payment_type.split(', ') : [])).includes(type)}
                                          onCheckedChange={(checked) => {
                                            const currentTypes = editCosignerRecordData.down_payment_types || (editCosignerRecordData.down_payment_type ? editCosignerRecordData.down_payment_type.split(', ').filter(t => t) : []);
                                            const newTypes = checked ? [...currentTypes, type] : currentTypes.filter(t => t !== type);
                                            setEditCosignerRecordData({ 
                                              ...editCosignerRecordData, 
                                              down_payment_types: newTypes,
                                              down_payment_type: newTypes.join(', '),
                                              down_payment_cash: !newTypes.includes('Cash') ? '' : editCosignerRecordData.down_payment_cash,
                                              down_payment_card: !newTypes.includes('Tarjeta') ? '' : editCosignerRecordData.down_payment_card
                                            });
                                          }}
                                        />
                                        <Label className="text-xs">{type}</Label>
                                      </div>
                                    ))}
                                  </div>
                                  <div className="flex flex-wrap gap-2">
                                    {(editCosignerRecordData.down_payment_types || (editCosignerRecordData.down_payment_type ? editCosignerRecordData.down_payment_type.split(', ') : [])).includes('Cash') && (
                                      <Input placeholder="Monto Cash $" value={editCosignerRecordData.down_payment_cash || ''} onChange={(e) => setEditCosignerRecordData({ ...editCosignerRecordData, down_payment_cash: e.target.value })} className="h-7 w-28 text-sm" />
                                    )}
                                    {(editCosignerRecordData.down_payment_types || (editCosignerRecordData.down_payment_type ? editCosignerRecordData.down_payment_type.split(', ') : [])).includes('Tarjeta') && (
                                      <Input placeholder="Monto Tarjeta $" value={editCosignerRecordData.down_payment_card || ''} onChange={(e) => setEditCosignerRecordData({ ...editCosignerRecordData, down_payment_card: e.target.value })} className="h-7 w-28 text-sm" />
                                    )}
                                  </div>
                                </div>

                                {/* Action Buttons */}
                                <div className="flex gap-2 pt-2">
                                  <Button size="sm" variant="outline" onClick={cancelEditCosignerRecord}>Cancelar</Button>
                                  <Button size="sm" onClick={saveEditCosignerRecord}>Guardar Cambios</Button>
                                </div>
                              </div>
                            ) : (
                              /* Display Record */
                              <div className="bg-slate-50 rounded p-2 text-sm flex items-start justify-between">
                                <div className="flex-1">
                                  <div className="flex flex-wrap gap-1 mb-1">
                                    {rec.has_id && <span className="bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded text-xs">ID: {rec.id_type}</span>}
                                    {rec.has_poi && <span className="bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded text-xs">POI: {rec.poi_type}</span>}
                                    {rec.ssn && <span className="bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded text-xs">SSN</span>}
                                    {rec.itin && <span className="bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded text-xs">ITIN</span>}
                                    {rec.self_employed && <span className="bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded text-xs">Self Employed</span>}
                                  </div>
                                  <div className="text-slate-500 text-xs space-y-0.5">
                                    <div>
                                      {rec.bank && `Bank: ${rec.bank}`}
                                      {rec.bank_deposit_type && ` (${rec.bank_deposit_type})`}
                                      {rec.bank_deposit_type === 'Deposito Directo' && rec.direct_deposit_amount && ` - $${rec.direct_deposit_amount}`}
                                    </div>
                                    <div>
                                      {rec.credit && `Credit: ${rec.credit}`}
                                      {rec.auto && ` • Auto: ${rec.auto}`}
                                      {rec.auto_loan && ` • Auto Loan: $${rec.auto_loan}`}
                                    </div>
                                    {rec.down_payment_type && (
                                      <div>
                                        Down: {rec.down_payment_type}
                                        {rec.down_payment_type.includes('Cash') && rec.down_payment_cash && ` (Cash: $${rec.down_payment_cash})`}
                                        {rec.down_payment_type.includes('Tarjeta') && rec.down_payment_card && ` (Tarjeta: $${rec.down_payment_card})`}
                                      </div>
                                    )}
                                    {rec.down_payment_type && rec.down_payment_type.includes('Trade') && rec.trade_make && (
                                      <div>Trade: {rec.trade_make} {rec.trade_model} {rec.trade_year} {rec.trade_estimated_value && `- Est: $${rec.trade_estimated_value}`}</div>
                                    )}
                                  </div>
                                </div>
                                <div className="flex gap-1 ml-2">
                                  <Button size="sm" variant="ghost" onClick={() => startEditCosignerRecord(rec)} className="h-7 w-7 p-0">
                                    <RefreshCw className="w-3 h-3 text-slate-400" />
                                  </Button>
                                  <Button size="sm" variant="ghost" onClick={() => deleteCosignerRecord(rec.id)} className="h-7 w-7 p-0">
                                    <Trash2 className="w-3 h-3 text-red-400" />
                                  </Button>
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}

                    {cosignerRecords.length === 0 && !showRecordForm && (
                      <p className="text-sm text-slate-400 italic">No hay records para este co-signer</p>
                    )}

                    {/* Add Record Form for Co-signer */}
                    {showRecordForm && newCosignerRecord && (
                      <div className="space-y-3 mt-3 p-3 bg-slate-50 rounded-lg border">
                        <h6 className="font-medium text-slate-700 text-sm">Nuevo Record para Co-signer</h6>
                        
                        {/* ID & POI Row */}
                        <div className="grid grid-cols-2 gap-3">
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <Checkbox
                                checked={newCosignerRecord.has_id}
                                onCheckedChange={(checked) => setNewCosignerRecord({ ...newCosignerRecord, has_id: checked })}
                                id="cs-has_id"
                              />
                              <Label htmlFor="cs-has_id" className="text-sm font-medium">ID</Label>
                            </div>
                            {newCosignerRecord.has_id && (
                              <Select value={newCosignerRecord.id_type} onValueChange={(v) => setNewCosignerRecord({ ...newCosignerRecord, id_type: v })}>
                                <SelectTrigger className="h-8 text-sm">
                                  <SelectValue placeholder="Tipo ID" />
                                </SelectTrigger>
                                <SelectContent>
                                  {configLists?.id_type?.map((item) => (
                                    <SelectItem key={item.id} value={item.name}>{item.name}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            )}
                          </div>
                          <div className="space-y-2">
                            <div className="flex items-center gap-2">
                              <Checkbox
                                checked={newCosignerRecord.has_poi}
                                onCheckedChange={(checked) => setNewCosignerRecord({ ...newCosignerRecord, has_poi: checked })}
                                id="cs-has_poi"
                              />
                              <Label htmlFor="cs-has_poi" className="text-sm font-medium">POI</Label>
                            </div>
                            {newCosignerRecord.has_poi && (
                              <Select value={newCosignerRecord.poi_type} onValueChange={(v) => setNewCosignerRecord({ ...newCosignerRecord, poi_type: v })}>
                                <SelectTrigger className="h-8 text-sm">
                                  <SelectValue placeholder="Tipo POI" />
                                </SelectTrigger>
                                <SelectContent>
                                  {configLists?.poi_type?.map((item) => (
                                    <SelectItem key={item.id} value={item.name}>{item.name}</SelectItem>
                                  ))}
                                </SelectContent>
                              </Select>
                            )}
                          </div>
                        </div>

                        {/* Checkboxes Row */}
                        <div className="flex flex-wrap gap-3">
                          <div className="flex items-center gap-1">
                            <Checkbox checked={newCosignerRecord.ssn} onCheckedChange={(c) => setNewCosignerRecord({ ...newCosignerRecord, ssn: c })} id="cs-ssn" />
                            <Label htmlFor="cs-ssn" className="text-xs">SSN</Label>
                          </div>
                          <div className="flex items-center gap-1">
                            <Checkbox checked={newCosignerRecord.itin} onCheckedChange={(c) => setNewCosignerRecord({ ...newCosignerRecord, itin: c })} id="cs-itin" />
                            <Label htmlFor="cs-itin" className="text-xs">ITIN</Label>
                          </div>
                          <div className="flex items-center gap-1">
                            <Checkbox checked={newCosignerRecord.self_employed} onCheckedChange={(c) => setNewCosignerRecord({ ...newCosignerRecord, self_employed: c })} id="cs-se" />
                            <Label htmlFor="cs-se" className="text-xs">Self Employed</Label>
                          </div>
                        </div>

                        {/* POR */}
                        <div className="space-y-2">
                          <div className="flex items-center gap-2">
                            <Checkbox
                              checked={newCosignerRecord.has_por}
                              onCheckedChange={(checked) => setNewCosignerRecord({ ...newCosignerRecord, has_por: checked })}
                              id="cs-has_por"
                            />
                            <Label htmlFor="cs-has_por" className="text-sm font-medium">POR</Label>
                          </div>
                          {newCosignerRecord.has_por && (
                            <div className="flex flex-wrap gap-2 ml-5">
                              {configLists?.por_type?.map((item) => (
                                <div key={item.id} className="flex items-center gap-1">
                                  <Checkbox
                                    checked={(newCosignerRecord.por_types || []).includes(item.name)}
                                    onCheckedChange={(checked) => {
                                      const current = newCosignerRecord.por_types || [];
                                      setNewCosignerRecord({
                                        ...newCosignerRecord,
                                        por_types: checked ? [...current, item.name] : current.filter(t => t !== item.name)
                                      });
                                    }}
                                  />
                                  <Label className="text-xs">{item.name}</Label>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>

                        {/* Bank Row */}
                        <div className="grid grid-cols-2 gap-2">
                          <Select value={newCosignerRecord.bank} onValueChange={(v) => setNewCosignerRecord({ ...newCosignerRecord, bank: v })}>
                            <SelectTrigger className="h-8 text-sm">
                              <SelectValue placeholder="Bank" />
                            </SelectTrigger>
                            <SelectContent className="max-h-48">
                              {configLists?.banks?.map((b) => (
                                <SelectItem key={b.id} value={b.name}>{b.name}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <Select value={newCosignerRecord.bank_deposit_type} onValueChange={(v) => setNewCosignerRecord({ ...newCosignerRecord, bank_deposit_type: v, direct_deposit_amount: v !== 'Deposito Directo' ? '' : newCosignerRecord.direct_deposit_amount })}>
                            <SelectTrigger className="h-8 text-sm">
                              <SelectValue placeholder="Tipo Depósito" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="Deposito Directo">Deposito Directo</SelectItem>
                              <SelectItem value="No deposito directo">No deposito directo</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        {/* Direct Deposit Amount */}
                        {newCosignerRecord.bank_deposit_type === 'Deposito Directo' && (
                          <div>
                            <Input placeholder="Monto Depósito Directo $" value={newCosignerRecord.direct_deposit_amount || ''} onChange={(e) => setNewCosignerRecord({ ...newCosignerRecord, direct_deposit_amount: e.target.value })} className="h-8 text-sm max-w-xs" />
                          </div>
                        )}

                        {/* Credit & Auto */}
                        <div className="grid grid-cols-3 gap-2">
                          <Input placeholder="Credit" value={newCosignerRecord.credit} onChange={(e) => setNewCosignerRecord({ ...newCosignerRecord, credit: e.target.value })} className="h-8 text-sm" />
                          <Select value={newCosignerRecord.auto} onValueChange={(v) => setNewCosignerRecord({ ...newCosignerRecord, auto: v })}>
                            <SelectTrigger className="h-8 text-sm">
                              <SelectValue placeholder="Auto" />
                            </SelectTrigger>
                            <SelectContent className="max-h-48">
                              {configLists?.cars?.map((c) => (
                                <SelectItem key={c.id} value={c.name}>{c.name}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          <Input placeholder="Auto Loan" value={newCosignerRecord.auto_loan} onChange={(e) => setNewCosignerRecord({ ...newCosignerRecord, auto_loan: e.target.value })} className="h-8 text-sm" />
                        </div>

                        {/* Down Payment - Multi-select */}
                        <div>
                          <div className="flex items-center gap-2 mb-2">
                            <span className="text-xs text-slate-500">Down (puede seleccionar varios):</span>
                            {['Cash', 'Tarjeta', 'Trade'].map((type) => (
                              <div key={type} className="flex items-center gap-1">
                                <Checkbox
                                  checked={(newCosignerRecord.down_payment_types || []).includes(type)}
                                  onCheckedChange={(checked) => {
                                    const currentTypes = newCosignerRecord.down_payment_types || [];
                                    const newTypes = checked ? [...currentTypes, type] : currentTypes.filter(t => t !== type);
                                    setNewCosignerRecord({ 
                                      ...newCosignerRecord, 
                                      down_payment_types: newTypes,
                                      down_payment_type: newTypes.join(', '),
                                      down_payment_cash: !newTypes.includes('Cash') ? '' : newCosignerRecord.down_payment_cash,
                                      down_payment_card: !newTypes.includes('Tarjeta') ? '' : newCosignerRecord.down_payment_card
                                    });
                                  }}
                                />
                                <Label className="text-xs">{type}</Label>
                              </div>
                            ))}
                          </div>
                          <div className="flex flex-wrap gap-2">
                            {(newCosignerRecord.down_payment_types || []).includes('Cash') && (
                              <Input placeholder="Monto Cash $" value={newCosignerRecord.down_payment_cash || ''} onChange={(e) => setNewCosignerRecord({ ...newCosignerRecord, down_payment_cash: e.target.value })} className="h-7 w-28 text-sm" />
                            )}
                            {(newCosignerRecord.down_payment_types || []).includes('Tarjeta') && (
                              <Input placeholder="Monto Tarjeta $" value={newCosignerRecord.down_payment_card || ''} onChange={(e) => setNewCosignerRecord({ ...newCosignerRecord, down_payment_card: e.target.value })} className="h-7 w-28 text-sm" />
                            )}
                          </div>
                        </div>

                        {/* Trade-in details compact */}
                        {(newCosignerRecord.down_payment_types || []).includes('Trade') && (
                          <div className="grid grid-cols-3 gap-2 p-2 bg-white rounded border text-xs">
                            <Input placeholder="Make" value={newCosignerRecord.trade_make} onChange={(e) => setNewCosignerRecord({ ...newCosignerRecord, trade_make: e.target.value })} className="h-7 text-xs" />
                            <Input placeholder="Model" value={newCosignerRecord.trade_model} onChange={(e) => setNewCosignerRecord({ ...newCosignerRecord, trade_model: e.target.value })} className="h-7 text-xs" />
                            <Input placeholder="Year" value={newCosignerRecord.trade_year} onChange={(e) => setNewCosignerRecord({ ...newCosignerRecord, trade_year: e.target.value })} className="h-7 text-xs" />
                            <Input placeholder="Miles" value={newCosignerRecord.trade_miles} onChange={(e) => setNewCosignerRecord({ ...newCosignerRecord, trade_miles: e.target.value })} className="h-7 text-xs" />
                            <Input placeholder="Est. Value" value={newCosignerRecord.trade_estimated_value} onChange={(e) => setNewCosignerRecord({ ...newCosignerRecord, trade_estimated_value: e.target.value })} className="h-7 text-xs" />
                          </div>
                        )}

                        {/* Action Buttons */}
                        <div className="flex gap-2 pt-2">
                          <Button size="sm" variant="outline" onClick={() => { setShowRecordForm(false); setNewCosignerRecord(null); }}>
                            Cancelar
                          </Button>
                          <Button size="sm" onClick={saveCosignerRecord}>
                            Guardar Record
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Add Co-Signer */}
      {showAdd && (
        <div className="bg-white rounded-lg border border-purple-200 p-4">
          {/* Mode Tabs */}
          <div className="flex gap-2 mb-4">
            <Button 
              size="sm" 
              variant={addMode === 'search' ? 'default' : 'outline'}
              onClick={() => setAddMode('search')}
            >
              {t('cosigner.existing')}
            </Button>
            <Button 
              size="sm" 
              variant={addMode === 'new' ? 'default' : 'outline'}
              onClick={() => setAddMode('new')}
            >
              {t('cosigner.new')}
            </Button>
          </div>

          {addMode === 'search' ? (
            <>
              <div className="flex gap-2 mb-3">
                <Input
                  placeholder={t('cosigner.searchPhone')}
                  value={searchPhone}
                  onChange={(e) => setSearchPhone(e.target.value)}
                  data-testid="cosigner-search-phone"
                />
                <Button onClick={searchByPhone} data-testid="search-cosigner-btn">
                  <Search className="w-4 h-4" />
                </Button>
              </div>
              {foundClient && (
                <div className="flex items-center justify-between bg-slate-50 rounded-lg p-3">
                  <div>
                    <p className="font-medium">{foundClient.first_name} {foundClient.last_name}</p>
                    <p className="text-sm text-slate-400">{foundClient.phone}</p>
                  </div>
                  <Button size="sm" onClick={linkCosigner} data-testid="link-cosigner-btn">Link</Button>
                </div>
              )}
            </>
          ) : (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <Label className="form-label">{t('clients.firstName')} *</Label>
                  <Input
                    value={newCosigner.first_name}
                    onChange={(e) => setNewCosigner({ ...newCosigner, first_name: e.target.value })}
                    required
                  />
                </div>
                <div>
                  <Label className="form-label">{t('clients.lastName')} *</Label>
                  <Input
                    value={newCosigner.last_name}
                    onChange={(e) => setNewCosigner({ ...newCosigner, last_name: e.target.value })}
                    required
                  />
                </div>
              </div>
              <div>
                <Label className="form-label">{t('clients.phone')} *</Label>
                <Input
                  type="tel"
                  value={newCosigner.phone}
                  onChange={(e) => setNewCosigner({ ...newCosigner, phone: e.target.value })}
                  placeholder="+1 555 123 4567"
                  required
                />
              </div>
              <div>
                <Label className="form-label">{t('clients.email')}</Label>
                <Input
                  type="email"
                  value={newCosigner.email}
                  onChange={(e) => setNewCosigner({ ...newCosigner, email: e.target.value })}
                />
              </div>
              <div>
                <Label className="form-label">{t('clients.address')}</Label>
                <AddressAutocomplete
                  value={newCosigner.address}
                  onChange={(value) => setNewCosigner({ ...newCosigner, address: value })}
                  placeholder="Start typing an address..."
                />
              </div>
              <div>
                <Label className="form-label">{t('clients.apartment')}</Label>
                <Input
                  value={newCosigner.apartment}
                  onChange={(e) => setNewCosigner({ ...newCosigner, apartment: e.target.value })}
                />
              </div>
              <div className="flex gap-2 pt-2">
                <Button variant="outline" size="sm" onClick={() => setShowAdd(false)}>
                  {t('common.cancel')}
                </Button>
                <Button size="sm" onClick={createAndLinkCosigner} data-testid="create-cosigner-btn">
                  {t('common.save')}
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Client Info Modal Component
function ClientInfoModal({ client, onClose, onSendDocsSMS, onSendDocsEmail, onRefresh, isAdmin }) {
  const { t } = useTranslation();
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({
    first_name: client.first_name,
    last_name: client.last_name,
    phone: client.phone,
    email: client.email || '',
    address: client.address || '',
    apartment: client.apartment || ''
  });
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(null); // 'id', 'income', or 'residence'
  const [uploading, setUploading] = useState(null); // 'id', 'income', or 'residence'
  const [clientDocs, setClientDocs] = useState({
    id_uploaded: client.id_uploaded || false,
    income_proof_uploaded: client.income_proof_uploaded || false,
    residence_proof_uploaded: client.residence_proof_uploaded || false,
    id_file_url: client.id_file_url || null,
    income_proof_file_url: client.income_proof_file_url || null,
    residence_proof_file_url: client.residence_proof_file_url || null
  });

  const handleSave = async () => {
    try {
      await axios.put(`${API}/clients/${client.id}`, editData);
      toast.success('Client updated');
      setIsEditing(false);
      onRefresh();
      onClose(); // Close modal to show updated data in list
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update');
    }
  };

  const handleUploadDocument = async (docType, file) => {
    if (!file) return;
    
    setUploading(docType);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('doc_type', docType);
      
      const response = await axios.post(`${API}/clients/${client.id}/documents/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      // Update local state
      if (docType === 'id') {
        setClientDocs(prev => ({ ...prev, id_uploaded: true, id_file_url: response.data.file_url }));
      } else if (docType === 'income') {
        setClientDocs(prev => ({ ...prev, income_proof_uploaded: true, income_proof_file_url: response.data.file_url }));
      } else if (docType === 'residence') {
        setClientDocs(prev => ({ ...prev, residence_proof_uploaded: true, residence_proof_file_url: response.data.file_url }));
      }
      
      toast.success('Documento subido correctamente');
      onRefresh();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Error al subir documento');
    } finally {
      setUploading(null);
    }
  };

  const handleDownloadDocument = async (docType) => {
    try {
      const response = await axios.get(`${API}/clients/${client.id}/documents/download/${docType}`, {
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${client.first_name}_${client.last_name}_${docType}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      toast.error('Error al descargar documento');
    }
  };

  const handleDeleteDocument = async (docType) => {
    try {
      const updateData = docType === 'id' 
        ? { id_uploaded: false }
        : docType === 'income' 
        ? { income_proof_uploaded: false }
        : { residence_proof_uploaded: false };
      
      await axios.put(`${API}/clients/${client.id}/documents`, null, {
        params: updateData
      });
      
      // Update local state
      if (docType === 'id') {
        setClientDocs(prev => ({ ...prev, id_uploaded: false, id_file_url: null }));
      } else if (docType === 'income') {
        setClientDocs(prev => ({ ...prev, income_proof_uploaded: false, income_proof_file_url: null }));
      } else {
        setClientDocs(prev => ({ ...prev, residence_proof_uploaded: false, residence_proof_file_url: null }));
      }
      
      toast.success(`Documento ${docType === 'id' ? 'ID' : docType === 'income' ? 'Comprobante de Ingresos' : 'Comprobante de Residencia'} eliminado`);
      setShowDeleteConfirm(null);
      onRefresh();
    } catch (error) {
      toast.error('Error al eliminar documento');
    }
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle>{t('clients.info')}</DialogTitle>
            {!isEditing && (
              <Button variant="ghost" size="sm" onClick={() => setIsEditing(true)}>
                <RefreshCw className="w-4 h-4 mr-1" />
                Edit
              </Button>
            )}
          </div>
          <p className="text-sm text-slate-500">View and manage client details</p>
        </DialogHeader>
        <div className="space-y-4">
          {isEditing ? (
            // Edit Mode
            <>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="form-label">{t('clients.firstName')}</Label>
                  <Input
                    value={editData.first_name}
                    onChange={(e) => setEditData({ ...editData, first_name: e.target.value })}
                  />
                </div>
                <div>
                  <Label className="form-label">{t('clients.lastName')}</Label>
                  <Input
                    value={editData.last_name}
                    onChange={(e) => setEditData({ ...editData, last_name: e.target.value })}
                  />
                </div>
                <div>
                  <Label className="form-label">{t('clients.phone')}</Label>
                  <Input
                    type="tel"
                    value={editData.phone}
                    onChange={(e) => setEditData({ ...editData, phone: e.target.value })}
                    placeholder="(213) 462-9914"
                  />
                  <p className="text-xs text-slate-400 mt-1">
                    Formato: 10 dígitos - Se agregará +1 automáticamente
                  </p>
                </div>
                <div>
                  <Label className="form-label">{t('clients.email')}</Label>
                  <Input
                    type="email"
                    value={editData.email}
                    onChange={(e) => setEditData({ ...editData, email: e.target.value })}
                  />
                </div>
                <div className="col-span-2">
                  <Label className="form-label">{t('clients.address')}</Label>
                  <AddressAutocomplete
                    value={editData.address}
                    onChange={(value) => setEditData({ ...editData, address: value })}
                    placeholder="Start typing an address..."
                  />
                </div>
                <div className="col-span-2">
                  <Label className="form-label">{t('clients.apartment')}</Label>
                  <Input
                    value={editData.apartment}
                    onChange={(e) => setEditData({ ...editData, apartment: e.target.value })}
                  />
                </div>
              </div>
              <div className="flex gap-2 pt-2">
                <Button variant="outline" onClick={() => setIsEditing(false)}>
                  {t('common.cancel')}
                </Button>
                <Button onClick={handleSave} data-testid="save-client-edit">
                  {t('common.save')}
                </Button>
              </div>
            </>
          ) : (
            // View Mode
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="form-label">{t('clients.firstName')}</Label>
                <p className="font-medium">{client.first_name}</p>
              </div>
              <div>
                <Label className="form-label">{t('clients.lastName')}</Label>
                <p className="font-medium">{client.last_name}</p>
              </div>
              <div>
                <Label className="form-label">{t('clients.phone')}</Label>
                <p className="font-medium">{client.phone}</p>
              </div>
              <div>
                <Label className="form-label">{t('clients.email')}</Label>
                <p className="font-medium">{client.email || '-'}</p>
              </div>
              <div className="col-span-2">
                <Label className="form-label">{t('clients.address')}</Label>
                <p className="font-medium">{client.address || '-'} {client.apartment && `Apt ${client.apartment}`}</p>
              </div>
            </div>
          )}

          {/* Document Status with Upload/Download/Delete */}
          <div>
            <Label className="form-label">{t('clients.documents')}</Label>
            <div className="space-y-2 mt-2">
              {/* ID Document */}
              <div className="flex items-center justify-between bg-slate-50 rounded-lg p-3">
                <div className="flex items-center gap-2">
                  {clientDocs.id_uploaded ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                  ) : (
                    <XCircle className="w-5 h-5 text-slate-300" />
                  )}
                  <span className="text-sm">{t('clients.idUploaded')}</span>
                </div>
                <div className="flex items-center gap-1">
                  {clientDocs.id_uploaded ? (
                    showDeleteConfirm === 'id' ? (
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-red-600">¿Eliminar?</span>
                        <Button size="sm" variant="destructive" onClick={() => handleDeleteDocument('id')}>
                          Sí
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setShowDeleteConfirm(null)}>
                          No
                        </Button>
                      </div>
                    ) : (
                      <>
                        {isAdmin && (
                          <Button size="sm" variant="ghost" onClick={() => handleDownloadDocument('id')} title="Descargar">
                            <Download className="w-4 h-4 text-blue-500" />
                          </Button>
                        )}
                        {isAdmin && (
                          <Button size="sm" variant="ghost" onClick={() => setShowDeleteConfirm('id')} title="Eliminar">
                            <Trash2 className="w-4 h-4 text-red-400" />
                          </Button>
                        )}
                      </>
                    )
                  ) : (
                    <label className="cursor-pointer">
                      <input
                        type="file"
                        className="hidden"
                        accept=".pdf,.jpg,.jpeg,.png"
                        onChange={(e) => handleUploadDocument('id', e.target.files[0])}
                        disabled={uploading === 'id'}
                      />
                      <Button size="sm" variant="outline" asChild disabled={uploading === 'id'}>
                        <span>
                          <Upload className="w-4 h-4 mr-1" />
                          {uploading === 'id' ? 'Subiendo...' : 'Subir'}
                        </span>
                      </Button>
                    </label>
                  )}
                </div>
              </div>
              
              {/* Income Proof */}
              <div className="flex items-center justify-between bg-slate-50 rounded-lg p-3">
                <div className="flex items-center gap-2">
                  {clientDocs.income_proof_uploaded ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                  ) : (
                    <XCircle className="w-5 h-5 text-slate-300" />
                  )}
                  <span className="text-sm">{t('clients.incomeProof')}</span>
                </div>
                <div className="flex items-center gap-1">
                  {clientDocs.income_proof_uploaded ? (
                    showDeleteConfirm === 'income' ? (
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-red-600">¿Eliminar?</span>
                        <Button size="sm" variant="destructive" onClick={() => handleDeleteDocument('income')}>
                          Sí
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setShowDeleteConfirm(null)}>
                          No
                        </Button>
                      </div>
                    ) : (
                      <>
                        {isAdmin && (
                          <Button size="sm" variant="ghost" onClick={() => handleDownloadDocument('income')} title="Descargar">
                            <Download className="w-4 h-4 text-blue-500" />
                          </Button>
                        )}
                        {isAdmin && (
                          <Button size="sm" variant="ghost" onClick={() => setShowDeleteConfirm('income')} title="Eliminar">
                            <Trash2 className="w-4 h-4 text-red-400" />
                          </Button>
                        )}
                      </>
                    )
                  ) : (
                    <label className="cursor-pointer">
                      <input
                        type="file"
                        className="hidden"
                        accept=".pdf,.jpg,.jpeg,.png"
                        onChange={(e) => handleUploadDocument('income', e.target.files[0])}
                        disabled={uploading === 'income'}
                      />
                      <Button size="sm" variant="outline" asChild disabled={uploading === 'income'}>
                        <span>
                          <Upload className="w-4 h-4 mr-1" />
                          {uploading === 'income' ? 'Subiendo...' : 'Subir'}
                        </span>
                      </Button>
                    </label>
                  )}
                </div>
              </div>

              {/* Residence Proof */}
              <div className="flex items-center justify-between bg-slate-50 rounded-lg p-3">
                <div className="flex items-center gap-2">
                  {clientDocs.residence_proof_uploaded ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                  ) : (
                    <XCircle className="w-5 h-5 text-slate-300" />
                  )}
                  <div className="flex items-center gap-1">
                    <Home className="w-4 h-4 text-slate-400" />
                    <span className="text-sm">Comprobante de Residencia</span>
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {clientDocs.residence_proof_uploaded ? (
                    showDeleteConfirm === 'residence' ? (
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-red-600">¿Eliminar?</span>
                        <Button size="sm" variant="destructive" onClick={() => handleDeleteDocument('residence')}>
                          Sí
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => setShowDeleteConfirm(null)}>
                          No
                        </Button>
                      </div>
                    ) : (
                      <>
                        {isAdmin && (
                          <Button size="sm" variant="ghost" onClick={() => handleDownloadDocument('residence')} title="Descargar">
                            <Download className="w-4 h-4 text-blue-500" />
                          </Button>
                        )}
                        {isAdmin && (
                          <Button size="sm" variant="ghost" onClick={() => setShowDeleteConfirm('residence')} title="Eliminar">
                            <Trash2 className="w-4 h-4 text-red-400" />
                          </Button>
                        )}
                      </>
                    )
                  ) : (
                    <label className="cursor-pointer">
                      <input
                        type="file"
                        className="hidden"
                        accept=".pdf,.jpg,.jpeg,.png"
                        onChange={(e) => handleUploadDocument('residence', e.target.files[0])}
                        disabled={uploading === 'residence'}
                      />
                      <Button size="sm" variant="outline" asChild disabled={uploading === 'residence'}>
                        <span>
                          <Upload className="w-4 h-4 mr-1" />
                          {uploading === 'residence' ? 'Subiendo...' : 'Subir'}
                        </span>
                      </Button>
                    </label>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Send Documents Link - SMS and Email */}
          <div className="flex gap-2 pt-4 border-t">
            <Button 
              variant="outline" 
              className="flex-1" 
              onClick={onSendDocsSMS} 
              data-testid="send-docs-sms-btn"
              title="Enviar link por SMS (requiere aprobación A2P)"
            >
              <Send className="w-4 h-4 mr-2" />
              SMS
            </Button>
            <Button 
              variant="default" 
              className="flex-1 bg-green-600 hover:bg-green-700" 
              onClick={() => onSendDocsEmail(client)}
              data-testid="send-docs-email-btn"
              title="Enviar link por Email"
            >
              <Mail className="w-4 h-4 mr-2" />
              Email
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
