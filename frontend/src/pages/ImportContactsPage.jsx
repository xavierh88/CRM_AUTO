import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import { Upload, FileSpreadsheet, Send, Users, Phone, CheckCircle2, XCircle, Loader2, Trash2, MessageSquare, Clock } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ImportContactsPage() {
  const { t } = useTranslation();
  const [contacts, setContacts] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [sendingSms, setSendingSms] = useState({});
  const [file, setFile] = useState(null);

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
      } else {
        toast.error('Please select a CSV or Excel file (.csv, .xlsx, .xls)');
        e.target.value = '';
      }
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
      document.getElementById('file-upload').value = '';
      fetchContacts();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to import contacts');
    } finally {
      setUploading(false);
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

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <FileSpreadsheet className="w-6 h-6 text-blue-600" />
          Import Contacts
        </h1>
        <p className="text-slate-500 mt-1">Import contacts from Excel or CSV and send marketing SMS</p>
      </div>

      {/* Upload Section */}
      <Card>
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
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <Input
                id="file-upload"
                type="file"
                accept=".csv,.xlsx,.xls"
                onChange={handleFileChange}
                className="cursor-pointer"
              />
              {file && (
                <p className="text-sm text-slate-500 mt-1">
                  Selected: <strong>{file.name}</strong> ({(file.size / 1024).toFixed(1)} KB)
                </p>
              )}
            </div>
            <Button onClick={handleUpload} disabled={!file || uploading}>
              {uploading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Importing...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4 mr-2" />
                  Import Contacts
                </>
              )}
            </Button>
          </div>

          {/* Instructions */}
          <div className="mt-4 p-4 bg-blue-50 rounded-lg">
            <h4 className="font-medium text-blue-800 mb-2">File Requirements:</h4>
            <ul className="text-sm text-blue-700 space-y-1">
              <li>• Columns can be named: First Name, Last Name, Phone (or Spanish equivalents)</li>
              <li>• Phone numbers: System will extract last 10 digits automatically</li>
              <li>• Duplicate phone numbers will be skipped</li>
              <li>• SMS will be scheduled for 11:00 AM (or you can send immediately)</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Contacts List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <Users className="w-5 h-5 text-slate-600" />
              Imported Contacts ({total})
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {contacts.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              <FileSpreadsheet className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No contacts imported yet</p>
              <p className="text-sm">Upload a file to get started</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Phone</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last SMS</TableHead>
                  <TableHead>Auto SMS</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {contacts.map((contact) => (
                  <TableRow key={contact.id}>
                    <TableCell className="font-medium">
                      {contact.first_name} {contact.last_name}
                    </TableCell>
                    <TableCell>
                      <span className="flex items-center gap-1 text-slate-600">
                        <Phone className="w-3 h-3" />
                        {contact.phone_formatted}
                      </span>
                    </TableCell>
                    <TableCell>{getStatusBadge(contact)}</TableCell>
                    <TableCell className="text-sm text-slate-500">
                      {contact.last_sms_sent ? formatDate(contact.last_sms_sent) : '-'}
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={!contact.opt_out}
                          onCheckedChange={() => handleToggleOptOut(contact.id, contact.opt_out)}
                          disabled={contact.appointment_created}
                        />
                        <span className="text-xs text-slate-400">
                          {contact.opt_out ? 'Off' : 'On'}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        {!contact.appointment_created && !contact.opt_out && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleSendSmsNow(contact.id)}
                            disabled={sendingSms[contact.id]}
                            title="Send SMS Now"
                          >
                            {sendingSms[contact.id] ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <Send className="w-4 h-4" />
                            )}
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant="outline"
                          className="text-red-500 hover:bg-red-50"
                          onClick={() => handleDelete(contact.id)}
                          title="Delete"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
