import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import {
  Search, FileText, Download, Upload, Trash2, Eye, CheckCircle, AlertCircle,
  ChevronDown, ChevronUp, Filter, RefreshCw, Loader2, XCircle as XCircleIcon,
  LayoutGrid, LayoutList, File, Image
} from 'lucide-react';
import DocumentViewer from '../components/DocumentViewer';
import DocumentCategoryDialog from '../components/DocumentCategoryDialog';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DOC_CATEGORIES = [
  { id: 'id', labelKey: 'documents.id', label: 'Identification', icon: FileText, color: 'blue' },
  { id: 'income', labelKey: 'documents.income', label: 'Income Proof', icon: FileText, color: 'emerald' },
  { id: 'residence', labelKey: 'documents.residence', label: 'Residence Proof', icon: FileText, color: 'amber' },
];

const STATUS_OPTIONS = [
  { value: 'all', labelKey: 'common.all', label: 'All' },
  { value: 'complete', labelKey: 'documents.complete', label: 'Complete' },
  { value: 'pending', labelKey: 'documents.pending', label: 'Pending' },
  { value: 'missing', labelKey: 'documents.missing', label: 'Missing' },
];

const TYPE_FILTER_OPTIONS = [
  { value: 'all', labelKey: 'common.all', label: 'All' },
  ...DOC_CATEGORIES.map(c => ({ value: c.id, labelKey: c.labelKey, label: c.label })),
];

function formatFileSize(bytes) {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleDateString('es-ES', {
      day: '2-digit', month: 'short', year: 'numeric'
    });
  } catch {
    return dateStr;
  }
}

function getFileType(filename, mimeType) {
  if (mimeType) {
    if (['image/jpeg', 'image/jpg', 'image/png', 'image/webp'].includes(mimeType)) return 'image';
    if (mimeType === 'application/pdf') return 'pdf';
  }
  const ext = filename?.split('.').pop()?.toLowerCase();
  if (['jpg', 'jpeg', 'png', 'webp'].includes(ext)) return 'image';
  if (ext === 'pdf') return 'pdf';
  return 'other';
}

function getFileIcon(type) {
  if (type === 'image') return Image;
  if (type === 'pdf') return FileText;
  return File;
}

export default function DocumentsPage() {
  const { t } = useTranslation();
  const { user, isAdmin, isBDCManager } = useAuth();
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedClient, setSelectedClient] = useState(null);
  const [clientDocs, setClientDocs] = useState({});
  const [uploading, setUploading] = useState(false);
  const [viewMode, setViewMode] = useState('table');
  const [docViewer, setDocViewer] = useState({ open: false, documents: [], initialIndex: 0, clientName: '', docCategory: '' });
  const [docCategoryDialog, setDocCategoryDialog] = useState({ open: false, clientId: null, clientName: '', category: null });

  const fetchClients = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ exclude_sold: 'false', sort_by: 'name' });
      if (searchTerm) params.append('search', searchTerm);
      if (!isAdmin && !isBDCManager) {
        params.append('salesperson_id', user.id);
      }
      const response = await axios.get(`${API}/clients?${params.toString()}`);
      setClients(response.data);
    } catch (error) {
      console.error('Failed to fetch clients:', error);
      setClients([]);
    } finally {
      setLoading(false);
    }
  }, [searchTerm, user, isAdmin, isBDCManager]);

  useEffect(() => {
    fetchClients();
  }, [fetchClients]);

  const fetchClientDocs = async (clientId) => {
    try {
      const [idRes, incomeRes, residenceRes] = await Promise.all([
        axios.get(`${API}/clients/${clientId}/documents/list/id`).catch(() => ({ data: { documents: [], count: 0 } })),
        axios.get(`${API}/clients/${clientId}/documents/list/income`).catch(() => ({ data: { documents: [], count: 0 } })),
        axios.get(`${API}/clients/${clientId}/documents/list/residence`).catch(() => ({ data: { documents: [], count: 0 } })),
      ]);
      const client = clients.find(c => c.id === clientId);
      setClientDocs({
        id: (idRes.data.documents || []).map(d => ({ ...d, client_id: clientId, doc_type: 'id' })),
        income: (incomeRes.data.documents || []).map(d => ({ ...d, client_id: clientId, doc_type: 'income' })),
        residence: (residenceRes.data.documents || []).map(d => ({ ...d, client_id: clientId, doc_type: 'residence' })),
        client,
      });
      setSelectedClient(clientId);
    } catch (error) {
      toast.error('Failed to load documents');
    }
  };

  const handleUpload = async (clientId, type, fileList) => {
    if (!fileList || fileList.length === 0) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('doc_type', type);
      Array.from(fileList).forEach(file => formData.append('files', file));
      await axios.post(`${API}/clients/${clientId}/documents/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success('Document(s) uploaded');
      fetchClientDocs(clientId);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Upload failed');
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

  const handleDownload = async (clientId, type, doc) => {
    try {
      let url = `${API}/clients/${clientId}/documents/download/${type}`;
      if (doc.id && doc.id !== 'legacy') {
        url += `?doc_id=${doc.id}`;
      }
      const response = await axios.get(url, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        responseType: 'blob'
      });
      const blob = new Blob([response.data]);
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = doc.original_name || doc.filename || `document_${type}`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(downloadUrl);
      toast.success('Download started');
    } catch (err) {
      toast.error('Download failed');
    }
  };

  const handleDownloadAll = async (clientId, type) => {
    try {
      const url = `${API}/clients/${clientId}/documents/download/${type}`;
      const response = await axios.get(url, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        responseType: 'blob'
      });
      const blob = new Blob([response.data]);
      const downloadUrl = URL.createObjectURL(blob);
      const client = clients.find(c => c.id === clientId);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = `${client?.first_name}_${client?.last_name}_${type}_all.pdf`.replace(/\s+/g, '_');
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(downloadUrl);
      toast.success('ZIP/PDF download started');
    } catch (err) {
      toast.error('Download failed');
    }
  };

  const handlePreview = (doc, docs, index, clientName, category) => {
    const viewableDocs = docs.filter(d => {
      const ext = d.filename?.split('.').pop()?.toLowerCase();
      return ['jpg', 'jpeg', 'png', 'webp', 'pdf'].includes(ext) || 
             ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'application/pdf'].includes(d.type);
    });
    const viewableIndex = viewableDocs.findIndex(d => d.id === doc.id);
    if (viewableIndex >= 0) {
      setDocViewer({ open: true, documents: viewableDocs, initialIndex: viewableIndex, clientName, docCategory: category });
    }
  };

  const handlePreviewFromCategoryDialog = (documents, index, clientName, docCategory) => {
    setDocViewer({ open: true, documents, initialIndex: index, clientName, docCategory });
  };

  const getCategoryStatus = (client, categoryId) => {
    if (categoryId === 'id') return client.id_documents?.length > 0 || client.id_uploaded ? 'complete' : 'missing';
    if (categoryId === 'income') return client.income_documents?.length > 0 || client.income_proof_uploaded ? 'complete' : 'missing';
    if (categoryId === 'residence') return client.residence_documents?.length > 0 || client.residence_proof_uploaded ? 'complete' : 'missing';
    return 'missing';
  };

  const getOverallStatus = (client) => {
    const idCount = client.id_documents?.length || (client.id_uploaded ? 1 : 0);
    const incomeCount = client.income_documents?.length || (client.income_proof_uploaded ? 1 : 0);
    const residenceCount = client.residence_documents?.length || (client.residence_proof_uploaded ? 1 : 0);
    if (idCount > 0 && incomeCount > 0 && residenceCount > 0) return 'complete';
    if (idCount > 0 || incomeCount > 0 || residenceCount > 0) return 'pending';
    return 'missing';
  };

  if (loading) {
    return (
      <div className="space-y-6" data-testid="documents-page">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground">{t('documents.title')}</h1>
            <p className="text-muted-foreground mt-1">Loading documents...</p>
          </div>
        </div>
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input placeholder={t('documents.search')} disabled className="pl-10" />
              </div>
            </div>
          </CardContent>
        </Card>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <Card key={i} className="border-l-4 border-l-primary">
              <CardContent className="p-4">
                <div className="loading-spinner" style={{width: '100%', height: '80px', borderWidth: '2px', borderRadius: '8px'}} />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const filteredClients = clients.filter(c => {
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      const name = `${c.first_name} ${c.last_name}`.toLowerCase();
      if (!name.includes(term) && !c.phone?.includes(term)) return false;
    }
    if (statusFilter !== 'all') {
      const status = getOverallStatus(c);
      if (status !== statusFilter) return false;
    }
    if (typeFilter !== 'all') {
      const catStatus = getCategoryStatus(c, typeFilter);
      if (statusFilter !== 'all') {
        if (catStatus !== statusFilter) return false;
      } else {
        if (catStatus === 'missing') return false;
      }
    }
    return true;
  });

  return (
    <div className="space-y-6" data-testid="documents-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('documents.title')}</h1>
          <p className="text-muted-foreground mt-1">
            {clients.length} clients • Document management
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setViewMode('table')}>
            <LayoutList className="w-4 h-4 mr-1" /> Table
          </Button>
          <Button variant="outline" size="sm" onClick={() => setViewMode('cards')}>
            <LayoutGrid className="w-4 h-4 mr-1" /> Cards
          </Button>
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
                {TYPE_FILTER_OPTIONS.map(opt => (
                  <SelectItem key={opt.value} value={opt.value}>{t(opt.labelKey) || opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-40">
                <SelectValue placeholder={t('documents.status')} />
              </SelectTrigger>
              <SelectContent>
                {STATUS_OPTIONS.map(opt => (
                  <SelectItem key={opt.value} value={opt.value}>{t(opt.labelKey) || opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Document Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {DOC_CATEGORIES.map((cat) => {
          const complete = clients.filter(c => {
            if (cat.id === 'id') return c.id_uploaded;
            if (cat.id === 'income') return c.income_proof_uploaded;
            if (cat.id === 'residence') return c.residence_proof_uploaded;
            return false;
          }).length;
          const pending = clients.length - complete;
          return (
            <Card key={cat.id} className={`border-l-4 border-l-${cat.color}-500`}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{t(cat.labelKey) || cat.label}</p>
                    <p className="text-2xl font-bold text-foreground">{complete}/{clients.length}</p>
                  </div>
                  <div className={`p-3 rounded-lg bg-${cat.color}-500/10`}>
                    <cat.icon className={`w-6 h-6 text-${cat.color}-500`} />
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-4 text-sm">
                  <span className="flex items-center gap-1 text-emerald-500">
                    <CheckCircle className="w-4 h-4" /> {complete} {t('documents.complete') || 'Complete'}
                  </span>
                  <span className="flex items-center gap-1 text-amber-500">
                    <AlertCircle className="w-4 h-4" /> {pending} {t('documents.pending') || 'Pending'}
                  </span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Client Documents - Table View */}
      {viewMode === 'table' && (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-b border-border bg-muted/50">
                    <TableHead className="p-4 text-left font-medium text-muted-foreground">Client</TableHead>
                    <TableHead className="p-4 text-left font-medium text-muted-foreground">Phone</TableHead>
                    <TableHead className="p-4 text-left font-medium text-muted-foreground">{t('documents.id') || 'ID'}</TableHead>
                    <TableHead className="p-4 text-left font-medium text-muted-foreground">{t('documents.income') || 'Income Proof'}</TableHead>
                    <TableHead className="p-4 text-left font-medium text-muted-foreground">{t('documents.residence') || 'Residence Proof'}</TableHead>
                    <TableHead className="p-4 text-left font-medium text-muted-foreground">{t('documents.status') || 'Status'}</TableHead>
                    <TableHead className="p-4 text-left font-medium text-muted-foreground">Total Files</TableHead>
                    <TableHead className="p-4 text-right font-medium text-muted-foreground">{t('common.actions') || 'Actions'}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredClients.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="p-12 text-center text-muted-foreground">
                        {t('documents.noDocuments') || 'No documents found'}
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredClients.map((client) => {
                      const status = getOverallStatus(client);
                      const idCount = client.id_documents?.length || (client.id_uploaded ? 1 : 0);
                      const incomeCount = client.income_documents?.length || (client.income_proof_uploaded ? 1 : 0);
                      const residenceCount = client.residence_documents?.length || (client.residence_proof_uploaded ? 1 : 0);
                      const totalFiles = idCount + incomeCount + residenceCount;
                      return (
                        <TableRow key={client.id} className="border-b border-border/50 hover:bg-muted/50 cursor-pointer" onClick={() => fetchClientDocs(client.id)}>
                          <TableCell className="p-4">
                            <p className="font-medium text-foreground">{client.first_name} {client.last_name}</p>
                          </TableCell>
                          <TableCell className="p-4 font-mono text-sm">{client.phone}</TableCell>
                          <TableCell className="p-4">
                            {idCount > 0 ? (
                              <span className="flex items-center gap-1 text-emerald-500"><CheckCircle className="w-4 h-4" /> {idCount} {t('documents.files') || 'files'}</span>
                            ) : (
                              <span className="flex items-center gap-1 text-amber-500"><AlertCircle className="w-4 h-4" /> {t('documents.missing') || 'Missing'}</span>
                            )}
                          </TableCell>
                          <TableCell className="p-4">
                            {incomeCount > 0 ? (
                              <span className="flex items-center gap-1 text-emerald-500"><CheckCircle className="w-4 h-4" /> {incomeCount} {t('documents.files') || 'files'}</span>
                            ) : (
                              <span className="flex items-center gap-1 text-amber-500"><AlertCircle className="w-4 h-4" /> {t('documents.missing') || 'Missing'}</span>
                            )}
                          </TableCell>
                          <TableCell className="p-4">
                            {residenceCount > 0 ? (
                              <span className="flex items-center gap-1 text-emerald-500"><CheckCircle className="w-4 h-4" /> {residenceCount} {t('documents.files') || 'files'}</span>
                            ) : (
                              <span className="flex items-center gap-1 text-amber-500"><AlertCircle className="w-4 h-4" /> {t('documents.missing') || 'Missing'}</span>
                            )}
                          </TableCell>
                          <TableCell className="p-4">
                            {status === 'complete' ? (
                              <Badge variant="default" className="text-xs">{t('documents.complete') || 'Complete'}</Badge>
                            ) : status === 'pending' ? (
                              <Badge variant="secondary" className="text-xs">{t('documents.pending') || 'Pending'}</Badge>
                            ) : (
                              <Badge variant="destructive" className="text-xs">{t('documents.missing') || 'Missing'}</Badge>
                            )}
                          </TableCell>
                          <TableCell className="p-4 font-mono text-sm">{totalFiles}</TableCell>
                          <TableCell className="p-4 text-right">
                            <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); fetchClientDocs(client.id); }}>
                              <Eye className="w-4 h-4 mr-1" /> {t('common.view') || 'View'}
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Client Documents - Card View (Mobile) */}
      {viewMode === 'cards' && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredClients.map((client) => {
            const status = getOverallStatus(client);
            const idCount = client.id_documents?.length || (client.id_uploaded ? 1 : 0);
            const incomeCount = client.income_documents?.length || (client.income_proof_uploaded ? 1 : 0);
            const residenceCount = client.residence_documents?.length || (client.residence_proof_uploaded ? 1 : 0);
            const totalFiles = idCount + incomeCount + residenceCount;
            return (
              <Card key={client.id} className="border-l-4 border-l-primary hover:shadow-lg transition-shadow cursor-pointer" onClick={() => fetchClientDocs(client.id)}>
                <CardContent className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="font-semibold text-foreground truncate">{client.first_name} {client.last_name}</p>
                      <p className="text-sm text-muted-foreground font-mono">{client.phone}</p>
                    </div>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      status === 'complete' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                      status === 'pending' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' :
                      'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                    }`}>
                      {t(`documents.${status}`) || status}
                    </span>
                  </div>
                  <div className="mt-3 flex items-center gap-2 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <FileText className="w-3 h-3" /> {totalFiles} files
                    </span>
                    <span className="flex items-center gap-1">
                      {idCount > 0 ? <CheckCircle className="w-3 h-3 text-emerald-500" /> : <AlertCircle className="w-3 h-3 text-amber-500" />}
                      <span>{idCount}</span>
                    </span>
                    <span className="flex items-center gap-1">
                      {incomeCount > 0 ? <CheckCircle className="w-3 h-3 text-emerald-500" /> : <AlertCircle className="w-3 h-3 text-amber-500" />}
                      <span>{incomeCount}</span>
                    </span>
                    <span className="flex items-center gap-1">
                      {residenceCount > 0 ? <CheckCircle className="w-3 h-3 text-emerald-500" /> : <AlertCircle className="w-3 h-3 text-amber-500" />}
                      <span>{residenceCount}</span>
                    </span>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Client Documents Detail Dialog */}
      {selectedClient && clientDocs.client && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={() => { setSelectedClient(null); setClientDocs({}); }}>
          <div className="bg-card rounded-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
            <div className="p-4 border-b border-border flex items-center justify-between bg-muted/50">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-primary/15 border border-primary/30 flex items-center justify-center">
                  <FileText className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-foreground">{clientDocs.client.first_name} {clientDocs.client.last_name} - Documents</h2>
                  <p className="text-sm text-muted-foreground">{clientDocs.client.phone}</p>
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={() => { setSelectedClient(null); setClientDocs({}); }}>
                <XCircleIcon className="w-5 h-5" />
              </Button>
            </div>
            <div className="p-4 overflow-y-auto space-y-6">
              {DOC_CATEGORIES.map((cat) => {
                const docs = clientDocs[cat.id] || [];
                const status = docs.length > 0 ? 'complete' : 'missing';
                return (
                  <div key={cat.id}>
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-medium flex items-center gap-2 text-foreground">
                        <cat.icon className={`w-5 h-5 text-${cat.color}-500`} />
                        {t(cat.labelKey) || cat.label} ({docs.length})
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                          status === 'complete' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' :
                          'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                        }`}>
                          {t(`documents.${status}`) || status}
                        </span>
                      </h3>
                      <label className="cursor-pointer">
                        <input
                          type="file"
                          accept=".pdf,.jpg,.jpeg,.png,.webp"
                          multiple
                          className="sr-only"
                          onChange={(e) => e.target.files?.length && handleUpload(selectedClient, cat.id, e.target.files)}
                          disabled={uploading}
                        />
                        <Button variant="outline" size="sm" disabled={uploading}>
                          <Upload className="w-4 h-4 mr-1" /> {t('common.upload') || 'Upload'}
                        </Button>
                      </label>
                    </div>
                    {docs.length === 0 ? (
                      <div className="border-2 border-dashed border-border/50 rounded-lg p-8 text-center text-muted-foreground">
                        <cat.icon className={`w-12 h-12 text-${cat.color}-500/50 mx-auto mb-3`} />
                        <p>No {t(cat.labelKey)?.toLowerCase() || cat.label.toLowerCase()} uploaded</p>
                        <p className="text-xs mt-1">Click "Upload" to add the first document</p>
                      </div>
                    ) : (
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {docs.map((doc) => {
                          const fileType = getFileType(doc.filename || doc.original_name, doc.type);
                          const FileIcon = getFileIcon(fileType);
                          const canPreview = fileType === 'image' || fileType === 'pdf';
                          return (
                            <div key={doc.id} className="p-3 border border-border rounded-lg bg-muted/30 flex flex-col">
                              <div className="flex items-center gap-3 min-w-0 mb-2">
                                <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                                  fileType === 'image' ? 'bg-emerald-500/15 border border-emerald-500/30' :
                                  fileType === 'pdf' ? 'bg-rose-500/15 border border-rose-500/30' :
                                  'bg-slate-800 border border-slate-700'
                                }`}>
                                  <FileIcon className={`w-5 h-5 ${
                                    fileType === 'image' ? 'text-emerald-400' :
                                    fileType === 'pdf' ? 'text-rose-400' :
                                    'text-slate-400'
                                  }`} />
                                </div>
                                <div className="min-w-0 flex-1">
                                  <p className="font-medium text-sm truncate text-foreground">{doc.original_name || doc.filename || 'document'}</p>
                                  <p className="text-xs text-muted-foreground">
                                    {doc.uploaded_at ? formatDate(doc.uploaded_at) : ''}
                                    {doc.size && ` • ${formatFileSize(doc.size)}`}
                                    {doc.type && ` • ${doc.type.split('/')[1]?.toUpperCase() || 'FILE'}`}
                                  </p>
                                </div>
                              </div>
                              <div className="flex items-center gap-1 pt-2 border-t border-border/50">
                                {canPreview && (
                                  <Button
                                    variant="ghost"
                                    size="icon"
                                    onClick={() => handlePreview(doc, docs, docs.indexOf(doc), `${clientDocs.client.first_name} ${clientDocs.client.last_name}`, t(cat.labelKey) || cat.label)}
                                    className="text-muted-foreground hover:text-primary h-8 w-8"
                                    title={t('common.view') || 'View'}
                                  >
                                    <Eye className="w-4 h-4" />
                                  </Button>
                                )}
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => handleDownload(selectedClient, cat.id, doc)}
                                  className="text-muted-foreground hover:text-primary h-8 w-8"
                                  title={t('common.download') || 'Download'}
                                >
                                  <Download className="w-4 h-4" />
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => handleDelete(selectedClient, cat.id, doc.id)}
                                  className="text-muted-foreground hover:text-destructive h-8 w-8"
                                  title={t('common.delete') || 'Delete'}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </Button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <div className="p-4 border-t border-border bg-muted/50 flex justify-end gap-2">
              <Button variant="outline" onClick={() => handleDownloadAll(selectedClient, 'id')}>
                <Download className="w-4 h-4 mr-1" /> Download All ID
              </Button>
              <Button variant="outline" onClick={() => handleDownloadAll(selectedClient, 'income')}>
                <Download className="w-4 h-4 mr-1" /> Download All Income
              </Button>
              <Button variant="outline" onClick={() => handleDownloadAll(selectedClient, 'residence')}>
                <Download className="w-4 h-4 mr-1" /> Download All Residence
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Document Viewer */}
      <DocumentViewer
        isOpen={docViewer.open}
        onClose={() => setDocViewer({ open: false, documents: [], initialIndex: 0, clientName: '', docCategory: '' })}
        documents={docViewer.documents}
        initialIndex={docViewer.initialIndex}
        clientName={docViewer.clientName}
        docCategory={docViewer.docCategory}
      />

      {/* Document Category Dialog (legacy support for ClientsPage) */}
      <DocumentCategoryDialog
        isOpen={docCategoryDialog.open}
        onClose={() => setDocCategoryDialog({ open: false, clientId: null, clientName: '', category: null })}
        clientId={docCategoryDialog.clientId}
        clientName={docCategoryDialog.clientName}
        category={docCategoryDialog.category}
        onUploadComplete={fetchClients}
        onPreview={handlePreviewFromCategoryDialog}
      />
    </div>
  );
}