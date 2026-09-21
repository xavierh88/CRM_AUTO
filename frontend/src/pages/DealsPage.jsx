import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { Input } from '../components/ui/input';
import { toast } from 'sonner';
import {
  Plus, Search, DollarSign, Users, TrendingUp, Target,
  ChevronDown, ChevronUp, Edit, Trash2, Eye, MoreHorizontal,
  AlertTriangle, CheckCircle, XCircle, Calendar, Activity,
  ExternalLink, ArrowRight, GripVertical
} from 'lucide-react';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DEAL_STAGES = [
  { id: 'NEW LEAD', label: 'New Lead', color: 'bg-blue-500' },
  { id: 'CONTACTED', label: 'Contacted', color: 'bg-cyan-500' },
  { id: 'ENGAGED', label: 'Engaged', color: 'bg-indigo-500' },
  { id: 'PREQUALIFY', label: 'Prequalify', color: 'bg-purple-500' },
  { id: 'APPLIED', label: 'Applied', color: 'bg-violet-500' },
  { id: 'APPROVED', label: 'Approved', color: 'bg-emerald-500' },
  { id: 'CONDITIONAL', label: 'Conditional', color: 'bg-amber-500' },
  { id: 'DECLINED', label: 'Declined', color: 'bg-rose-500' },
  { id: 'APPOINTMENT', label: 'Appointment', color: 'bg-orange-500' },
  { id: 'SHOW', label: 'Show', color: 'bg-sky-500' },
  { id: 'NEGOTIATING', label: 'Negotiating', color: 'bg-fuchsia-500' },
  { id: 'PENDING DEAL', label: 'Pending Deal', color: 'bg-teal-500' },
  { id: 'STOP/HOLD', label: 'Stop/Hold', color: 'bg-slate-500' },
  { id: 'SOLD', label: 'Sold', color: 'bg-green-500' },
  { id: 'LOST', label: 'Lost', color: 'bg-red-500' },
];

export default function DealsPage() {
  const { t } = useTranslation();
  const { user, isAdmin, isBDCManager } = useAuth();
  const navigate = useNavigate();
  const [deals, setDeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [stageFilter, setStageFilter] = useState('all');
  const [viewMode, setViewMode] = useState('kanban'); // 'kanban' or 'table'
  const [selectedDeal, setSelectedDeal] = useState(null);
  const [totalValue, setTotalValue] = useState(0);

  const fetchDeals = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ exclude_sold: 'false' });
      if (searchTerm) params.append('search', searchTerm);
      if (stageFilter !== 'all') params.append('stage', stageFilter);
      
      if (!isAdmin && !isBDCManager) {
        params.append('owner_filter', 'mine');
      }

      const response = await axios.get(`${API}/clients?${params.toString()}`);
      const dealClients = response.data.filter(c => c.commercial_stage && !['SOLD', 'LOST'].includes(c.commercial_stage));
      setDeals(dealClients);
      
      // Calculate total pipeline value
      const value = dealClients.reduce((sum, d) => sum + (d.vehicle_price || 0), 0);
      setTotalValue(value);
    } catch (error) {
      console.error('Failed to fetch deals:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeals();
  }, [searchTerm, stageFilter, isAdmin, isBDCManager]);

  const handleDragEnd = (result) => {
    if (!result.destination) return;
    
    const sourceStage = result.source.droppableId;
    const destStage = result.destination.droppableId;
    const sourceIndex = result.source.index;
    const destIndex = result.destination.index;

    if (sourceStage === destStage && sourceIndex === destIndex) return;

    const item = deals.find(d => d.commercial_stage === sourceStage)[sourceIndex];
    const newDeals = [...deals];
    
    // Update the item's stage
    const itemIndex = newDeals.findIndex(d => d.id === item.id);
    if (itemIndex !== -1) {
      newDeals[itemIndex] = { ...newDeals[itemIndex], commercial_stage: destStage };
      setDeals(newDeals);
      
      // Optimistically update backend
      axios.put(`${API}/clients/${item.id}`, { commercial_stage: destStage })
        .catch(() => {
          fetchDeals(); // Revert on error
          toast.error('Failed to update deal stage');
        });
    }
  };

  const getDealsByStage = (stageId) => {
    return deals.filter(d => d.commercial_stage === stageId);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner" />
      </div>
    );
  }

  const activeStages = DEAL_STAGES.filter(s => 
    getDealsByStage(s.id).length > 0 || stageFilter === 'all' || stageFilter === s.id
  );

  return (
    <div className="space-y-6" data-testid="deals-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('deals.title')}</h1>
          <p className="text-muted-foreground mt-1">
            Pipeline: ${totalValue.toLocaleString()} • {deals.length} active deals
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => setViewMode('kanban')} className={viewMode === 'kanban' ? 'bg-primary text-primary-foreground' : ''}>
            <Target className="w-4 h-4 mr-2" />
            Kanban
          </Button>
          <Button variant="outline" onClick={() => setViewMode('table')} className={viewMode === 'table' ? 'bg-primary text-primary-foreground' : ''}>
            <Activity className="w-4 h-4 mr-2" />
            Table
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
                placeholder={t('deals.search') || 'Search deals...'}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={stageFilter} onValueChange={setStageFilter}>
              <SelectTrigger className="w-full sm:w-44">
                <SelectValue placeholder={t('deals.stage')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('common.all') || 'All Stages'}</SelectItem>
                {DEAL_STAGES.map(stage => (
                  <SelectItem key={stage.id} value={stage.id}>{stage.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Kanban View */}
      {viewMode === 'kanban' && (
        <DragDropContext onDragEnd={handleDragEnd}>
          <div className="flex gap-4 overflow-x-auto pb-4" style={{ minWidth: '100%' }}>
            {activeStages.map((stage) => {
              const stageDeals = getDealsByStage(stage.id);
              return (
                <Droppable key={stage.id} droppableId={stage.id}>
                  {(provided, snapshot) => (
                    <div
                      ref={provided.innerRef}
                      {...provided.droppableProps}
                      className={`flex flex-col min-w-[300px] max-w-[340px] ${snapshot.isDraggingOver ? 'bg-primary/5' : ''}`}
                      style={{ borderRadius: '12px', background: snapshot.isDraggingOver ? 'hsl(var(--primary) / 0.05)' : 'hsl(var(--card))' }}
                    >
                      <div className="p-4 border-b border-border flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`w-3 h-3 rounded-full ${stage.color}`} />
                          <h3 className="font-semibold">{stage.label}</h3>
                          <Badge variant="outline" className="text-xs">{stageDeals.length}</Badge>
                        </div>
                        <span className="text-sm text-muted-foreground">
                          ${stageDeals.reduce((sum, d) => sum + (d.vehicle_price || 0), 0).toLocaleString()}
                        </span>
                      </div>
                      <div
                        className="flex-1 p-2 space-y-2 min-h-[200px]"
                        ref={provided.innerRef}
                        {...provided.droppableProps}
                      >
                        {stageDeals.map((deal, index) => (
                          <Draggable key={deal.id} draggableId={deal.id} index={index}>
                            {(provided, snapshot) => (
                              <div
                                ref={provided.innerRef}
                                {...provided.draggableProps}
                                {...provided.dragHandleProps}
                                className={`p-3 bg-background border border-border rounded-lg cursor-grab hover:shadow-md transition-shadow ${snapshot.isDragging ? 'shadow-lg ring-2 ring-primary' : ''}`}
                              >
                                <div className="flex items-start justify-between">
                                  <div className="flex-1 min-w-0">
                                    <p className="font-medium truncate">{deal.first_name} {deal.last_name}</p>
                                    <p className="text-sm text-muted-foreground truncate">{deal.vehicle_interest || 'No vehicle'}</p>
                                    <p className="text-sm font-semibold text-primary mt-1">${(deal.vehicle_price || 0).toLocaleString()}</p>
                                  </div>
                                  <Button variant="ghost" size="sm" onClick={() => navigate(`/clients/${deal.id}`)} aria-label="View">
                                    <ExternalLink className="w-4 h-4" />
                                  </Button>
                                </div>
                              </div>
                            )}
                          </Draggable>
                        ))}
                        {provided.placeholder}
                      </div>
                    </div>
                  )}
                </Droppable>
              );
            })}
          </div>
        </DragDropContext>
      )}

      {/* Table View */}
      {viewMode === 'table' && (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-border">
                    <th className="p-4 text-left font-medium text-muted-foreground">Client</th>
                    <th className="p-4 text-left font-medium text-muted-foreground">Vehicle</th>
                    <th className="p-4 text-left font-medium text-muted-foreground">Stage</th>
                    <th className="p-4 text-left font-medium text-muted-foreground">Value</th>
                    <th className="p-4 text-left font-medium text-muted-foreground">Assigned</th>
                    <th className="p-4 text-left font-medium text-muted-foreground">Last Activity</th>
                    <th className="p-4 text-right font-medium text-muted-foreground">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {deals.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="p-12 text-center text-muted-foreground">
                        {t('deals.noDeals') || 'No deals in pipeline'}
                      </td>
                    </tr>
                  ) : (
                    deals.map((deal) => (
                      <tr key={deal.id} className="border-b border-border/50 hover:bg-muted/50">
                        <td className="p-4">
                          <p className="font-medium">{deal.first_name} {deal.last_name}</p>
                          <p className="text-sm text-muted-foreground font-mono">{deal.phone}</p>
                        </td>
                        <td className="p-4">{deal.vehicle_interest || '-'}</td>
                        <td className="p-4">
                          <Badge variant="outline" className="text-xs">
                            {deal.commercial_stage}
                          </Badge>
                        </td>
                        <td className="p-4 font-semibold">${(deal.vehicle_price || 0).toLocaleString()}</td>
                        <td className="p-4 text-sm text-muted-foreground">{deal.assigned_salesperson_name || '-'}</td>
                        <td className="p-4 text-sm text-muted-foreground">
                          {deal.last_contact ? new Date(deal.last_contact).toLocaleDateString() : '-'}
                        </td>
                        <td className="p-4 text-right">
                          <Button variant="ghost" size="sm" onClick={() => navigate(`/clients/${deal.id}`)}>
                            <ExternalLink className="w-4 h-4" />
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
      )}
    </div>
  );
}