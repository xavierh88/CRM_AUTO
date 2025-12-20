import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Textarea } from '../components/ui/textarea';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';
import { Trash2, RotateCcw, Users, Shield, CheckCircle2, XCircle, UserCog, Plus, Building2, Car, Landmark, MessageSquare, Save } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AdminPage() {
  const { t } = useTranslation();
  const [users, setUsers] = useState([]);
  const [trashClients, setTrashClients] = useState([]);
  const [trashRecords, setTrashRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Config lists state
  const [banks, setBanks] = useState([]);
  const [dealers, setDealers] = useState([]);
  const [cars, setCars] = useState([]);
  const [newBank, setNewBank] = useState('');
  const [newDealer, setNewDealer] = useState('');
  const [newCar, setNewCar] = useState('');
  
  // SMS Templates state
  const [smsTemplates, setSmsTemplates] = useState([]);
  const [editingTemplate, setEditingTemplate] = useState(null);
  const [savingTemplate, setSavingTemplate] = useState(false);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [usersRes, trashClientsRes, trashRecordsRes, banksRes, dealersRes, carsRes, templatesRes] = await Promise.all([
        axios.get(`${API}/users`),
        axios.get(`${API}/trash/clients`),
        axios.get(`${API}/trash/user-records`),
        axios.get(`${API}/config-lists/bank`),
        axios.get(`${API}/config-lists/dealer`),
        axios.get(`${API}/config-lists/car`),
        axios.get(`${API}/sms-templates`).catch(() => ({ data: [] }))
      ]);
      setUsers(usersRes.data);
      setTrashClients(trashClientsRes.data);
      setTrashRecords(trashRecordsRes.data);
      setBanks(banksRes.data);
      setDealers(dealersRes.data);
      setCars(carsRes.data);
      setSmsTemplates(templatesRes.data);
    } catch (error) {
      console.error('Failed to fetch admin data:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleUserActive = async (userId, currentStatus) => {
    try {
      await axios.put(`${API}/users/activate`, {
        user_id: userId,
        is_active: !currentStatus
      });
      toast.success(`User ${!currentStatus ? 'activated' : 'deactivated'}`);
      fetchData();
    } catch (error) {
      toast.error('Failed to update user status');
    }
  };

  const updateUserRole = async (userId, newRole) => {
    try {
      await axios.put(`${API}/users/role`, {
        user_id: userId,
        role: newRole
      });
      toast.success(`Role updated to ${newRole}`);
      fetchData();
    } catch (error) {
      toast.error('Failed to update role');
    }
  };

  const restoreClient = async (clientId) => {
    try {
      await axios.post(`${API}/clients/${clientId}/restore`);
      toast.success('Client restored');
      fetchData();
    } catch (error) {
      toast.error('Failed to restore client');
    }
  };

  const permanentDeleteClient = async (clientId) => {
    if (!window.confirm('Are you sure? This cannot be undone.')) return;
    try {
      await axios.delete(`${API}/clients/${clientId}?permanent=true`);
      toast.success('Client permanently deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete client');
    }
  };

  const permanentDeleteRecord = async (recordId) => {
    if (!window.confirm('Are you sure? This cannot be undone.')) return;
    try {
      await axios.delete(`${API}/user-records/${recordId}?permanent=true`);
      toast.success('Record permanently deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete record');
    }
  };

  // Config list functions
  const addConfigItem = async (category, name, setter) => {
    if (!name.trim()) {
      toast.error('Please enter a name');
      return;
    }
    try {
      await axios.post(`${API}/config-lists`, { name: name.trim(), category });
      toast.success(`${name} added to ${category} list`);
      setter('');
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add item');
    }
  };

  const deleteConfigItem = async (itemId, category) => {
    if (!window.confirm('Are you sure you want to delete this item?')) return;
    try {
      await axios.delete(`${API}/config-lists/${itemId}`);
      toast.success('Item deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete item');
    }
  };

  // SMS Template functions
  const handleEditTemplate = (template) => {
    setEditingTemplate({
      ...template,
      message_en: template.message_en || '',
      message_es: template.message_es || ''
    });
  };

  const handleSaveTemplate = async () => {
    if (!editingTemplate) return;
    
    setSavingTemplate(true);
    try {
      await axios.put(`${API}/sms-templates/${editingTemplate.template_key}`, {
        template_key: editingTemplate.template_key,
        message_en: editingTemplate.message_en,
        message_es: editingTemplate.message_es
      });
      toast.success('Template saved successfully');
      setEditingTemplate(null);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save template');
    } finally {
      setSavingTemplate(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString();
  };

  // Count pending activations
  const pendingUsers = users.filter(u => !u.is_active && u.role !== 'admin').length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-page">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <Shield className="w-6 h-6 text-purple-600" />
          {t('nav.admin')}
        </h1>
        <p className="text-slate-500 mt-1">Manage users, lists, and recover deleted items</p>
      </div>

      {/* Pending Activations Alert */}
      {pendingUsers > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-center gap-3">
          <div className="w-10 h-10 bg-amber-100 rounded-full flex items-center justify-center">
            <UserCog className="w-5 h-5 text-amber-600" />
          </div>
          <div>
            <p className="font-medium text-amber-800">{pendingUsers} user(s) pending activation</p>
            <p className="text-sm text-amber-600">Review and activate new user accounts below</p>
          </div>
        </div>
      )}

      <Tabs defaultValue="users" className="w-full">
        <TabsList className="grid w-full grid-cols-5 max-w-2xl">
          <TabsTrigger value="users" data-testid="users-tab" className="relative">
            <Users className="w-4 h-4 mr-1" />
            Users
            {pendingUsers > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 bg-amber-500 text-white text-xs rounded-full flex items-center justify-center">
                {pendingUsers}
              </span>
            )}
          </TabsTrigger>
          <TabsTrigger value="banks" data-testid="banks-tab">
            <Landmark className="w-4 h-4 mr-1" />
            Banks
          </TabsTrigger>
          <TabsTrigger value="dealers" data-testid="dealers-tab">
            <Building2 className="w-4 h-4 mr-1" />
            Dealers
          </TabsTrigger>
          <TabsTrigger value="cars" data-testid="cars-tab">
            <Car className="w-4 h-4 mr-1" />
            Autos
          </TabsTrigger>
          <TabsTrigger value="trash" data-testid="trash-tab">
            <Trash2 className="w-4 h-4 mr-1" />
            Trash
          </TabsTrigger>
        </TabsList>

        {/* Users Tab */}
        <TabsContent value="users">
          <Card className="dashboard-card">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{t('admin.users')} ({users.length})</span>
                <div className="flex items-center gap-2 text-sm font-normal">
                  <span className="flex items-center gap-1 text-emerald-600">
                    <CheckCircle2 className="w-4 h-4" /> Active
                  </span>
                  <span className="flex items-center gap-1 text-slate-400">
                    <XCircle className="w-4 h-4" /> Inactive
                  </span>
                </div>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Status</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Phone</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user) => (
                    <TableRow 
                      key={user.id} 
                      data-testid={`user-row-${user.id}`}
                      className={!user.is_active && user.role !== 'admin' ? 'bg-amber-50' : ''}
                    >
                      <TableCell>
                        {user.is_active || user.role === 'admin' ? (
                          <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                        ) : (
                          <XCircle className="w-5 h-5 text-slate-300" />
                        )}
                      </TableCell>
                      <TableCell className="font-medium">{user.name}</TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>
                        {user.email === 'xadmin' ? (
                          <span className="px-2 py-1 rounded text-xs font-medium bg-purple-100 text-purple-700">
                            admin (system)
                          </span>
                        ) : (
                          <Select 
                            value={user.role} 
                            onValueChange={(value) => updateUserRole(user.id, value)}
                          >
                            <SelectTrigger className="w-32 h-8" data-testid={`role-select-${user.id}`}>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="salesperson">Salesperson</SelectItem>
                              <SelectItem value="admin">Admin</SelectItem>
                            </SelectContent>
                          </Select>
                        )}
                      </TableCell>
                      <TableCell>{user.phone || '-'}</TableCell>
                      <TableCell>{formatDate(user.created_at)}</TableCell>
                      <TableCell>
                        {user.email !== 'xadmin' && (
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-slate-500">
                              {user.is_active ? 'Active' : 'Inactive'}
                            </span>
                            <Switch
                              checked={user.is_active || false}
                              onCheckedChange={() => toggleUserActive(user.id, user.is_active)}
                              data-testid={`toggle-active-${user.id}`}
                            />
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {users.length === 0 && (
                <p className="text-center text-slate-400 py-8">{t('common.noData')}</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Banks Tab */}
        <TabsContent value="banks">
          <Card className="dashboard-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Landmark className="w-5 h-5 text-blue-600" />
                Banks ({banks.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2 mb-4">
                <Input
                  placeholder="Enter new bank name..."
                  value={newBank}
                  onChange={(e) => setNewBank(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && addConfigItem('bank', newBank, setNewBank)}
                  data-testid="new-bank-input"
                />
                <Button onClick={() => addConfigItem('bank', newBank, setNewBank)} data-testid="add-bank-btn">
                  <Plus className="w-4 h-4 mr-1" /> Add
                </Button>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2 max-h-96 overflow-y-auto">
                {banks.map((bank) => (
                  <div key={bank.id} className="flex items-center justify-between bg-slate-50 rounded-lg px-3 py-2 group">
                    <span className="text-sm">{bank.name}</span>
                    <Button 
                      size="sm" 
                      variant="ghost" 
                      className="opacity-0 group-hover:opacity-100 h-6 w-6 p-0"
                      onClick={() => deleteConfigItem(bank.id, 'bank')}
                    >
                      <Trash2 className="w-3 h-3 text-red-400" />
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Dealers Tab */}
        <TabsContent value="dealers">
          <Card className="dashboard-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="w-5 h-5 text-green-600" />
                Dealers ({dealers.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2 mb-4">
                <Input
                  placeholder="Enter new dealer name..."
                  value={newDealer}
                  onChange={(e) => setNewDealer(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && addConfigItem('dealer', newDealer, setNewDealer)}
                  data-testid="new-dealer-input"
                />
                <Button onClick={() => addConfigItem('dealer', newDealer, setNewDealer)} data-testid="add-dealer-btn">
                  <Plus className="w-4 h-4 mr-1" /> Add
                </Button>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {dealers.map((dealer) => (
                  <div key={dealer.id} className="flex items-center justify-between bg-slate-50 rounded-lg px-3 py-2 group">
                    <span className="text-sm">{dealer.name}</span>
                    <Button 
                      size="sm" 
                      variant="ghost" 
                      className="opacity-0 group-hover:opacity-100 h-6 w-6 p-0"
                      onClick={() => deleteConfigItem(dealer.id, 'dealer')}
                    >
                      <Trash2 className="w-3 h-3 text-red-400" />
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Cars Tab */}
        <TabsContent value="cars">
          <Card className="dashboard-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Car className="w-5 h-5 text-amber-600" />
                Autos ({cars.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2 mb-4">
                <Input
                  placeholder="Enter new car make/model..."
                  value={newCar}
                  onChange={(e) => setNewCar(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && addConfigItem('car', newCar, setNewCar)}
                  data-testid="new-car-input"
                />
                <Button onClick={() => addConfigItem('car', newCar, setNewCar)} data-testid="add-car-btn">
                  <Plus className="w-4 h-4 mr-1" /> Add
                </Button>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2 max-h-96 overflow-y-auto">
                {cars.map((car) => (
                  <div key={car.id} className="flex items-center justify-between bg-slate-50 rounded-lg px-3 py-2 group">
                    <span className="text-sm">{car.name}</span>
                    <Button 
                      size="sm" 
                      variant="ghost" 
                      className="opacity-0 group-hover:opacity-100 h-6 w-6 p-0"
                      onClick={() => deleteConfigItem(car.id, 'car')}
                    >
                      <Trash2 className="w-3 h-3 text-red-400" />
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Trash Tab */}
        <TabsContent value="trash">
          <div className="space-y-4">
            {/* Trash Clients */}
            <Card className="dashboard-card">
              <CardHeader>
                <CardTitle>{t('admin.deletedClients')} ({trashClients.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Phone</TableHead>
                      <TableHead>Email</TableHead>
                      <TableHead>Deleted At</TableHead>
                      <TableHead>{t('common.actions')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {trashClients.map((client) => (
                      <TableRow key={client.id} data-testid={`trash-client-${client.id}`}>
                        <TableCell className="font-medium">
                          {client.first_name} {client.last_name}
                        </TableCell>
                        <TableCell>{client.phone}</TableCell>
                        <TableCell>{client.email || '-'}</TableCell>
                        <TableCell>{formatDate(client.deleted_at)}</TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => restoreClient(client.id)}
                              data-testid={`restore-client-${client.id}`}
                            >
                              <RotateCcw className="w-4 h-4 mr-1" />
                              {t('common.restore')}
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="text-red-600 hover:bg-red-50"
                              onClick={() => permanentDeleteClient(client.id)}
                              data-testid={`delete-client-${client.id}`}
                            >
                              <Trash2 className="w-4 h-4 mr-1" />
                              {t('admin.permanentDelete')}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                {trashClients.length === 0 && (
                  <p className="text-center text-slate-400 py-8">No deleted clients</p>
                )}
              </CardContent>
            </Card>

            {/* Trash Records */}
            <Card className="dashboard-card">
              <CardHeader>
                <CardTitle>{t('admin.deletedRecords')} ({trashRecords.length})</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Salesperson</TableHead>
                      <TableHead>Client ID</TableHead>
                      <TableHead>Dealer</TableHead>
                      <TableHead>Sold</TableHead>
                      <TableHead>Deleted At</TableHead>
                      <TableHead>{t('common.actions')}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {trashRecords.map((record) => (
                      <TableRow key={record.id} data-testid={`trash-record-${record.id}`}>
                        <TableCell className="font-medium">{record.salesperson_name}</TableCell>
                        <TableCell className="font-mono text-xs">{record.client_id.slice(0, 8)}...</TableCell>
                        <TableCell>{record.dealer || '-'}</TableCell>
                        <TableCell>
                          {record.sold ? (
                            <span className="bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded text-xs">Yes</span>
                          ) : (
                            <span className="bg-slate-100 text-slate-500 px-2 py-0.5 rounded text-xs">No</span>
                          )}
                        </TableCell>
                        <TableCell>{formatDate(record.deleted_at)}</TableCell>
                        <TableCell>
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-red-600 hover:bg-red-50"
                            onClick={() => permanentDeleteRecord(record.id)}
                            data-testid={`delete-record-${record.id}`}
                          >
                            <Trash2 className="w-4 h-4 mr-1" />
                            Delete
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                {trashRecords.length === 0 && (
                  <p className="text-center text-slate-400 py-8">No deleted records</p>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
