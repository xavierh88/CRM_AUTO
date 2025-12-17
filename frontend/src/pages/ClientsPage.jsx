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
  Send, Trash2, CheckCircle2, XCircle, UserPlus, Phone
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
  const [newRecord, setNewRecord] = useState({
    dl: false, checks: false, ssn: false, itin: false,
    auto: '', credit: '', bank: '', auto_loan: '', down_payment: '', dealer: '',
    sold: false, vehicle_make: '', vehicle_year: '', sale_date: '',
    previous_record_id: null
  });

  const handleAddRecord = async (previousRecordId = null) => {
    // Don't save empty records
    const hasData = newRecord.dl || newRecord.checks || newRecord.ssn || newRecord.itin ||
      newRecord.auto || newRecord.credit || newRecord.bank || newRecord.auto_loan ||
      newRecord.down_payment || newRecord.dealer || previousRecordId;
    
    if (!hasData) {
      toast.error('Please fill at least one field');
      return;
    }

    try {
      await axios.post(`${API}/user-records`, { 
        client_id: clientId, 
        ...newRecord,
        previous_record_id: previousRecordId 
      });
      setShowAddRecord(false);
      setNewRecord({
        dl: false, checks: false, ssn: false, itin: false,
        auto: '', credit: '', bank: '', auto_loan: '', down_payment: '', dealer: '',
        sold: false, vehicle_make: '', vehicle_year: '', sale_date: '',
        previous_record_id: null
      });
      onRefresh();
      toast.success(t('common.success'));
    } catch (error) {
      toast.error(t('common.error'));
    }
  };

  const createNewOpportunity = async (previousRecordId) => {
    try {
      await axios.post(`${API}/user-records`, { 
        client_id: clientId, 
        previous_record_id: previousRecordId,
        dl: false, checks: false, ssn: false, itin: false
      });
      onRefresh();
      toast.success('New opportunity created!');
    } catch (error) {
      toast.error(t('common.error'));
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

  return (
    <div className="mb-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-semibold text-slate-700">{t('records.title')}</h4>
        <Button 
          size="sm" 
          variant="outline" 
          onClick={() => setShowAddRecord(true)}
          data-testid="add-record-btn"
        >
          <Plus className="w-4 h-4 mr-1" />
          {t('records.addNew')}
        </Button>
      </div>

      {/* Records List */}
      <div className="space-y-3">
        {records.filter(r => r.salesperson_id === user.id).map((record) => (
          <div key={record.id} className="bg-white rounded-lg border border-slate-200 p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-medium text-blue-600">Your Record</span>
              {appointments[record.id] ? (
                <div className="flex items-center gap-2">
                  {getStatusBadge(appointments[record.id].status)}
                  <Button 
                    size="sm" 
                    variant="ghost"
                    onClick={() => sendAppointmentSMS(clientId, appointments[record.id].id)}
                    data-testid={`send-appt-sms-${record.id}`}
                  >
                    <Send className="w-4 h-4" />
                  </Button>
                </div>
              ) : (
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={() => createAppointment(record.id)}
                  data-testid={`create-appt-${record.id}`}
                >
                  <Calendar className="w-4 h-4 mr-1" />
                  Create Appointment
                </Button>
              )}
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
                  <span className="text-sm text-slate-600 uppercase">{t(`records.${field}`)}</span>
                </div>
              ))}
            </div>

            {/* Details */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 text-sm">
              {record.auto && <div><span className="text-slate-400">Auto:</span> {record.auto}</div>}
              {record.dealer && <div><span className="text-slate-400">Dealer:</span> {record.dealer}</div>}
              {record.down_payment && <div><span className="text-slate-400">Down:</span> ${record.down_payment}</div>}
              {record.sold && <div className="col-span-full"><span className="bg-amber-100 text-amber-700 px-2 py-1 rounded text-xs font-medium">SOLD - {record.vehicle_make} {record.vehicle_year}</span></div>}
            </div>

            {/* Appointment Actions */}
            {appointments[record.id] && (
              <div className="flex gap-2 mt-3 pt-3 border-t border-slate-100">
                <Button 
                  size="sm" 
                  variant="outline"
                  className="text-emerald-600 hover:bg-emerald-50"
                  onClick={() => updateAppointmentStatus(appointments[record.id].id, 'cumplido')}
                >
                  {t('appointments.markCompleted')}
                </Button>
                <Button 
                  size="sm" 
                  variant="outline"
                  className="text-slate-600 hover:bg-slate-50"
                  onClick={() => updateAppointmentStatus(appointments[record.id].id, 'no_show')}
                >
                  {t('appointments.markNoShow')}
                </Button>
              </div>
            )}
          </div>
        ))}

        {records.filter(r => r.salesperson_id !== user.id).length > 0 && (
          <div className="text-sm text-slate-400 mt-2">
            + {records.filter(r => r.salesperson_id !== user.id).length} records from other salespeople
          </div>
        )}
      </div>

      {/* Add Record Form */}
      {showAddRecord && (
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
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-3">
            <Input placeholder={t('records.auto')} value={newRecord.auto} onChange={(e) => setNewRecord({ ...newRecord, auto: e.target.value })} />
            <Input placeholder={t('records.dealer')} value={newRecord.dealer} onChange={(e) => setNewRecord({ ...newRecord, dealer: e.target.value })} />
            <Input placeholder={t('records.downPayment')} value={newRecord.down_payment} onChange={(e) => setNewRecord({ ...newRecord, down_payment: e.target.value })} />
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowAddRecord(false)}>{t('common.cancel')}</Button>
            <Button size="sm" onClick={handleAddRecord} data-testid="save-record-btn">{t('common.save')}</Button>
          </div>
        </div>
      )}
    </div>
  );
}

// Co-Signers Section Component
function CoSignersSection({ clientId, cosigners, onRefresh }) {
  const { t } = useTranslation();
  const [showAdd, setShowAdd] = useState(false);
  const [searchPhone, setSearchPhone] = useState('');
  const [foundClient, setFoundClient] = useState(null);

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

  const removeCosigner = async (relationId) => {
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
        <h4 className="font-semibold text-slate-700">{t('cosigner.title')}</h4>
        <Button size="sm" variant="outline" onClick={() => setShowAdd(!showAdd)} data-testid="add-cosigner-btn">
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
                <span className="font-medium">{relation.cosigner?.first_name} {relation.cosigner?.last_name}</span>
                <span className="text-sm text-slate-400">{relation.cosigner?.phone}</span>
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
          <h5 className="font-medium text-slate-700 mb-3">{t('cosigner.existing')}</h5>
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
        </div>
      )}
    </div>
  );
}

// Client Info Modal Component
function ClientInfoModal({ client, onClose, onSendDocsSMS, onRefresh }) {
  const { t } = useTranslation();

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{t('clients.info')}</DialogTitle>
          <p className="text-sm text-slate-500">View and manage client details</p>
        </DialogHeader>
        <div className="space-y-4">
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

          {/* Document Status */}
          <div>
            <Label className="form-label">{t('clients.documents')}</Label>
            <div className="flex gap-4 mt-2">
              <div className="flex items-center gap-2">
                {client.id_uploaded ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                ) : (
                  <XCircle className="w-5 h-5 text-slate-300" />
                )}
                <span className="text-sm">{t('clients.idUploaded')}</span>
              </div>
              <div className="flex items-center gap-2">
                {client.income_proof_uploaded ? (
                  <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                ) : (
                  <XCircle className="w-5 h-5 text-slate-300" />
                )}
                <span className="text-sm">{t('clients.incomeProof')}</span>
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
