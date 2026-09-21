import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import {
  Search, FileText, Download, Upload, Trash2, Eye, CheckCircle, AlertCircle,
  ChevronDown, ChevronUp, Filter, RefreshCw, Loader2
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DOC_TYPES = [
  { id: 'id', label: 'ID Documents', icon: FileText },
  { id: 'income', label: 'Income Proof', icon: FileText },
  { id: 'residence', label: 'Residence Proof', icon: FileText },
  { id: 'insurance', label: 'Insurance', icon: FileText },
  { id: 'other', label: 'Other', icon: FileText },
];

export default function DocumentsPage() {
  const { t } = useTranslation();
  const { user, isAdmin, isBDCManager } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedClient, setSelectedClient] = useState(null);
  const [clientDocs, setClientDocs] = useState({});
  const [uploading, setUploading] = useState(false);

  const fetchDocuments = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append('search', searchTerm);
      if (typeFilter !== 'all') params.append('type', typeFilter);
      if (statusFilter !== 'all') params.append('status', statusFilter);
      
      if (!isAdmin && !isBDCManager) {
        params.append('salesperson_id', user.id);
      }

      // Note: This endpoint would need to be created in backend
      // For now, we'll fetch clients and their docs
      const response = await axios.get(`${API}/clients?exclude_sold=false&sort_by=name`);
      setDocuments(response.data);
    } catch (error) {
      console.error('Failed to fetch documents:', error);
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [searchTerm, typeFilter, statusFilter, user, isAdmin, isBDCManager]);

  const fetchClientDocs = async (clientId) => {
    try {
      const [idRes, incomeRes, residenceRes] = await Promise.all([
        axios.get(`${API}/clients/${clientId}/documents/list/id`).catch(() => ({ data: [] })),
        axios.get(`${API}/clients/${clientId}/documents/list/income`).catch(() => ({ data: [] })),
        axios.get(`${API}/clients/${clientId}/documents/list/residence`).catch(() => ({ data: [] })),
      ]);
      setClientDocs({
        id: idRes.data,
        income: incomeRes.data,
        residence: residenceRes.data,
      });
      setSelectedClient(clientId);
    } catch (error) {
      toast.error('Failed to load documents');
    }
  };

  const handleUpload = async (clientId, type, file) => {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      await axios.post(`${API}/clients/${clientId}/documents/upload/${type}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success('Document uploaded');
      fetchClientDocs(clientId);
    } catch (error) {
      toast.error('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (clientId, type, docId) => {
    if (!window.confirm('Delete this document?')) return;
    try {
      await axios.delete(`${API}/clients/${clientId}/documents/${type}/${docId}`);
      toast.success('Document deleted');
      fetchClientDocs(clientId);
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  const getDocStats = (client) => {
    const complete = client.id_uploaded && client.income_proof_uploaded;
    return { complete, id: client.id_uploaded, income: client.income_proof_uploaded };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="documents-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('documents.title')}</h1>
          <p className="text-muted-foreground mt-1">
            {documents.length} clients • Document management
          </p>
        </div>
      </div>

      {/* Search & Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder={t('documents.search')}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-full sm:w-40">
                <SelectValue placeholder={t('documents.type')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('common.all')}</SelectItem>
                {DOC_TYPES.map(dt => (
                  <SelectItem key={dt.id} value={dt.id}>{dt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-40">
                <SelectValue placeholder={t('documents.status')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('common.all')}</SelectItem>
                <SelectItem value="complete">{t('documents.complete')}</SelectItem>
                <SelectItem value="pending">{t('documents.pending')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Document Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {DOC_TYPES.slice(0, 3).map((type) => {
          const complete = documents.filter(c => {
            if (type.id === 'id') return c.id_uploaded;
            if (type.id === 'income') return c.income_proof_uploaded;
            return false;
          }).length;
          const pending = documents.length - complete;
          return (
            <Card key={type.id} className="border-l-4 border-l-primary">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{type.label}</p>
                    <p className="text-2xl font-bold">{complete}/{documents.length}</p>
                  </div>
                  <div className={`p-3 rounded-lg ${type.icon === FileText ? 'bg-blue-500/10' : ''}`}>
                    <type.icon className="w-6 h-6 text-primary" />
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-4 text-sm">
                  <span className="flex items-center gap-1 text-emerald-600">
                    <CheckCircle className="w-4 h-4" /> {complete} complete
                  </span>
                  <span className="flex items-center gap-1 text-amber-600">
                    <AlertCircle className="w-4 h-4" /> {pending} pending
                  </span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Client Documents Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="p-4 text-left font-medium text-muted-foreground">Client</th>
                  <th className="p-4 text-left font-medium text-muted-foreground">Phone</th>
                  <th className="p-4 text-left font-medium text-muted-foreground">ID Docs</th>
                  <th className="p-4 text-left font-medium text-muted-foreground">Income Proof</th>
                  <th className="p-4 text-left font-medium text-muted-foreground">Residence Proof</th>
                  <th className="p-4 text-left font-medium text-muted-foreground">Status</th>
                  <th className="p-4 text-right font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {documents.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="p-12 text-center text-muted-foreground">
                      {t('documents.noDocuments')}
                    </td>
                  </tr>
                ) : (
                  documents
                    .filter(c => {
                      if (searchTerm) {
                        const term = searchTerm.toLowerCase();
                        return `${c.first_name} ${c.last_name}`.toLowerCase().includes(term) ||
                               c.phone?.includes(term);
                      }
                      return true;
                    })
                    .filter(c => {
                      if (statusFilter === 'complete') return c.id_uploaded && c.income_proof_uploaded;
                      if (statusFilter === 'pending') return !c.id_uploaded || !c.income_proof_uploaded;
                      return true;
                    })
                    .map((client) => (
                      <tr key={client.id} className="border-b border-border/50 hover:bg-muted/50 cursor-pointer" onClick={() => fetchClientDocs(client.id)}>
                        <td className="p-4">
                          <p className="font-medium">{client.first_name} {client.last_name}</p>
                        </td>
                        <td className="p-4 font-mono text-sm">{client.phone}</td>
                        <td className="p-4">
                          {client.id_uploaded ? (
                            <span className="flex items-center gap-1 text-emerald-600"><CheckCircle className="w-4 h-4" /> Complete</span>
                          ) : (
                            <span className="flex items-center gap-1 text-amber-600"><AlertCircle className="w-4 h-4" /> Missing</span>
                          )}
                        </td>
                        <td className="p-4">
                          {client.income_proof_uploaded ? (
                            <span className="flex items-center gap-1 text-emerald-600"><CheckCircle className="w-4 h-4" /> Complete</span>
                          ) : (
                            <span className="flex items-center gap-1 text-amber-600"><AlertCircle className="w-4 h-4" /> Missing</span>
                          )}
                        </td>
                        <td className="p-4">
                          {client.residence_proof_uploaded ? (
                            <span className="flex items-center gap-1 text-emerald-600"><CheckCircle className="w-4 h-4" /> Complete</span>
                          ) : (
                            <span className="flex items-center gap-1 text-amber-600"><AlertCircle className="w-4 h-4" /> Missing</span>
                          )}
                        </td>
                        <td className="p-4">
                          {client.id_uploaded && client.income_proof_uploaded ? (
                            <Badge variant="default" className="text-xs">{t('documents.complete')}</Badge>
                          ) : (
                            <Badge variant="secondary" className="text-xs">{t('documents.pending')}</Badge>
                          )}
                        </td>
                        <td className="p-4 text-right">
                          <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); fetchClientDocs(client.id); }}>
                            <Eye className="w-4 h-4 mr-1" /> View
                          </Button>
                        </td>
                      </tr>
                    ))
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Client Documents Detail Dialog */}
      {selectedClient && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => { setSelectedClient(null); setClientDocs({}); }}>
          <div className="bg-card rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h2 className="text-lg font-semibold">{clientDocs.client?.first_name} {clientDocs.client?.last_name} - Documents</h2>
              <Button variant="ghost" size="sm" onClick={() => { setSelectedClient(null); setClientDocs({}); }}>
                <XCircleIcon className="w-5 h-5" />
              </Button>
            </div>
            <div className="p-4 overflow-y-auto space-y-6">
              {DOC_TYPES.map((type) => {
                const docs = clientDocs[type.id] || [];
                return (
                  <div key={type.id}>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-medium flex items-center gap-2">
                        <type.icon className="w-5 h-5 text-primary" />
                        {type.label} ({docs.length})
                      </h3>
                      <label className="cursor-pointer">
                        <input type="file" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" className="sr-only" onChange={(e) => e.target.files[0] && handleUpload(selectedClient, type.id, e.target.files[0])} />
                        <Button variant="outline" size="sm" disabled={uploading}>
                          <Upload className="w-4 h-4 mr-1" /> Upload
                        </Button>
                      </label>
                    </div>
                    {docs.length === 0 ? (
                      <div className="border-2 border-dashed border-border/50 rounded-lg p-8 text-center text-muted-foreground">
                        No {type.label.toLowerCase()} uploaded
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {docs.map((doc) => (
                          <div key={doc.id} className="p-3 border border-border rounded-lg flex items-center justify-between">
                            <div className="flex items-center gap-3 min-w-0">
                              <FileText className="w-6 h-6 text-muted-foreground flex-shrink-0" />
                              <div className="min-w-0">
                                <p className="font-medium text-sm truncate">{doc.original_name || doc.filename}</p>
                                <p className="text-xs text-muted-foreground">
                                  {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : ''}
                                  {doc.size && ` • ${(doc.size / 1024).toFixed(1)} KB`}
                                </p>
                              </div>
                            </div>
                            <div className="flex items-center gap-1 flex-shrink-0">
                              <Button variant="ghost" size="sm" onClick={() => window.open(doc.url, '_blank')}>
                                <Eye className="w-4 h-4" />
                              </Button>
                              <Button variant="ghost" size="sm" onClick={() => handleDelete(selectedClient, type.id, doc.id)} className="text-destructive">
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}