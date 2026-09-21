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
  Plus, Search, Filter, Users, UserPlus, Phone, Mail, MapPin,
  ChevronDown, ChevronUp, Edit, Trash2, Eye, MoreHorizontal,
  AlertTriangle, CheckCircle, XCircle, Calendar, DollarSign,
  Activity, ArrowRight, ExternalLink
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const LEAD_STAGES = [
  'NEW LEAD', 'CONTACTED', 'ENGAGED', 'PREQUALIFY', 'APPLIED',
  'APPROVED', 'CONDITIONAL', 'DECLINED', 'APPOINTMENT', 'SHOW',
  'NEGOTIATING', 'PENDING DEAL', 'STOP/HOLD', 'SOLD', 'LOST'
];

const LEAD_SOURCES = [
  'Website', 'Walk-in', 'Phone', 'Referral', 'Social Media',
  'Email Campaign', 'Third Party', 'Previous Customer', 'Other'
];

export default function LeadsPage() {
  const { t } = useTranslation();
  const { user, isAdmin, isBDCManager } = useAuth();
  const navigate = useNavigate();
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [stageFilter, setStageFilter] = useState('all');
  const [sourceFilter, setSourceFilter] = useState('all');
  const [salespersonFilter, setSalespersonFilter] = useState('all');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [selectedLead, setSelectedLead] = useState(null);
  const [salespersons, setSalespersons] = useState([]);
  const [totalCount, setTotalCount] = useState(0);

  // Form state
  const [formData, setFormData] = useState({
    first_name: '', last_name: '', phone: '', email: '', address: '',
    source: 'Website', stage: 'NEW LEAD', vehicle_interest: '',
    assigned_to: '', notes: '', follow_up_date: '', follow_up_notes: ''
  });
  const [formErrors, setFormErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const fetchLeads = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ exclude_sold: 'false' });
      if (searchTerm) params.append('search', searchTerm);
      if (stageFilter !== 'all') params.append('stage', stageFilter);
      if (sourceFilter !== 'all') params.append('source', sourceFilter);
      if (salespersonFilter !== 'all') params.append('salesperson_id', salespersonFilter);
      params.append('sort_by', sortBy);
      params.append('sort_order', sortOrder);
      
      if (!isAdmin && !isBDCManager) {
        params.append('owner_filter', 'mine');
      }

      const response = await axios.get(`${API}/clients?${params.toString()}`);
      setLeads(response.data);
      setTotalCount(response.data.length);
    } catch (error) {
      console.error('Failed to fetch leads:', error);
    } finally {
      setLoading(false);
    }
  }, [searchTerm, stageFilter, sourceFilter, salespersonFilter, sortBy, sortOrder, isAdmin, isBDCManager]);

  const fetchSalespersons = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/salespersons`);
      setSalespersons(response.data);
    } catch (error) {
      console.error('Failed to fetch salespersons:', error);
    }
  }, []);

  useEffect(() => {
    fetchLeads();
    fetchSalespersons();
  }, [fetchLeads, fetchSalespersons]);

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  };

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

  const getSourceBadge = (source) => {
    return (
      <Badge variant="outline" className="text-xs">
        {source}
      </Badge>
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setFormErrors({});
    
    const errors = {};
    if (!formData.first_name) errors.first_name = 'First name is required';
    if (!formData.last_name) errors.last_name = 'Last name is required';
    if (!formData.phone) errors.phone = 'Phone is required';
    
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      setSubmitting(false);
      return;
    }

    try {
      const payload = {
        ...formData,
        commercial_stage: formData.stage,
        assigned_salesperson: formData.assigned_to
      };
      
      if (selectedLead) {
        await axios.put(`${API}/clients/${selectedLead.id}`, payload);
        toast.success('Lead updated');
      } else {
        await axios.post(`${API}/clients`, payload);
        toast.success('Lead created');
      }
      setShowAddDialog(false);
      resetForm();
      fetchLeads();
    } catch (error) {
      console.error('Failed to save lead:', error);
      toast.error(error.response?.data?.detail || 'Failed to save lead');
    } finally {
      setSubmitting(false);
    }
  };

  const resetForm = () => {
    setFormData({
      first_name: '', last_name: '', phone: '', email: '', address: '',
      source: 'Website', stage: 'NEW LEAD', vehicle_interest: '',
      assigned_to: '', notes: '', follow_up_date: '', follow_up_notes: ''
    });
    setSelectedLead(null);
    setFormErrors({});
  };

  const handleEdit = (lead) => {
    setSelectedLead(lead);
    setFormData({
      first_name: lead.first_name, last_name: lead.last_name, phone: lead.phone, email: lead.email || '', address: lead.address || '',
      source: lead.source || 'Website', stage: lead.commercial_stage || 'NEW LEAD', vehicle_interest: lead.vehicle_interest || '',
      assigned_to: lead.assigned_salesperson || '', notes: lead.notes || '', follow_up_date: lead.follow_up_date || '', follow_up_notes: lead.follow_up_notes || ''
    });
    setShowAddDialog(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this lead?')) return;
    try {
      await axios.delete(`${API}/clients/${id}`);
      toast.success('Lead moved to trash');
      fetchLeads();
    } catch (error) {
      toast.error('Failed to delete lead');
    }
  };

  const handleNavigate = (lead) => {
    navigate(`/clients/${lead.id}`);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="leads-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('leads.title')}</h1>
          <p className="text-muted-foreground mt-1">
            {totalCount} {totalCount === 1 ? 'lead' : 'leads'} • Pipeline view
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => { resetForm(); setShowAddDialog(true); }}>
            <Plus className="w-4 h-4 mr-2" />
            {t('leads.addLead')}
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
                placeholder={t('leads.search')}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={stageFilter} onValueChange={setStageFilter}>
              <SelectTrigger className="w-full sm:w-44">
                <SelectValue placeholder={t('leads.stage')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('common.all') || 'All'}</SelectItem>
                {LEAD_STAGES.map(stage => (
                  <SelectItem key={stage} value={stage}>{stage}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={sourceFilter} onValueChange={setSourceFilter}>
              <SelectTrigger className="w-full sm:w-40">
                <SelectValue placeholder={t('leads.source')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('common.all') || 'All'}</SelectItem>
                {LEAD_SOURCES.map(src => (
                  <SelectItem key={src} value={src}>{src}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            {isAdmin && salespersons.length > 0 && (
              <Select value={salespersonFilter} onValueChange={setSalespersonFilter}>
                <SelectTrigger className="w-full sm:w-44">
                  <SelectValue placeholder={t('leads.salesperson')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('common.all') || 'All'}</SelectItem>
                  {salespersons.map(sp => (
                    <SelectItem key={sp.id} value={sp.id}>{sp.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Leads Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="border-b border-border">
                  <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('created_at')}>
                    Created <span className={sortBy === 'created_at' ? (sortOrder === 'asc' ? ' ↑' : ' ↓') : ''} />
                  </TableHead>
                  <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('name')}>
                    Name <span className={sortBy === 'name' ? (sortOrder === 'asc' ? ' ↑' : ' ↓') : ''} />
                  </TableHead>
                  <TableHead>Phone</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>{t('leads.source')}</TableHead>
                  <TableHead>{t('leads.stage')}</TableHead>
                  <TableHead>{t('leads.vehicleInterest')}</TableHead>
                  <TableHead>{t('leads.salesperson')}</TableHead>
                  <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('last_contact')}>
                    Last Contact <span className={sortBy === 'last_contact' ? (sortOrder === 'asc' ? ' ↑' : ' ↓') : ''} />
                  </TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {leads.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={10} className="text-center py-12 text-muted-foreground">
                      {t('leads.noLeads')}
                    </TableCell>
                  </TableRow>
                ) : (
                  leads.map((lead) => (
                    <TableRow key={lead.id} className="hover:bg-muted/50 cursor-pointer" onClick={() => handleNavigate(lead)}>
                      <TableCell className="text-sm text-muted-foreground">
                        {lead.created_at ? new Date(lead.created_at).toLocaleDateString() : '-'}
                      </TableCell>
                      <TableCell className="font-medium">
                        {lead.first_name} {lead.last_name}
                      </TableCell>
                      <TableCell className="font-mono">{lead.phone}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{lead.email || '-'}</TableCell>
                      <TableCell>{getSourceBadge(lead.source || 'Unknown')}</TableCell>
                      <TableCell>{getStageBadge(lead.commercial_stage || 'NEW LEAD')}</TableCell>
                      <TableCell className="text-sm max-w-xs truncate">{lead.vehicle_interest || '-'}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">{lead.assigned_salesperson_name || lead.assigned_salesperson || '-'}</TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {lead.last_contact ? new Date(lead.last_contact).toLocaleDateString() : '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); handleEdit(lead); }} aria-label="Edit">
                            <Edit className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); handleDelete(lead.id); }} aria-label="Delete" className="text-destructive hover:text-destructive">
                            <Trash2 className="w-4 h-4" />
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

      {/* Add/Edit Lead Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedLead ? 'Edit Lead' : t('leads.addLead')}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="p-4 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="first_name">First Name *</Label>
                <Input id="first_name" value={formData.first_name} onChange={(e) => setFormData({...formData, first_name: e.target.value})} error={formErrors.first_name} />
              </div>
              <div>
                <Label htmlFor="last_name">Last Name *</Label>
                <Input id="last_name" value={formData.last_name} onChange={(e) => setFormData({...formData, last_name: e.target.value})} error={formErrors.last_name} />
              </div>
              <div>
                <Label htmlFor="phone">Phone *</Label>
                <Input id="phone" type="tel" value={formData.phone} onChange={(e) => setFormData({...formData, phone: e.target.value})} error={formErrors.phone} />
              </div>
              <div>
                <Label htmlFor="email">Email</Label>
                <Input id="email" type="email" value={formData.email} onChange={(e) => setFormData({...formData, email: e.target.value})} />
              </div>
              <div className="sm:col-span-2">
                <Label htmlFor="address">Address</Label>
                <Input id="address" value={formData.address} onChange={(e) => setFormData({...formData, address: e.target.value})} />
              </div>
              <div>
                <Label htmlFor="source">Source</Label>
                <Select value={formData.source} onValueChange={(v) => setFormData({...formData, source: v})}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select source" />
                  </SelectTrigger>
                  <SelectContent>
                    {LEAD_SOURCES.map(src => (
                      <SelectItem key={src} value={src}>{src}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="stage">Stage</Label>
                <Select value={formData.stage} onValueChange={(v) => setFormData({...formData, stage: v})}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select stage" />
                  </SelectTrigger>
                  <SelectContent>
                    {LEAD_STAGES.map(stage => (
                      <SelectItem key={stage} value={stage}>{stage}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="vehicle_interest">Vehicle Interest</Label>
                <Input id="vehicle_interest" value={formData.vehicle_interest} onChange={(e) => setFormData({...formData, vehicle_interest: e.target.value})} placeholder="e.g., 2024 Honda Accord EX-L" />
              </div>
              {isAdmin && salespersons.length > 0 && (
                <div>
                  <Label htmlFor="assigned_to">Assigned To</Label>
                  <Select value={formData.assigned_to} onValueChange={(v) => setFormData({...formData, assigned_to: v})}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select salesperson" />
                    </SelectTrigger>
                    <SelectContent>
                      {salespersons.map(sp => (
                        <SelectItem key={sp.id} value={sp.id}>{sp.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              )}
            </div>
            <div>
              <Label htmlFor="notes">Notes</Label>
              <textarea id="notes" className="w-full min-h-[80px] p-3 border border-border rounded-lg bg-background text-foreground" value={formData.notes} onChange={(e) => setFormData({...formData, notes: e.target.value})} />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="follow_up_date">Follow-up Date</Label>
                <Input id="follow_up_date" type="date" value={formData.follow_up_date} onChange={(e) => setFormData({...formData, follow_up_date: e.target.value})} />
              </div>
              <div>
                <Label htmlFor="follow_up_notes">Follow-up Notes</Label>
                <Input id="follow_up_notes" value={formData.follow_up_notes} onChange={(e) => setFormData({...formData, follow_up_notes: e.target.value})} />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button type="button" variant="outline" onClick={() => { setShowAddDialog(false); resetForm(); }}>
                {t('common.cancel')}
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting ? 'Saving...' : t('common.save')}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}