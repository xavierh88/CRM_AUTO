import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { toast } from 'sonner';
import { 
  Upload, FileSpreadsheet, Send, Users, Phone, CheckCircle2, XCircle, 
  Loader2, Trash2, MessageSquare, Clock, AlertTriangle, UserPlus, UsersRound, RefreshCw
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ImportContactsPage() {
  const { t } = useTranslation();
  const [contacts, setContacts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [sendingSms, setSendingSms] = useState({});
  const [file, setFile] = useState(null);
  
  // Duplicate check state
  const [showDuplicateCheck, setShowDuplicateCheck] = useState(false);
  const [checkingDuplicates, setCheckingDuplicates] = useState(false);
  const [duplicateResults, setDuplicateResults] = useState(null);
  const [selectedForImport, setSelectedForImport] = useState({});
  const [importingSelected, setImportingSelected] = useState(false);

  const fetchContacts = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/imported-contacts?limit=100`);
      setContacts(response.data.contacts);
      setTotal(response.data.total);
    } catch (error) {
      console.error('Failed to fetch contacts:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchContacts();
  }, [fetchContacts]);

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      const fileName = selectedFile.name.toLowerCase();
      if (fileName.endsWith('.csv') || fileName.endsWith('.xlsx') || fileName.endsWith('.xls')) {
        setFile(selectedFile);
        setDuplicateResults(null);
      } else {
        toast.error('Please select a CSV or Excel file (.csv, .xlsx, .xls)');
        e.target.value = '';
      }
    }
  };

  const handleCheckDuplicates = async () => {
    if (!file) {
      toast.error('Please select a file first');
      return;
    }

    setCheckingDuplicates(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/import-contacts/check-duplicates`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setDuplicateResults(response.data);
      setShowDuplicateCheck(true);
      
      // Pre-select new contacts and available ones
      const preSelected = {};
      response.data.contacts.forEach((contact, idx) => {
        if (contact.status === 'new' || contact.can_take_over) {
          preSelected[idx] = true;
        }
      });
      setSelectedForImport(preSelected);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to check duplicates');
    } finally {
      setCheckingDuplicates(false);
    }
  };

  const handleUpload = async () => {
    if (!file) {
      toast.error('Please select a file first');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await axios.post(`${API}/import-contacts`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success(response.data.message);
      setFile(null);
      setDuplicateResults(null);
      document.getElementById('file-upload').value = '';
      fetchContacts();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to import contacts');
    } finally {
      setUploading(false);
    }
  };

  const handleTakeOver = async (clientId) => {
    try {
      await axios.post(`${API}/import-contacts/take-over/${clientId}`);
      toast.success('Cliente tomado exitosamente');
      // Refresh duplicate check
      handleCheckDuplicates();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo tomar el cliente');
    }
  };

  const handleRequestCollaboration = async (clientId) => {
    try {
      await axios.post(`${API}/clients/${clientId}/request-collaboration`);
      toast.success('Solicitud de colaboración enviada');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'No se pudo enviar la solicitud');
    }
  };

  const handleSendSmsNow = async (contactId) => {
    setSendingSms(prev => ({ ...prev, [contactId]: true }));
    try {
      await axios.post(`${API}/imported-contacts/${contactId}/send-sms-now`);
      toast.success('SMS sent successfully!');
      fetchContacts();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send SMS');
    } finally {
      setSendingSms(prev => ({ ...prev, [contactId]: false }));
    }
  };

  const handleToggleOptOut = async (contactId, currentOptOut) => {
    try {
      await axios.put(`${API}/imported-contacts/${contactId}/opt-out?opt_out=${!currentOptOut}`);
      toast.success(!currentOptOut ? 'Automatic SMS disabled' : 'Automatic SMS enabled');
      fetchContacts();
    } catch (error) {
      toast.error('Failed to update opt-out status');
    }
  };

  const handleDelete = async (contactId) => {
    if (!window.confirm('Are you sure you want to delete this contact?')) return;
    try {
      await axios.delete(`${API}/imported-contacts/${contactId}`);
      toast.success('Contact deleted');
      fetchContacts();
    } catch (error) {
      toast.error('Failed to delete contact');
    }
  };

  const getStatusBadge = (contact) => {
    if (contact.appointment_created) {
      return <Badge className="bg-green-100 text-green-700">Scheduled</Badge>;
    }
    if (contact.opt_out) {
      return <Badge className="bg-slate-100 text-slate-500">Opted Out</Badge>;
    }
    if (contact.sms_sent) {
      return <Badge className="bg-blue-100 text-blue-700">Contacted ({contact.sms_count}x)</Badge>;
    }
    return <Badge className="bg-amber-100 text-amber-700">Pending</Badge>;
  };

  const getDuplicateStatusBadge = (contact) => {
    switch (contact.status) {
      case 'new':
        return <Badge className="bg-green-100 text-green-700">Nuevo</Badge>;
      case 'own':
        return <Badge className="bg-blue-100 text-blue-700">Tu cliente</Badge>;
      case 'available':
        return <Badge className="bg-amber-100 text-amber-700">Disponible (+72h)</Badge>;
      case 'active':
        return <Badge className="bg-red-100 text-red-700">Activo con otro</Badge>;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6" data-testid="import-contacts-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Import Contacts</h1>
          <p className="text-slate-500 mt-1">Import contacts from Excel or CSV files for SMS marketing campaigns</p>
        </div>
        <Badge variant="outline" className="text-lg px-4 py-2">
          <Users className="w-4 h-4 mr-2" />
          {total} contacts
        </Badge>
      </div>

      {/* Upload Section */}
      <Card className="dashboard-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="w-5 h-5 text-blue-600" />
            Upload File
          </CardTitle>
          <CardDescription>
            Upload an Excel (.xlsx, .xls) or CSV file with columns: First Name, Last Name, Phone
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
            <div className="flex-1">
              <Input
                id="file-upload"
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={handleFileChange}
                className="cursor-pointer"
              />
            </div>
            {file && (
              <div className="flex items-center gap-2 text-sm text-slate-600">
                <FileSpreadsheet className="w-4 h-4" />
                {file.name}
              </div>
            )}
            <div className="flex gap-2">
              <Button 
                onClick={handleCheckDuplicates} 
                disabled={!file || checkingDuplicates}
                variant="outline"
              >
                {checkingDuplicates ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Verificando...
                  </>
                ) : (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Verificar Duplicados
                  </>
                )}
              </Button>
              <Button onClick={handleUpload} disabled={!file || uploading}>
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Importing...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2" />
                    Import All
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Contacts List */}
      <Card className="dashboard-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-purple-600" />
            Imported Contacts
          </CardTitle>
          <CardDescription>
            SMS are automatically sent at 11:00 AM. Weekly reminders for 5 weeks if no appointment is created.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
            </div>
          ) : contacts.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <FileSpreadsheet className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No imported contacts yet</p>
              <p className="text-sm mt-1">Upload an Excel or CSV file to get started</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Phone</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Last SMS</TableHead>
                    <TableHead>Auto SMS</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {contacts.map((contact) => (
                    <TableRow key={contact.id}>
                      <TableCell className="font-medium">
                        {contact.first_name} {contact.last_name}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1 text-sm">
                          <Phone className="w-3 h-3 text-slate-400" />
                          {contact.phone_formatted}
                        </div>
                      </TableCell>
                      <TableCell>{getStatusBadge(contact)}</TableCell>
                      <TableCell>
                        {contact.last_sms_sent ? (
                          <div className="flex items-center gap-1 text-sm text-slate-500">
                            <Clock className="w-3 h-3" />
                            {new Date(contact.last_sms_sent).toLocaleDateString()}
                          </div>
                        ) : '-'}
                      </TableCell>
                      <TableCell>
                        <Switch
                          checked={!contact.opt_out}
                          onCheckedChange={() => handleToggleOptOut(contact.id, contact.opt_out)}
                          disabled={contact.appointment_created}
                        />
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleSendSmsNow(contact.id)}
                            disabled={sendingSms[contact.id] || contact.opt_out}
                            title="Send SMS now"
                          >
                            {sendingSms[contact.id] ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Send className="w-4 h-4" />
                            )}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleDelete(contact.id)}
                            className="text-red-600 hover:bg-red-50"
                            title="Delete contact"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Duplicate Check Dialog */}
      <Dialog open={showDuplicateCheck} onOpenChange={setShowDuplicateCheck}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-amber-500" />
              Verificación de Duplicados
            </DialogTitle>
            <DialogDescription>
              Hemos encontrado algunos contactos que ya existen en el sistema. Revisa antes de importar.
            </DialogDescription>
          </DialogHeader>

          {duplicateResults && (
            <div className="space-y-4">
              {/* Summary */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-green-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-green-700">{duplicateResults.new_contacts}</p>
                  <p className="text-xs text-green-600">Nuevos</p>
                </div>
                <div className="bg-amber-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-amber-700">{duplicateResults.available_to_take}</p>
                  <p className="text-xs text-amber-600">Disponibles (+72h)</p>
                </div>
                <div className="bg-red-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-red-700">{duplicateResults.active_with_others}</p>
                  <p className="text-xs text-red-600">Con otro vendedor</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-slate-700">{duplicateResults.total_rows}</p>
                  <p className="text-xs text-slate-600">Total en archivo</p>
                </div>
              </div>

              {/* Contacts Table */}
              <div className="border rounded-lg overflow-hidden">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Nombre</TableHead>
                      <TableHead>Teléfono</TableHead>
                      <TableHead>Estado</TableHead>
                      <TableHead>Vendedor Actual</TableHead>
                      <TableHead className="text-right">Acción</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {duplicateResults.contacts.map((contact, idx) => (
                      <TableRow key={idx} className={contact.status === 'new' ? 'bg-green-50/50' : ''}>
                        <TableCell className="font-medium">
                          {contact.first_name} {contact.last_name}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1 text-sm">
                            <Phone className="w-3 h-3 text-slate-400" />
                            {contact.phone}
                          </div>
                        </TableCell>
                        <TableCell>{getDuplicateStatusBadge(contact)}</TableCell>
                        <TableCell>
                          {contact.existing_client?.salesperson ? (
                            <span className="text-sm text-slate-600">
                              {contact.existing_client.salesperson.name}
                            </span>
                          ) : '-'}
                        </TableCell>
                        <TableCell className="text-right">
                          {contact.status === 'new' && (
                            <Badge className="bg-green-100 text-green-700">
                              <CheckCircle2 className="w-3 h-3 mr-1" />
                              Se importará
                            </Badge>
                          )}
                          {contact.status === 'own' && (
                            <Badge className="bg-blue-100 text-blue-700">Ya es tuyo</Badge>
                          )}
                          {contact.can_take_over && contact.status !== 'new' && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleTakeOver(contact.existing_client.id)}
                              className="text-amber-600 hover:bg-amber-50"
                            >
                              <UserPlus className="w-4 h-4 mr-1" />
                              Tomar Cliente
                            </Button>
                          )}
                          {contact.can_request_collaboration && (
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => handleRequestCollaboration(contact.existing_client.id)}
                              className="text-purple-600 hover:bg-purple-50"
                            >
                              <UsersRound className="w-4 h-4 mr-1" />
                              Trabajar Juntos
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              <div className="flex justify-end gap-3 pt-4">
                <Button variant="outline" onClick={() => setShowDuplicateCheck(false)}>
                  Cancelar
                </Button>
                <Button onClick={handleUpload} disabled={uploading}>
                  {uploading ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Importando...
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4 mr-2" />
                      Importar Nuevos ({duplicateResults.new_contacts})
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
