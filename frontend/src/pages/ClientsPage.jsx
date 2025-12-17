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
  Send, Trash2, CheckCircle2, XCircle, UserPlus, Phone, RefreshCw
} from 'lucide-react';

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

  const [newClient, setNewClient] = useState({
    first_name: '', last_name: '', phone: '', email: '', address: '', apartment: ''
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
      setNewClient({ first_name: '', last_name: '', phone: '', email: '', address: '', apartment: '' });
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

  const sendAppointmentSMS = async (clientId, appointmentId) => {
    try {
      await axios.post(`${API}/sms/send-appointment-link?client_id=${clientId}&appointment_id=${appointmentId}`);
      toast.success('Appointment SMS sent (mocked)');
    } catch (error) {
      toast.error('Failed to send SMS');
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
                  placeholder="+1 555 123 4567"
                  required
                  data-testid="client-phone"
                />
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
                <Input
                  value={newClient.address}
                  onChange={(e) => setNewClient({ ...newClient, address: e.target.value })}
                  data-testid="client-address"
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
        {filteredClients.length === 0 ? (
          <Card className="dashboard-card">
            <CardContent className="py-12 text-center text-slate-400">
              {t('common.noData')}
            </CardContent>
          </Card>
        ) : (
          filteredClients.map((client) => (
            <Card key={client.id} className="dashboard-card overflow-hidden" data-testid={`client-card-${client.id}`}>
              <Collapsible open={expandedClients[client.id]} onOpenChange={() => toggleClientExpand(client.id)}>
                <CollapsibleTrigger asChild>
                  <div className="flex items-center justify-between p-4 hover:bg-slate-50 cursor-pointer w-full" role="button" tabIndex={0}>
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center text-blue-600 font-semibold">
                        {client.first_name.charAt(0)}
                      </div>
                      <div className="text-left">
                        <p className="font-semibold text-slate-900">
                          {client.first_name} {client.last_name}
                        </p>
                        <p className="text-sm text-slate-500">{client.phone}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      {client.last_record_date && (
                        <div className="text-right hidden sm:block">
                          <p className="text-xs text-slate-400">{t('clients.lastContact')}</p>
                          <p className="text-sm font-medium text-slate-600">{formatDate(client.last_record_date)}</p>
                        </div>
                      )}
                      <div className="flex items-center gap-2">
                        {client.id_uploaded ? (
                          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                        ) : (
                          <XCircle className="w-5 h-5 text-slate-300" />
                        )}
                        {client.income_proof_uploaded ? (
                          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                        ) : (
                          <XCircle className="w-5 h-5 text-slate-300" />
                        )}
                      </div>
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
                      onRefresh={() => fetchClientRecords(client.id)}
                      sendAppointmentSMS={sendAppointmentSMS}
                    />

                    {/* Co-Signers */}
                    <CoSignersSection 
                      clientId={client.id}
                      cosigners={cosigners[client.id] || []}
                      onRefresh={() => fetchClientRecords(client.id)}
                    />
                  </div>
                </CollapsibleContent>
              </Collapsible>
            </Card>
          ))
        )}
      </div>

      {/* Client Info Modal */}
      {selectedClient && (
        <ClientInfoModal 
          client={selectedClient} 
          onClose={() => setSelectedClient(null)}
          onSendDocsSMS={() => sendDocumentsSMS(selectedClient.id)}
          onRefresh={fetchClients}
        />
      )}
    </div>
  );
}

// User Records Section Component
function UserRecordsSection({ clientId, records, appointments, onRefresh, sendAppointmentSMS }) {
  const { t } = useTranslation();
  const { user } = useAuth();
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
    dl: false, checks: false, ssn: false, itin: false,
    auto: '', credit: '', bank: '', auto_loan: '', down_payment: '', dealer: '',
    finance_status: 'no', vehicle_make: '', vehicle_year: '',
    sale_month: '', sale_day: '', sale_year: ''
  };

  const [newRecord, setNewRecord] = useState({ ...emptyRecord });

  const handleCreateAppointment = async () => {
    if (!appointmentData.date || !appointmentData.time) {
      toast.error('Please fill date and time');
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
      
      // Send SMS automatically
      await axios.post(`${API}/sms/send-appointment-link?client_id=${clientId}&appointment_id=${response.data.id}`);
      
      setShowAppointmentForm(null);
      setAppointmentData({ date: '', time: '', dealer: '', language: 'en' });
      onRefresh();
      toast.success('Appointment created and SMS sent to client');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create appointment');
    }
  };

  const handleEditRecord = (record) => {
    setEditingRecord(record.id);
    setEditRecordData({
      dl: record.dl, checks: record.checks, ssn: record.ssn, itin: record.itin,
      auto: record.auto || '', credit: record.credit || '', bank: record.bank || '',
      auto_loan: record.auto_loan || '', down_payment: record.down_payment || '',
      dealer: record.dealer || '', finance_status: record.finance_status || 'no',
      vehicle_make: record.vehicle_make || '', vehicle_year: record.vehicle_year || '',
      sale_month: record.sale_month?.toString() || '', sale_day: record.sale_day?.toString() || '',
      sale_year: record.sale_year?.toString() || ''
    });
  };

  const handleSaveEditRecord = async () => {
    try {
      await axios.put(`${API}/user-records/${editingRecord}`, {
        client_id: clientId,
        ...editRecordData,
        sale_month: editRecordData.sale_month ? parseInt(editRecordData.sale_month) : null,
        sale_day: editRecordData.sale_day ? parseInt(editRecordData.sale_day) : null,
        sale_year: editRecordData.sale_year ? parseInt(editRecordData.sale_year) : null
      });
      setEditingRecord(null);
      setEditRecordData(null);
      onRefresh();
      toast.success('Record updated');
    } catch (error) {
      toast.error('Failed to update record');
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

  // Group records by opportunity number
  const myRecords = records.filter(r => r.salesperson_id === user.id);
  
  // Group by opportunity_number (1-5)
  const opportunityGroups = {};
  myRecords.forEach(record => {
    const oppNum = record.opportunity_number || 1;
    if (!opportunityGroups[oppNum]) opportunityGroups[oppNum] = [];
    opportunityGroups[oppNum].push(record);
  });
  
  // Get the highest opportunity number and check if we can create more
  const maxOpportunity = Math.max(...Object.keys(opportunityGroups).map(Number), 0);
  const latestRecordInLastOpp = opportunityGroups[maxOpportunity]?.[0];
  const canCreateNewOpportunity = maxOpportunity < 5 && latestRecordInLastOpp && 
    (latestRecordInLastOpp.finance_status === 'financiado' || latestRecordInLastOpp.finance_status === 'least');

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
                    clientId={clientId}
                    createAppointment={createAppointment}
                    updateAppointmentStatus={updateAppointmentStatus}
                    t={t}
                    isPurple={oppNum > 1}
                    onOpenAppointmentForm={setShowAppointmentForm}
                    currentUserId={user.id}
                    onEdit={handleEditRecord}
                    onDelete={handleDeleteRecord}
                    isEditing={editingRecord === record.id}
                    editData={editRecordData}
                    setEditData={setEditRecordData}
                    onSaveEdit={handleSaveEditRecord}
                    onCancelEdit={() => { setEditingRecord(null); setEditRecordData(null); }}
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

      {/* Appointment Form Modal */}
      {showAppointmentForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md m-4">
            <h3 className="text-lg font-semibold mb-4">Schedule Appointment</h3>
            <div className="space-y-4">
              <div>
                <Label className="form-label">Date *</Label>
                <Input 
                  type="date" 
                  value={appointmentData.date}
                  onChange={(e) => setAppointmentData({ ...appointmentData, date: e.target.value })}
                />
              </div>
              <div>
                <Label className="form-label">Time *</Label>
                <Input 
                  type="time" 
                  value={appointmentData.time}
                  onChange={(e) => setAppointmentData({ ...appointmentData, time: e.target.value })}
                />
              </div>
              <div>
                <Label className="form-label">Dealer</Label>
                <Input 
                  placeholder="Dealer location"
                  value={appointmentData.dealer}
                  onChange={(e) => setAppointmentData({ ...appointmentData, dealer: e.target.value })}
                />
              </div>
              <div>
                <Label className="form-label">Client Language Preference</Label>
                <Select value={appointmentData.language} onValueChange={(value) => setAppointmentData({ ...appointmentData, language: value })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="en">English</SelectItem>
                    <SelectItem value="es">Español</SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-slate-400 mt-1">The client will receive SMS in this language</p>
              </div>
              <div className="flex gap-2 pt-2">
                <Button variant="outline" onClick={() => setShowAppointmentForm(null)} className="flex-1">
                  Cancel
                </Button>
                <Button onClick={handleCreateAppointment} className="flex-1">
                  Create & Send SMS
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {records.filter(r => r.salesperson_id !== user.id).length > 0 && (
        <div className="text-sm text-slate-400 mt-4 text-center">
          + {records.filter(r => r.salesperson_id !== user.id).length} records from other salespeople
        </div>
      )}

      {/* Add Record Form */}
      {(showAddRecord || showNewOpportunity) && (
        <div className="bg-white rounded-lg border border-blue-200 p-4 mt-3">
          <h5 className="font-medium text-slate-700 mb-3">New Record</h5>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
            {['dl', 'checks', 'ssn', 'itin'].map((field) => (
              <div key={field} className="flex items-center gap-2">
                <Checkbox
                  checked={newRecord[field]}
                  onCheckedChange={(checked) => setNewRecord({ ...newRecord, [field]: checked })}
                  id={`new-${field}`}
                />
                <Label htmlFor={`new-${field}`} className="text-sm uppercase">{t(`records.${field}`)}</Label>
              </div>
            ))}
          </div>
          
          {/* Info fields */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
            <Input placeholder="Auto" value={newRecord.auto} onChange={(e) => setNewRecord({ ...newRecord, auto: e.target.value })} />
            <Input placeholder="Credit" value={newRecord.credit} onChange={(e) => setNewRecord({ ...newRecord, credit: e.target.value })} />
            <Input placeholder="Bank" value={newRecord.bank} onChange={(e) => setNewRecord({ ...newRecord, bank: e.target.value })} />
            <Input placeholder="Auto Loan" value={newRecord.auto_loan} onChange={(e) => setNewRecord({ ...newRecord, auto_loan: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-3">
            <Input placeholder="Down Payment" value={newRecord.down_payment} onChange={(e) => setNewRecord({ ...newRecord, down_payment: e.target.value })} />
            <Input placeholder="Dealer" value={newRecord.dealer} onChange={(e) => setNewRecord({ ...newRecord, dealer: e.target.value })} />
          </div>

          {/* Sold Status */}
          <div className="mb-3">
            <Label className="form-label mb-2 block">Sold</Label>
            <Select value={newRecord.finance_status} onValueChange={(value) => setNewRecord({ ...newRecord, finance_status: value })}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Select option" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="no">No</SelectItem>
                <SelectItem value="financiado">Financiado</SelectItem>
                <SelectItem value="least">Least</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Vehicle Info (only when financiado or least) */}
          {(newRecord.finance_status === 'financiado' || newRecord.finance_status === 'least') && (
            <div className="bg-amber-50 rounded-lg p-3 mb-3 border border-amber-200">
              <Label className="form-label mb-2 block text-amber-700">Vehicle Information</Label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
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
            <Button size="sm" onClick={() => handleAddRecord(addingToOpportunity > 1 ? latestRecordInLastOpp?.id : null)} data-testid="save-record-btn">{t('common.save')}</Button>
          </div>
        </div>
      )}
    </div>
  );
}

// Record Card Component
function RecordCard({ 
  record, appointments, getStatusBadge, sendAppointmentSMS, clientId, createAppointment, 
  updateAppointmentStatus, t, isPurple, onOpenAppointmentForm, currentUserId,
  onEdit, onDelete, isEditing, editData, setEditData, onSaveEdit, onCancelEdit 
}) {
  const isOwner = record.salesperson_id === currentUserId;

  if (isEditing) {
    return (
      <div className={`bg-white rounded-lg border p-4 ${isPurple ? 'border-purple-200' : 'border-blue-200'}`}>
        <h5 className="font-medium text-slate-700 mb-3">Edit Record</h5>
        
        {/* Checklist */}
        <div className="flex gap-4 mb-3 flex-wrap">
          {['dl', 'checks', 'ssn', 'itin'].map((field) => (
            <div key={field} className="flex items-center gap-2">
              <Checkbox
                checked={editData[field]}
                onCheckedChange={(checked) => setEditData({ ...editData, [field]: checked })}
              />
              <Label className="text-sm uppercase">{field}</Label>
            </div>
          ))}
        </div>
        
        {/* Info fields */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
          <Input placeholder="Auto" value={editData.auto} onChange={(e) => setEditData({ ...editData, auto: e.target.value })} />
          <Input placeholder="Credit" value={editData.credit} onChange={(e) => setEditData({ ...editData, credit: e.target.value })} />
          <Input placeholder="Bank" value={editData.bank} onChange={(e) => setEditData({ ...editData, bank: e.target.value })} />
          <Input placeholder="Auto Loan" value={editData.auto_loan} onChange={(e) => setEditData({ ...editData, auto_loan: e.target.value })} />
        </div>
        <div className="grid grid-cols-2 gap-3 mb-3">
          <Input placeholder="Down Payment" value={editData.down_payment} onChange={(e) => setEditData({ ...editData, down_payment: e.target.value })} />
          <Input placeholder="Dealer" value={editData.dealer} onChange={(e) => setEditData({ ...editData, dealer: e.target.value })} />
        </div>

        {/* Sold Status */}
        <div className="mb-3">
          <Label className="form-label mb-2 block">Sold</Label>
          <Select value={editData.finance_status} onValueChange={(value) => setEditData({ ...editData, finance_status: value })}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="no">No</SelectItem>
              <SelectItem value="financiado">Financiado</SelectItem>
              <SelectItem value="least">Least</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Vehicle Info */}
        {(editData.finance_status === 'financiado' || editData.finance_status === 'least') && (
          <div className="bg-amber-50 rounded-lg p-3 mb-3 border border-amber-200">
            <Label className="form-label mb-2 block text-amber-700">Vehicle Information</Label>
            <div className="grid grid-cols-2 gap-3">
              <Input placeholder="Make" value={editData.vehicle_make} onChange={(e) => setEditData({ ...editData, vehicle_make: e.target.value })} />
              <Input placeholder="Year" value={editData.vehicle_year} onChange={(e) => setEditData({ ...editData, vehicle_year: e.target.value })} />
            </div>
            <div className="grid grid-cols-3 gap-3 mt-3">
              <Select value={editData.sale_month} onValueChange={(value) => setEditData({ ...editData, sale_month: value })}>
                <SelectTrigger><SelectValue placeholder="Month" /></SelectTrigger>
                <SelectContent>
                  {[...Array(12)].map((_, i) => (
                    <SelectItem key={i+1} value={String(i+1)}>{new Date(2000, i).toLocaleString('default', { month: 'short' })}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={editData.sale_day} onValueChange={(value) => setEditData({ ...editData, sale_day: value })}>
                <SelectTrigger><SelectValue placeholder="Day" /></SelectTrigger>
                <SelectContent>
                  {[...Array(31)].map((_, i) => (
                    <SelectItem key={i+1} value={String(i+1)}>{i+1}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={editData.sale_year} onValueChange={(value) => setEditData({ ...editData, sale_year: value })}>
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
          {record.finance_status && record.finance_status !== 'no' && (
            <span className="bg-amber-100 text-amber-700 px-2 py-0.5 rounded text-xs font-medium uppercase">
              SOLD - {record.finance_status}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
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
            <>
              {getStatusBadge(appointments[record.id].status)}
              <Button size="sm" variant="ghost" onClick={() => sendAppointmentSMS(clientId, appointments[record.id].id)} title="Resend SMS">
                <Send className="w-4 h-4" />
              </Button>
            </>
          ) : (
            <Button size="sm" variant="outline" onClick={() => onOpenAppointmentForm(record.id)}>
              <Calendar className="w-4 h-4 mr-1" />
              Appt
            </Button>
          )}
        </div>
      </div>

      {/* Checklist */}
      <div className="flex gap-4 mb-3 flex-wrap">
        {['dl', 'checks', 'ssn', 'itin'].map((field) => (
          <div key={field} className="flex items-center gap-2">
            <span className={`w-5 h-5 rounded flex items-center justify-center ${
              record[field] ? 'bg-emerald-100 text-emerald-600' : 'bg-slate-100 text-slate-400'
            }`}>
              {record[field] ? '✓' : '×'}
            </span>
            <span className="text-sm text-slate-600 uppercase">{field}</span>
          </div>
        ))}
      </div>

      {/* Details */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
        {record.auto && <div><span className="text-slate-400">Auto:</span> {record.auto}</div>}
        {record.credit && <div><span className="text-slate-400">Credit:</span> {record.credit}</div>}
        {record.bank && <div><span className="text-slate-400">Bank:</span> {record.bank}</div>}
        {record.auto_loan && <div><span className="text-slate-400">Auto Loan:</span> {record.auto_loan}</div>}
        {record.dealer && <div><span className="text-slate-400">Dealer:</span> {record.dealer}</div>}
        {record.down_payment && <div><span className="text-slate-400">Down:</span> ${record.down_payment}</div>}
      </div>

      {/* Vehicle info for financed/least */}
      {(record.finance_status === 'financiado' || record.finance_status === 'least') && record.vehicle_make && (
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

      {/* Appointment Actions */}
      {appointments[record.id] && (
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
function CoSignersSection({ clientId, cosigners, onRefresh }) {
  const { t } = useTranslation();
  const [showAdd, setShowAdd] = useState(false);
  const [addMode, setAddMode] = useState('search'); // 'search' or 'new'
  const [searchPhone, setSearchPhone] = useState('');
  const [foundClient, setFoundClient] = useState(null);
  const [newCosigner, setNewCosigner] = useState({
    first_name: '', last_name: '', phone: '', email: '', address: '', apartment: ''
  });

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
      // Create new client as co-signer
      const clientRes = await axios.post(`${API}/clients`, newCosigner);
      // Link as co-signer
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
            <div key={relation.id} className="flex items-center justify-between bg-white rounded-lg border border-purple-200 p-3">
              <div className="flex items-center gap-3">
                <span className="cosigner-badge">CO-SIGNER</span>
                <div>
                  <span className="font-medium">{relation.cosigner?.first_name} {relation.cosigner?.last_name}</span>
                  <div className="text-sm text-slate-400">
                    {relation.cosigner?.phone}
                    {relation.cosigner?.email && ` • ${relation.cosigner?.email}`}
                  </div>
                </div>
              </div>
              <Button size="sm" variant="ghost" onClick={() => removeCosigner(relation.id)}>
                <Trash2 className="w-4 h-4 text-slate-400" />
              </Button>
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
                <Input
                  value={newCosigner.address}
                  onChange={(e) => setNewCosigner({ ...newCosigner, address: e.target.value })}
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
function ClientInfoModal({ client, onClose, onSendDocsSMS, onRefresh }) {
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
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(null); // 'id' or 'income'

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

  const handleDeleteDocument = async (docType) => {
    try {
      const updateData = docType === 'id' 
        ? { id_uploaded: false }
        : { income_proof_uploaded: false };
      
      await axios.put(`${API}/clients/${client.id}/documents`, null, {
        params: updateData
      });
      toast.success(`${docType === 'id' ? 'ID' : 'Income proof'} document removed`);
      setShowDeleteConfirm(null);
      onRefresh();
    } catch (error) {
      toast.error('Failed to remove document');
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
                  />
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
                  <Input
                    value={editData.address}
                    onChange={(e) => setEditData({ ...editData, address: e.target.value })}
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

          {/* Document Status */}
          <div>
            <Label className="form-label">{t('clients.documents')}</Label>
            <div className="space-y-2 mt-2">
              {/* ID Document */}
              <div className="flex items-center justify-between bg-slate-50 rounded-lg p-3">
                <div className="flex items-center gap-2">
                  {client.id_uploaded ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                  ) : (
                    <XCircle className="w-5 h-5 text-slate-300" />
                  )}
                  <span className="text-sm">{t('clients.idUploaded')}</span>
                </div>
                {client.id_uploaded && (
                  showDeleteConfirm === 'id' ? (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-red-600">Confirm delete?</span>
                      <Button size="sm" variant="destructive" onClick={() => handleDeleteDocument('id')}>
                        Yes
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setShowDeleteConfirm(null)}>
                        No
                      </Button>
                    </div>
                  ) : (
                    <Button size="sm" variant="ghost" onClick={() => setShowDeleteConfirm('id')}>
                      <Trash2 className="w-4 h-4 text-red-400" />
                    </Button>
                  )
                )}
              </div>
              
              {/* Income Proof */}
              <div className="flex items-center justify-between bg-slate-50 rounded-lg p-3">
                <div className="flex items-center gap-2">
                  {client.income_proof_uploaded ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                  ) : (
                    <XCircle className="w-5 h-5 text-slate-300" />
                  )}
                  <span className="text-sm">{t('clients.incomeProof')}</span>
                </div>
                {client.income_proof_uploaded && (
                  showDeleteConfirm === 'income' ? (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-red-600">Confirm delete?</span>
                      <Button size="sm" variant="destructive" onClick={() => handleDeleteDocument('income')}>
                        Yes
                      </Button>
                      <Button size="sm" variant="outline" onClick={() => setShowDeleteConfirm(null)}>
                        No
                      </Button>
                    </div>
                  ) : (
                    <Button size="sm" variant="ghost" onClick={() => setShowDeleteConfirm('income')}>
                      <Trash2 className="w-4 h-4 text-red-400" />
                    </Button>
                  )
                )}
              </div>
            </div>
          </div>

          {/* SMS Actions */}
          <div className="flex gap-3 pt-4 border-t">
            <Button variant="outline" className="flex-1" onClick={onSendDocsSMS} data-testid="send-docs-sms-btn">
              <Send className="w-4 h-4 mr-2" />
              {t('clients.sendDocsSms')}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
