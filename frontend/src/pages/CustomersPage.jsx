import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import {
  Plus, Search, Users, UserPlus, Phone, Mail, MapPin, FileText,
  ChevronDown, ChevronUp, Edit, Trash2, Eye, MoreHorizontal,
  CheckCircle, AlertCircle, Calendar, DollarSign, Activity,
  ExternalLink, Download, Upload, LayoutGrid, LayoutList
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function CustomersPage() {
  const { t } = useTranslation();
  const { user, isAdmin, isBDCManager } = useAuth();
  const navigate = useNavigate();
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [sortBy, setSortBy] = useState('last_contact');
  const [sortOrder, setSortOrder] = useState('desc');
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [totalCount, setTotalCount] = useState(0);
  const [viewMode, setViewMode] = useState('table');

  // Document state
  const [docClient, setDocClient] = useState(null);
  const [documents, setDocuments] = useState({ id: [], income: [] });
  const [uploading, setUploading] = useState(false);

  const fetchCustomers = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ exclude_sold: 'false' });
      if (searchTerm) params.append('search', searchTerm);
      if (statusFilter !== 'all') params.append('status', statusFilter);
      params.append('sort_by', sortBy);
      params.append('sort_order', sortOrder);
      
      if (!isAdmin && !isBDCManager) {
        params.append('owner_filter', 'mine');
      }

      const response = await axios.get(`${API}/clients?${params.toString()}`);
      setCustomers(response.data);
      setTotalCount(response.data.length);
    } catch (error) {
      console.error('Failed to fetch customers:', error);
    } finally {
      setLoading(false);
    }
  }, [searchTerm, statusFilter, sortBy, sortOrder, isAdmin, isBDCManager]);

  useEffect(() => {
    fetchCustomers();
  }, [fetchCustomers]);

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  };

  const getDocuments = async (clientId) => {
    try {
      const [idRes, incomeRes] = await Promise.all([
        axios.get(`${API}/clients/${clientId}/documents/list/id`),
        axios.get(`${API}/clients/${clientId}/documents/list/income`)
      ]);
      setDocuments({ id: idRes.data, income: incomeRes.data });
      setDocClient(clientId);
    } catch (error) {
      console.error('Failed to fetch documents:', error);
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
      getDocuments(clientId);
    } catch (error) {
      toast.error('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteDoc = async (clientId, type, docId) => {
    if (!window.confirm('Delete this document?')) return;
    try {
      await axios.delete(`${API}/clients/${clientId}/documents/${type}/${docId}`);
      toast.success('Document deleted');
      getDocuments(clientId);
    } catch (error) {
      toast.error('Failed to delete');
    }
  };

  const handleViewDocs = (client) => {
    setSelectedCustomer(client);
    getDocuments(client.id);
  };

  if (loading) {
    return (
      <div className="space-y-6" data-testid="customers-page">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground">{t('customers.title')}</h1>
            <p className="text-muted-foreground mt-1">
              {totalCount} {totalCount === 1 ? 'customer' : 'customers'}
            </p>
          </div>
        </div>
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input placeholder={t('customers.search')} disabled className="pl-10" />
              </div>
            </div>
          </CardContent>
        </Card>
        {viewMode === 'table' ? (
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-b border-border">
                      {[...Array(9)].map((_, i) => (
                        <TableHead key={i} className="w-24 h-12">
                          <div className="loading-spinner" style={{width: '60%', height: '4px', borderWidth: '2px'}} />
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {[...Array(5)].map((_, i) => (
                      <TableRow key={i}>
                        {[...Array(9)].map((_, j) => (
                          <TableCell key={j} className="h-12">
                            <div className="loading-spinner" style={{width: '80%', height: '4px', borderWidth: '2px'}} />
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <Card key={i} className="p-4">
                <div className="loading-spinner" style={{width: '60%', height: '16px', borderWidth: '2px'}} />
                <div className="loading-spinner" style={{width: '100%', height: '12px', borderWidth: '2px', marginTop: '8px', borderRadius: '4px'}} />
                <div className="loading-spinner" style={{width: '80%', height: '12px', borderWidth: '2px', marginTop: '4px', borderRadius: '4px'}} />
              </Card>
            ))}
          </div>
        )}
      </div>
    );
  }

  const formatDate = (dateStr) => dateStr ? new Date(dateStr).toLocaleDateString() : '-';

  const getStageBadge = (stage) => {
    const stageColors = {
      'NEW LEAD': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      'CONTACTED': 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
      'ENGAGED': 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
      'PREQUALIFY': 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      'APPLIED': 'bg-violet-500/20 text-violet-400 border-violet-500/30',
      'APPROVED': 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
      'CONDITIONAL': 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      'DECLINED': 'bg-rose-500/20 text-rose-400 border-rose-500/30',
      'APPOINTMENT': 'bg-orange-500/20 text-orange-400 border-orange-500/30',
      'SHOW': 'bg-sky-500/20 text-sky-400 border-sky-500/30',
      'NEGOTIATING': 'bg-fuchsia-500/20 text-fuchsia-400 border-fuchsia-500/30',
      'PENDING DEAL': 'bg-teal-500/20 text-teal-400 border-teal-500/30',
      'STOP/HOLD': 'bg-slate-500/20 text-slate-400 border-slate-500/30',
      'SOLD': 'bg-green-500/20 text-green-400 border-green-500/30',
      'LOST': 'bg-red-500/20 text-red-400 border-red-500/30',
    };
    return (
      <Badge className={`text-xs ${stageColors[stage] || 'bg-muted text-muted-foreground'}`}>
        {stage}
      </Badge>
    );
  };

  return (
    <div className="space-y-6" data-testid="customers-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('customers.title')}</h1>
          <p className="text-muted-foreground mt-1">
            {totalCount} {totalCount === 1 ? 'customer' : 'customers'}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <div className="hidden sm:flex border-border bg-muted rounded-lg p-1" role="group" aria-label="View mode">
            <Button
              variant={viewMode === 'table' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('table')}
              aria-pressed={viewMode === 'table'}
              aria-label="Table view"
            >
              <LayoutList className="w-4 h-4 mr-2" />
              Table
            </Button>
            <Button
              variant={viewMode === 'card' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('card')}
              aria-pressed={viewMode === 'card'}
              aria-label="Card view"
            >
              <LayoutGrid className="w-4 h-4 mr-2" />
              Cards
            </Button>
          </div>
        </div>
      </div>

      {/* Search */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder={t('customers.search')}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Customer List */}
      {viewMode === 'table' ? (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-b border-border bg-muted/50">
                    <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('name')}>
                      Name <span className={sortBy === 'name' ? (sortOrder === 'asc' ? ' ↑' : ' ↓') : ''} />
                    </TableHead>
                    <TableHead>Phone</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('last_contact')}>
                      {t('customers.lastContact')} <span className={sortBy === 'last_contact' ? (sortOrder === 'asc' ? ' ↑' : ' ↓') : ''} />
                    </TableHead>
                    <TableHead>Stage</TableHead>
                    <TableHead>Vehicle Interest</TableHead>
                    <TableHead>Documents</TableHead>
                    <TableHead>Assigned</TableHead>
                    <TableHead className="text-right w-24">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {customers.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center py-12 text-muted-foreground">
                        {t('customers.noCustomers')}
                      </TableCell>
                    </TableRow>
                  ) : (
                    customers.map((customer) => (
                      <TableRow key={customer.id} className="hover:bg-muted/50 border-b border-border/50">
                        <TableCell className="font-medium">
                          {customer.first_name} {customer.last_name}
                        </TableCell>
                        <TableCell className="font-mono">{customer.phone}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{customer.email || '-'}</TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {formatDate(customer.last_contact)}
                        </TableCell>
                        <TableCell>{getStageBadge(customer.commercial_stage || 'NEW LEAD')}</TableCell>
                        <TableCell className="text-sm max-w-xs truncate">{customer.vehicle_interest || '-'}</TableCell>
                        <TableCell>
                          <div className="flex items-center gap-1">
                            {customer.id_uploaded ? (
                              <CheckCircle className="w-4 h-4 text-emerald-500" title="ID Uploaded" />
                            ) : (
                              <AlertCircle className="w-4 h-4 text-amber-500" title="ID Missing" />
                            )}
                            {customer.income_proof_uploaded ? (
                              <CheckCircle className="w-4 h-4 text-emerald-500" title="Income Proof Uploaded" />
                            ) : (
                              <AlertCircle className="w-4 h-4 text-amber-500" title="Income Proof Missing" />
                            )}
                          </div>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">{customer.assigned_salesperson_name || customer.assigned_salesperson || '-'}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Button variant="ghost" size="sm" onClick={() => handleViewDocs(customer)} aria-label="Documents">
                              <FileText className="w-4 h-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => navigate(`/clients/${customer.id}`)} aria-label="View">
                              <Eye className="w-4 h-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {customers.map((customer) => (
            <Card key={customer.id} className="hover:shadow-lg transition-shadow cursor-pointer" onClick={() => navigate(`/clients/${customer.id}`)}>
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-foreground">{customer.first_name} {customer.last_name}</h3>
                    <p className="text-sm text-muted-foreground font-mono">{customer.phone}</p>
                    <p className="text-sm text-muted-foreground truncate">{customer.email || 'No email'}</p>
                  </div>
                  {getStageBadge(customer.commercial_stage || 'NEW LEAD')}
                </div>
                <div className="mt-3 pt-3 border-t border-border space-y-1 text-sm">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <MapPin className="w-3.5 h-3.5" />
                    <span className="truncate">{customer.vehicle_interest || 'No vehicle interest'}</span>
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Calendar className="w-3.5 h-3.5" />
                    <span>Last: {formatDate(customer.last_contact)}</span>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    {customer.id_uploaded ? (
                      <span className="flex items-center gap-1 text-emerald-500 text-xs">
                        <CheckCircle className="w-3.5 h-3.5" /> ID
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-amber-500 text-xs">
                        <AlertCircle className="w-3.5 h-3.5" /> ID Missing
                      </span>
                    )}
                    {customer.income_proof_uploaded ? (
                      <span className="flex items-center gap-1 text-emerald-500 text-xs ml-2">
                        <CheckCircle className="w-3.5 h-3.5" /> Income
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-amber-500 text-xs ml-2">
                        <AlertCircle className="w-3.5 h-3.5" /> Income Missing
                      </span>
                    )}
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-2">
                  <Button variant="ghost" size="sm" className="flex-1" onClick={(e) => { e.stopPropagation(); handleViewDocs(customer); }}>
                    <FileText className="w-4 h-4 mr-1" /> Docs
                  </Button>
                  <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); navigate(`/clients/${customer.id}`); }}>
                    <ExternalLink className="w-4 h-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Documents Dialog */}
      <Dialog open={!!docClient} onOpenChange={(open) => { if (!open) { setDocClient(null); setDocuments({ id: [], income: [] }); } }}>
        <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>{selectedCustomer ? `${selectedCustomer.first_name} ${selectedCustomer.last_name}` : ''} - Documents</span>
              <Button variant="ghost" size="sm" onClick={() => { setDocClient(null); setDocuments({ id: [], income: [] }); }}>
                <Download className="w-4 h-4 mr-1" />
                Download All
              </Button>
            </DialogTitle>
          </DialogHeader>
          <div className="p-4 space-y-6">
            {['id', 'income'].map((type) => (
              <div key={type}>
                <h4 className="font-medium mb-3 flex items-center gap-2">
                  {type === 'id' ? 'ID Documents' : 'Income Proof'}
                  <span className="text-sm text-muted-foreground">({documents[type]?.length || 0})</span>
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {documents[type]?.map((doc) => (
                    <div key={doc.id} className="p-3 border border-border rounded-lg flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <FileText className="w-6 h-6 text-muted-foreground" />
                        <div>
                          <p className="font-medium text-sm truncate max-w-[200px]">{doc.original_name || doc.filename}</p>
                          <p className="text-xs text-muted-foreground">
                            {doc.uploaded_at ? new Date(doc.uploaded_at).toLocaleDateString() : ''}
                            {doc.size && ` • ${(doc.size / 1024).toFixed(1)} KB`}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        <Button variant="ghost" size="sm" onClick={() => window.open(doc.url, '_blank')}>
                          <ExternalLink className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleDeleteDoc(docClient, type, doc.id)} className="text-destructive">
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                  {(!documents[type] || documents[type].length === 0) && (
                    <div className="col-span-2 border-2 border-dashed border-border/50 rounded-lg p-6 text-center">
                      <Upload className="w-8 h-8 mx-auto text-muted-foreground mb-2" />
                      <p className="text-muted-foreground mb-3">No {type === 'id' ? 'ID documents' : 'income proof'} uploaded</p>
                      <label className="cursor-pointer">
                        <input type="file" accept=".pdf,.jpg,.jpeg,.png" className="sr-only" onChange={(e) => e.target.files[0] && handleUpload(docClient, type, e.target.files[0])} />
                        <Button variant="outline" disabled={uploading}>
                          <Upload className="w-4 h-4 mr-1" />
                          {uploading ? 'Uploading...' : `Upload ${type === 'id' ? 'ID' : 'Income Proof'}`}
                        </Button>
                      </label>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}