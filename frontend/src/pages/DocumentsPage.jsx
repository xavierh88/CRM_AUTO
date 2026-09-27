import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import {
  AlertCircle, CheckCircle2, ChevronRight, Download, Eye, File, FileImage,
  FileText, FileSpreadsheet, Loader2, Search, Upload, X
} from 'lucide-react';
import DocumentViewer from '../components/DocumentViewer';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const CATEGORIES = [
  { id: 'id', label: 'Identification Documents', short: 'ID', icon: FileText },
  { id: 'income', label: 'Income Proof', short: 'Income', icon: FileText },
  { id: 'residence', label: 'Residence Proof', short: 'Residence', icon: FileText },
];

const countFor = (client, type) => {
  if (type === 'id') return client.id_documents?.length || (client.id_uploaded ? 1 : 0);
  if (type === 'income') return client.income_documents?.length || (client.income_proof_uploaded ? 1 : 0);
  return client.residence_documents?.length || (client.residence_proof_uploaded ? 1 : 0);
};

const overallStatus = (client) => {
  const counts = CATEGORIES.map((c) => countFor(client, c.id));
  if (counts.every(Boolean)) return 'complete';
  if (counts.some(Boolean)) return 'pending';
  return 'missing';
};

const fileName = (doc) => doc.original_name || doc.filename || doc.name || 'document';
const fileExt = (doc) => fileName(doc).split('.').pop()?.toUpperCase() || 'FILE';
const fileSize = (bytes) => {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
};
const fileDate = (value) => {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleDateString();
};
const previewable = (doc) => {
  const ext = fileName(doc).split('.').pop()?.toLowerCase();
  return ['pdf', 'jpg', 'jpeg', 'png', 'webp'].includes(ext) ||
    ['application/pdf', 'image/jpeg', 'image/jpg', 'image/png', 'image/webp'].includes(doc.type);
};

function StatusPill({ status }) {
  const styles = {
    complete: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    pending: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
    missing: 'border-slate-700 bg-slate-900 text-slate-400',
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium capitalize ${styles[status]}`}>
      {status === 'complete' && <CheckCircle2 className="mr-1.5 h-3.5 w-3.5" />}
      {status !== 'complete' && <AlertCircle className="mr-1.5 h-3.5 w-3.5" />}
      {status}
    </span>
  );
}

function FormatSummary({ documents = [] }) {
  if (!documents.length) {
    return <span className="text-xs font-medium text-slate-500">0 files</span>;
  }
  const groups = documents.reduce((acc, doc) => {
    const ext = fileExt(doc);
    acc[ext] = (acc[ext] || 0) + 1;
    return acc;
  }, {});
  return (
    <div className="flex flex-wrap gap-1.5">
      {Object.entries(groups).map(([format, count]) => {
        const Icon = ['XLS', 'XLSX'].includes(format) ? FileSpreadsheet
          : ['PNG', 'JPG', 'JPEG', 'WEBP'].includes(format) ? FileImage
          : FileText;
        return (
          <span key={format} className="inline-flex items-center gap-1 rounded-lg border border-slate-700 bg-slate-900 px-2 py-1 text-xs font-semibold text-slate-200">
            <Icon className="h-3.5 w-3.5 text-cyan-400" />
            {count} {format}
          </span>
        );
      })}
    </div>
  );
}

export default function DocumentsPage() {
  const { t } = useTranslation();
  const { user, isAdmin, isBDCManager } = useAuth();
  const navigate = useNavigate();
  const [clients, setClients] = useState([]);
  const [documentIndex, setDocumentIndex] = useState({});
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedClient, setSelectedClient] = useState(null);
  const [docs, setDocs] = useState({ id: [], income: [], residence: [] });
  const [detailLoading, setDetailLoading] = useState(false);
  const [uploading, setUploading] = useState(null);
  const [viewer, setViewer] = useState({ open: false, documents: [], initialIndex: 0, clientName: '', docCategory: '' });

  const fetchClients = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ exclude_sold: 'false', sort_by: 'name' });
      if (!isAdmin && !isBDCManager && user?.id) params.append('salesperson_id', user.id);
      const response = await axios.get(`${API}/clients?${params.toString()}`);
      const loadedClients = Array.isArray(response.data) ? response.data : [];
      setClients(loadedClients);
      const entries = await Promise.all(loadedClients.map(async (client) => {
        const results = await Promise.all(CATEGORIES.map((category) =>
          axios.get(`${API}/clients/${client.id}/documents/list/${category.id}`)
            .then((res) => res.data?.documents || [])
            .catch(() => [])
        ));
        return [client.id, { id: results[0], income: results[1], residence: results[2] }];
      }));
      setDocumentIndex(Object.fromEntries(entries));
    } catch (error) {
      console.error(error);
      toast.error('Unable to load clients');
      setClients([]);
    } finally {
      setLoading(false);
    }
  }, [isAdmin, isBDCManager, user?.id]);

  useEffect(() => { fetchClients(); }, [fetchClients]);

  const realCount = useCallback((client, type) => documentIndex[client.id]?.[type]?.length || 0, [documentIndex]);
  const realStatus = useCallback((client) => {
    const counts = CATEGORIES.map((category) => realCount(client, category.id));
    if (counts.every(Boolean)) return 'complete';
    if (counts.some(Boolean)) return 'pending';
    return 'missing';
  }, [realCount]);

  const filtered = useMemo(() => clients.filter((client) => {
    const term = search.trim().toLowerCase();
    const haystack = `${client.first_name || ''} ${client.last_name || ''} ${client.phone || ''}`.toLowerCase();
    return (!term || haystack.includes(term)) &&
      (statusFilter === 'all' || realStatus(client) === statusFilter);
  }), [clients, search, statusFilter, realStatus]);

  const withDocumentMeta = (clientId, type, list) => list.map((doc) => ({ ...doc, client_id: clientId, doc_type: type }));
  const clientDisplayName = (client) => `${client?.first_name || ''} ${client?.last_name || ''}`.trim() || 'Unnamed client';

  const openClient = async (client) => {
    setSelectedClient(client);
    setDetailLoading(true);
    try {
      const results = await Promise.all(CATEGORIES.map((category) =>
        axios.get(`${API}/clients/${client.id}/documents/list/${category.id}`)
          .then((response) => response.data?.documents || [])
          .catch(() => [])
      ));
      setDocs({ id: withDocumentMeta(client.id, 'id', results[0]), income: withDocumentMeta(client.id, 'income', results[1]), residence: withDocumentMeta(client.id, 'residence', results[2]) });
    } finally {
      setDetailLoading(false);
    }
  };

  const refreshClient = async () => {
    if (!selectedClient) return;
    await openClient(selectedClient);
    await fetchClients();
  };

  const upload = async (type, files) => {
    if (!selectedClient || !files?.length) return;
    setUploading(type);
    try {
      const body = new FormData();
      body.append('doc_type', type);
      Array.from(files).forEach((file) => body.append('files', file));
      await axios.post(`${API}/clients/${selectedClient.id}/documents/upload`, body, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      toast.success('Documents uploaded');
      await refreshClient();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(null);
    }
  };

  const downloadBlob = async (url, name) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!response.ok) {
        let detail = 'Download failed';
        try {
          const body = await response.json();
          if (typeof body?.detail === 'string') detail = body.detail;
        } catch (_) {}
        throw new Error(detail);
      }
      const blob = await response.blob();
      const objectUrl = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = objectUrl;
      anchor.download = name;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
    } catch (error) {
      console.error('Document download failed:', error);
      toast.error(error.message || 'Download failed');
    }
  };

  const downloadDocument = (type, doc) => {
    const query = doc.id && doc.id !== 'legacy' ? `?doc_id=${encodeURIComponent(doc.id)}` : '';
    return downloadBlob(
      `${API}/clients/${selectedClient.id}/documents/download/${type}${query}`,
      fileName(doc)
    );
  };

  const downloadAll = () => downloadBlob(
    `${API}/clients/${selectedClient.id}/documents/download-all`,
    `${selectedClient.first_name || 'client'}_${selectedClient.last_name || ''}_documents.zip`.replace(/\s+/g, '_')
  );

  const showPreview = (type, doc) => {
    const list = docs[type].filter(previewable);
    const index = list.findIndex((item) => item.id === doc.id);
    setViewer({
      open: true,
      documents: list,
      initialIndex: Math.max(0, index),
      clientName: `${selectedClient.first_name || ''} ${selectedClient.last_name || ''}`.trim(),
      docCategory: CATEGORIES.find((category) => category.id === type)?.label || '',
    });
  };

  if (selectedClient) {
    const total = CATEGORIES.reduce((sum, category) => sum + docs[category.id].length, 0);
    return (
      <div className="space-y-5" data-testid="documents-client-detail">
        <button type="button" onClick={() => setSelectedClient(null)} className="text-sm text-slate-400 hover:text-cyan-300">
          Clients <span className="px-1">›</span> {selectedClient.first_name} {selectedClient.last_name} <span className="px-1">›</span> Documents
        </button>

        <section className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 sm:p-5">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex min-w-0 items-center gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-cyan-500/30 bg-cyan-500/10 text-lg font-bold text-cyan-300">
                {(selectedClient.first_name?.[0] || '')}{(selectedClient.last_name?.[0] || '')}
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <button type="button" onClick={() => navigate('/clients', { state: { openClientId: selectedClient.id, openClientTab: 'summary' } })} className="block max-w-full truncate text-left text-xl font-semibold text-white transition hover:text-cyan-300 hover:underline"><span className="block truncate" title={clientDisplayName(selectedClient)}>{clientDisplayName(selectedClient)}</span></button>
                  <StatusPill status={CATEGORIES.every((category) => docs[category.id].length) ? 'complete' : total ? 'pending' : 'missing'} />
                </div>
                <p className="mt-1 text-sm text-slate-400">{selectedClient.phone || 'No phone'}{selectedClient.email ? ` • ${selectedClient.email}` : ''}</p>
                <p className="text-xs text-slate-500">{selectedClient.assigned_salesperson || selectedClient.salesperson_name || 'Unassigned salesperson'}{selectedClient.vehicle_interest ? ` • ${selectedClient.vehicle_interest}` : ''}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" onClick={downloadAll} disabled={!total}>
                <Download className="mr-2 h-4 w-4" /> Download All (ZIP)
              </Button>

            </div>
          </div>
        </section>

        {detailLoading ? (
          <div className="flex min-h-[320px] items-center justify-center rounded-2xl border border-slate-800 bg-slate-950/60">
            <Loader2 className="h-7 w-7 animate-spin text-cyan-400" />
          </div>
        ) : (
          <div className="grid gap-4 xl:grid-cols-3">
            {CATEGORIES.map((category) => {
              const list = docs[category.id];
              const Icon = category.icon;
              return (
                <section key={category.id} className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950/70">
                  <div className="border-b border-slate-800 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex gap-3">
                        <div className="rounded-lg border border-cyan-500/20 bg-cyan-500/10 p-2 text-cyan-300"><Icon className="h-5 w-5" /></div>
                        <div>
                          <h2 className="font-semibold text-slate-100">{category.label}</h2>
                          <p className="text-xs text-slate-500">{list.length} {list.length === 1 ? 'file' : 'files'}</p>
                        </div>
                      </div>
                      <StatusPill status={list.length ? 'complete' : 'missing'} />
                    </div>
                    <label className="mt-3 block">
                      <input type="file" multiple accept=".pdf,.jpg,.jpeg,.png,.doc,.docx,.xls,.xlsx" className="hidden" onChange={(e) => upload(category.id, e.target.files)} />
                      <Button asChild variant="outline" size="sm" className="w-full"><span>{uploading === category.id ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Upload className="mr-2 h-4 w-4" />}Upload more</span></Button>
                    </label>
                  </div>

                  <div className="space-y-2 p-3">
                    {!list.length && <div className="rounded-xl border border-dashed border-slate-800 p-8 text-center text-sm text-slate-500">No files uploaded</div>}
                    {list.map((doc, index) => (
                      <div key={doc.id || `${category.id}-${index}`} className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
                        <div className="flex gap-3">
                          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-800 text-cyan-300">
                            {fileExt(doc) === 'PDF' ? <FileText className="h-5 w-5" /> : ['JPG','JPEG','PNG','WEBP'].includes(fileExt(doc)) ? <FileImage className="h-5 w-5" /> : <File className="h-5 w-5" />}
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium text-slate-100">{fileName(doc)}</p>
                            <p className="mt-0.5 text-xs text-slate-500">{fileExt(doc)} • {fileSize(doc.size)} • {fileDate(doc.uploaded_at)}</p>
                          </div>
                        </div>
                        <div className="mt-3 grid grid-cols-2 gap-2">
                          <Button variant="ghost" size="sm" disabled={!previewable(doc)} onClick={() => showPreview(category.id, doc)}><Eye className="mr-1.5 h-4 w-4" /> View</Button>
                          <Button variant="ghost" size="sm" onClick={() => downloadDocument(category.id, doc)}><Download className="mr-1.5 h-4 w-4" /> Download</Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              );
            })}
          </div>
        )}

        <DocumentViewer
          isOpen={viewer.open}
          onClose={() => setViewer({ open: false, documents: [], initialIndex: 0, clientName: '', docCategory: '' })}
          documents={viewer.documents}
          initialIndex={viewer.initialIndex}
          clientName={viewer.clientName}
          docCategory={viewer.docCategory}
        />
      </div>
    );
  }

  return (
    <div className="space-y-5" data-testid="documents-page">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">{t('documents.title') || 'Documents'}</h1>
          <p className="mt-1 text-sm text-slate-400">View and manage all client documents</p>
        </div>
        <Button variant="outline" onClick={fetchClients}><Download className="mr-2 h-4 w-4" /> Export</Button>
      </div>

      <section className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
            <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search client or phone" className="border-slate-800 bg-slate-900 pl-10" />
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1 lg:pb-0">
            {['all', 'complete', 'pending', 'missing'].map((status) => (
              <button key={status} type="button" onClick={() => setStatusFilter(status)} className={`whitespace-nowrap rounded-full border px-3 py-2 text-xs font-medium capitalize transition ${
                statusFilter === status ? 'border-cyan-400 bg-cyan-500/15 text-cyan-300' : 'border-slate-800 bg-slate-900 text-slate-400'
              }`}>{status}</button>
            ))}
          </div>
        </div>
      </section>

      {loading ? (
        <div className="flex min-h-[300px] items-center justify-center"><Loader2 className="h-7 w-7 animate-spin text-cyan-400" /></div>
      ) : (
        <>
          <div className="hidden overflow-hidden rounded-2xl border border-slate-800 bg-slate-950/70 md:block">
            <table className="w-full">
              <thead className="border-b border-slate-800 bg-slate-900/70 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Client</th><th className="px-4 py-3">ID Documents</th><th className="px-4 py-3">Income Proof</th><th className="px-4 py-3">Residence Proof</th><th className="px-4 py-3">Total Files</th><th className="px-4 py-3">Status</th><th className="px-4 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {filtered.map((client) => {
                  const counts = CATEGORIES.map((category) => realCount(client, category.id));
                  return (
                    <tr key={client.id} className="hover:bg-slate-900/60">
                      <td className="px-4 py-4"><button type="button" onClick={() => navigate('/clients', { state: { openClientId: client.id, openClientTab: 'summary' } })} className="block max-w-[220px] truncate font-medium text-slate-100 transition hover:text-cyan-300 hover:underline" title={clientDisplayName(client)}>{clientDisplayName(client)}</button><p className="text-xs text-slate-500">{client.phone || 'No phone'}</p></td>
                      {counts.map((count, index) => <td key={CATEGORIES[index].id} className="px-4 py-4"><FormatSummary documents={documentIndex[client.id]?.[CATEGORIES[index].id] || []} /></td>)}
                      <td className="px-4 py-4 text-sm font-semibold text-slate-200">{counts.reduce((a,b) => a+b, 0)}</td>
                      <td className="px-4 py-4"><StatusPill status={realStatus(client)} /></td>
                      <td className="px-4 py-4 text-right"><Button variant="ghost" size="sm" onClick={() => openClient(client)}>View <ChevronRight className="ml-1 h-4 w-4" /></Button></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {!filtered.length && <div className="p-12 text-center text-sm text-slate-500">No clients match these filters.</div>}
          </div>

          <div className="space-y-3 md:hidden">
            {filtered.map((client) => {
              const counts = CATEGORIES.map((category) => realCount(client, category.id));
              return (
                <button key={client.id} type="button" onClick={() => openClient(client)} className="w-full rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-left">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex min-w-0 gap-3">
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-cyan-500/10 font-semibold text-cyan-300">{client.first_name?.[0]}{client.last_name?.[0]}</div>
                      <div className="min-w-0"><p className="truncate font-semibold text-slate-100" title={clientDisplayName(client)}>{clientDisplayName(client)}</p><p className="text-xs text-slate-500">{counts.reduce((a,b) => a+b, 0)} total files</p></div>
                    </div>
                    <StatusPill status={realStatus(client)} />
                  </div>
                  <div className="mt-4 grid grid-cols-3 gap-2">
                    {CATEGORIES.map((category, index) => <div key={category.id} className="rounded-lg border border-slate-800 bg-slate-900/70 p-2"><p className="text-[11px] text-slate-500">{category.short}</p><p className="mt-1 text-sm font-semibold text-cyan-300">{counts[index]}</p></div>)}
                  </div>
                  <div className="mt-3 flex items-center justify-end text-xs font-medium text-cyan-300">Open documents <ChevronRight className="ml-1 h-4 w-4" /></div>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
