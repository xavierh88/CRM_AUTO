import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { toast } from 'sonner';
import { Trash2, RotateCcw, Users, FileText, Shield } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function AdminPage() {
  const { t } = useTranslation();
  const [users, setUsers] = useState([]);
  const [trashClients, setTrashClients] = useState([]);
  const [trashRecords, setTrashRecords] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [usersRes, trashClientsRes, trashRecordsRes] = await Promise.all([
        axios.get(`${API}/users`),
        axios.get(`${API}/trash/clients`),
        axios.get(`${API}/trash/user-records`)
      ]);
      setUsers(usersRes.data);
      setTrashClients(trashClientsRes.data);
      setTrashRecords(trashRecordsRes.data);
    } catch (error) {
      console.error('Failed to fetch admin data:', error);
    } finally {
      setLoading(false);
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

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString();
  };

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
        <p className="text-slate-500 mt-1">Manage users and recover deleted items</p>
      </div>

      <Tabs defaultValue="users" className="w-full">
        <TabsList className="grid w-full grid-cols-3 max-w-md">
          <TabsTrigger value="users" data-testid="users-tab">
            <Users className="w-4 h-4 mr-2" />
            {t('admin.users')}
          </TabsTrigger>
          <TabsTrigger value="trash-clients" data-testid="trash-clients-tab">
            <Trash2 className="w-4 h-4 mr-2" />
            Clients
          </TabsTrigger>
          <TabsTrigger value="trash-records" data-testid="trash-records-tab">
            <FileText className="w-4 h-4 mr-2" />
            Records
          </TabsTrigger>
        </TabsList>

        {/* Users Tab */}
        <TabsContent value="users">
          <Card className="dashboard-card">
            <CardHeader>
              <CardTitle>{t('admin.users')} ({users.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Phone</TableHead>
                    <TableHead>Created</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {users.map((user) => (
                    <TableRow key={user.id} data-testid={`user-row-${user.id}`}>
                      <TableCell className="font-medium">{user.name}</TableCell>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          user.role === 'admin' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
                        }`}>
                          {user.role}
                        </span>
                      </TableCell>
                      <TableCell>{user.phone || '-'}</TableCell>
                      <TableCell>{formatDate(user.created_at)}</TableCell>
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

        {/* Trash Clients Tab */}
        <TabsContent value="trash-clients">
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
        </TabsContent>

        {/* Trash Records Tab */}
        <TabsContent value="trash-records">
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
        </TabsContent>
      </Tabs>
    </div>
  );
}
