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
  ExternalLink, ArrowRight, GripVertical, Trophy, History
} from 'lucide-react';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const DEAL_STAGES = [
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

  // No vendido workflow
  const [lostDialogOpen, setLostDialogOpen] = useState(false);
  const [pendingLostDeal, setPendingLostDeal] = useState(null);
  const [lostReason, setLostReason] = useState('');
  const [lostNote, setLostNote] = useState('');
  const [savingLost, setSavingLost] = useState(false);
  const [reactivatedDeal, setReactivatedDeal] = useState(null);
  const [reactivatedDialogOpen, setReactivatedDialogOpen] = useState(false);

  // SOLD requires explicit confirmation before persisting the sale.
  const [soldDialogOpen, setSoldDialogOpen] = useState(false);
  const [pendingSoldDeal, setPendingSoldDeal] = useState(null);
  const [savingSold, setSavingSold] = useState(false);

  // Deals workspace:
  // active pipeline, lost opportunities for recovery, and closed sales.
  const [dealSection, setDealSection] = useState('active');
  const [recentHistory, setRecentHistory] = useState({
    sold: [],
    lost: []
  });

  // Unified Deals history: paginated and loaded only when requested.
  const [dealHistory, setDealHistory] = useState({
    items: [],
    page: 1,
    page_size: 20,
    total: 0,
    pages: 0
  });
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historySearch, setHistorySearch] = useState('');
  const [historyEventType, setHistoryEventType] = useState('all');
  const [historyPeriod, setHistoryPeriod] = useState('all');

  const fetchRecentHistory = async () => {
    try {
      const response = await axios.get(`${API}/deals/recent-history`);
      setRecentHistory({
        sold: Array.isArray(response.data?.sold) ? response.data.sold : [],
        lost: Array.isArray(response.data?.lost) ? response.data.lost : []
      });
    } catch (error) {
      console.error('Failed to fetch recent deal history:', error);
      setRecentHistory({ sold: [], lost: [] });
    }
  };

  const fetchDealHistory = async (requestedPage = 1) => {
    setHistoryLoading(true);

    try {
      const params = new URLSearchParams({
        page: String(requestedPage),
        page_size: '20'
      });

      if (historyEventType !== 'all') {
        params.append('event_type', historyEventType);
      }

      if (historySearch.trim()) {
        params.append('search', historySearch.trim());
      }

      const now = new Date();

      if (historyPeriod === 'month') {
        const start = new Date(now.getFullYear(), now.getMonth(), 1);
        params.append('date_from', start.toISOString());
      } else if (historyPeriod === '3months') {
        const start = new Date(now);
        start.setMonth(start.getMonth() - 3);
        params.append('date_from', start.toISOString());
      } else if (historyPeriod === 'year') {
        const start = new Date(now.getFullYear(), 0, 1);
        params.append('date_from', start.toISOString());
      }

      const response = await axios.get(
        `${API}/deals/history?${params.toString()}`
      );

      setDealHistory({
        items: Array.isArray(response.data?.items) ? response.data.items : [],
        page: response.data?.page || 1,
        page_size: response.data?.page_size || 20,
        total: response.data?.total || 0,
        pages: response.data?.pages || 0
      });
    } catch (error) {
      console.error('Failed to fetch deal history:', error);
      setDealHistory({
        items: [],
        page: 1,
        page_size: 20,
        total: 0,
        pages: 0
      });
    } finally {
      setHistoryLoading(false);
    }
  };

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
      // Keep all commercial records available locally.
      // The workspace separates Active, Recovery and Sold visually
      // without making a closed sale look like it disappeared.
      const dealClients = response.data.filter(
        c => c.commercial_stage
      );
      setDeals(dealClients);

      // Pipeline value represents only real active opportunities.
      // Early lead stages remain in Leads. LOST and SOLD remain available
      // through Recovery, Sold and the commercial history.
      const activeStageIds = DEAL_STAGES
        .map(stage => stage.id)
        .filter(stageId => !['LOST', 'SOLD'].includes(stageId));

      const activeDealClients = dealClients.filter(
        c => activeStageIds.includes(String(c.commercial_stage).toUpperCase())
      );
      const value = activeDealClients.reduce(
        (sum, d) => sum + (d.vehicle_price || 0),
        0
      );
      setTotalValue(value);
    } catch (error) {
      console.error('Failed to fetch deals:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDeals();
    fetchRecentHistory();
  }, [searchTerm, stageFilter, isAdmin, isBDCManager]);

  useEffect(() => {
    if (dealSection === 'history') {
      fetchDealHistory(1);
    }
  }, [dealSection, historyEventType, historyPeriod]);

  const handleDragEnd = (result) => {
    if (!result.destination) return;
    
    const sourceStage = result.source.droppableId;
    const destStage = result.destination.droppableId;
    const sourceIndex = result.source.index;
    const destIndex = result.destination.index;

    if (sourceStage === destStage && sourceIndex === destIndex) return;

    const sourceDeals = deals.filter(d => d.commercial_stage === sourceStage);
    const item = sourceDeals[sourceIndex];

    if (!item || !item.id) {
      console.error('Deal drag failed: source deal not found', {
        sourceStage,
        sourceIndex,
        sourceDeals
      });
      return;
    }

    // A sale must be explicitly confirmed before changing backend truth.
    if (String(destStage).toUpperCase() === 'SOLD') {
      fetchDeals();
      setPendingSoldDeal(item);
      setSoldDialogOpen(true);
      return;
    }

    const newDeals = [...deals];
    
    // Update the item's stage
    const itemIndex = newDeals.findIndex(d => d.id === item.id);
    if (itemIndex !== -1) {
      newDeals[itemIndex] = { ...newDeals[itemIndex], commercial_stage: destStage };
      setDeals(newDeals);
      
      // LOST is confirmed through the Dealer AI responsive dialog.
      const normalizedDestStage = String(destStage || '').trim().toUpperCase();

      if (normalizedDestStage === 'LOST') {
        // Restore the optimistic move until the user explicitly confirms.
        fetchDeals();
        setPendingLostDeal(item);
        setLostReason('');
        setLostNote('');
        setLostDialogOpen(true);
        return;
      }

      axios.patch(`${API}/clients/${item.id}/commercial-stage`, {
        commercial_stage: destStage
      })
        .then((response) => {
          // Keep the UI synchronized with the persisted backend value.
          if (response?.data?.commercial_stage) {
            setDeals(current =>
              current.map(deal =>
                deal.id === item.id
                  ? { ...deal, commercial_stage: response.data.commercial_stage }
                  : deal
              )
            );
          }
        })
        .catch((error) => {
          console.error('Failed to update deal stage:', error);
          fetchDeals(); // Revert optimistic update from backend truth.
          toast.error('No se pudo guardar la etapa del Deal');
        });
    }
  };

  const confirmSoldDeal = async () => {
    if (savingSold) return;

    if (!pendingSoldDeal?.id) {
      toast.error('No se encontró el Deal');
      return;
    }

    setSavingSold(true);

    try {
      await axios.patch(
        `${API}/clients/${pendingSoldDeal.id}/commercial-stage`,
        { commercial_stage: 'SOLD' }
      );

      setSoldDialogOpen(false);
      setPendingSoldDeal(null);

      toast.success('Venta confirmada · Disponible en Vendidos 🏆');

      // SOLD leaves the active pipeline, but remains clearly accessible.
      setDealSection('sold');
      await Promise.all([
        fetchDeals(),
        fetchRecentHistory()
      ]);
    } catch (error) {
      console.error('Failed to confirm sale:', error);
      toast.error(
        error.response?.data?.detail ||
        'No se pudo confirmar la venta'
      );
    } finally {
      setSavingSold(false);
    }
  };

  const cancelSoldDeal = () => {
    if (savingSold) return;
    setSoldDialogOpen(false);
    setPendingSoldDeal(null);
    fetchDeals();
  };

  const confirmLostDeal = async () => {
    const reason = lostReason.trim();
    const note = lostNote.trim();

    if (!reason) {
      toast.error('Debes indicar el motivo de No vendido');
      return;
    }

    if (!pendingLostDeal?.id) {
      toast.error('No se encontró el Deal');
      return;
    }

    setSavingLost(true);

    try {
      const response = await axios.patch(
        `${API}/clients/${pendingLostDeal.id}/commercial-stage`,
        {
          commercial_stage: 'LOST',
          reason,
          ...(note ? { note } : {})
        }
      );

      setLostDialogOpen(false);
      setPendingLostDeal(null);
      setLostReason('');
      setLostNote('');

      toast.success('Deal marcado como No vendido');

      // LOST is not part of the active pipeline.
      // Refresh both Active Deals and Recovery immediately.
      await fetchDeals();
      await fetchRecentHistory();

      return response;
    } catch (error) {
      console.error('Failed to mark deal as lost:', error);
      toast.error(
        error.response?.data?.detail ||
        'No se pudo marcar el Deal como No vendido'
      );
    } finally {
      setSavingLost(false);
    }
  };

  const cancelLostDeal = () => {
    if (savingLost) return;
    setLostDialogOpen(false);
    setPendingLostDeal(null);
    setLostReason('');
    setLostNote('');
    fetchDeals();
  };

  const reactivateDeal = (item) => {
    const clientId = item?.client_id;

    if (!clientId) {
      toast.error('No se encontró el cliente');
      return;
    }

    // Solo abre confirmación. No modifica el Deal todavía.
    setReactivatedDeal({
      client_id: clientId,
      client: item?.client || null
    });
    setReactivatedDialogOpen(true);
  };

  const confirmReactivateDeal = async () => {
    const clientId = reactivatedDeal?.client_id;

    if (!clientId) {
      toast.error('No se encontró el cliente');
      return;
    }

    try {
      await axios.patch(
        `${API}/clients/${clientId}/commercial-stage`,
        {
          commercial_stage: 'CONTACTED',
          reason: 'deal_reactivated',
          note: 'Deal reactivado desde Recuperación.'
        }
      );

      await fetchDeals();
      await fetchRecentHistory();

      setReactivatedDialogOpen(false);
      setReactivatedDeal(null);

      navigate(`/clients?client_id=${clientId}`);
    } catch (error) {
      console.error('Failed to reactivate Deal:', error);
      toast.error(
        error.response?.data?.detail || 'No se pudo reactivar el Deal'
      );
    }
  };

  const getDealsByStage = (stageId) => {
    return deals.filter(d => d.commercial_stage === stageId);
  };

  if (loading) {
    return (
      <div className="deals-v2-page flex items-center justify-center h-64">
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
            Pipeline: ${totalValue.toLocaleString()} • {deals.filter(deal =>
              DEAL_STAGES
                .filter(stage => !['LOST', 'SOLD'].includes(stage.id))
                .some(stage => stage.id === String(deal.commercial_stage).toUpperCase())
            ).length} active deals
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

      {/* DEALS WORKSPACE NAVIGATION */}
      <div className="mb-4 grid grid-cols-3 gap-2 rounded-xl border border-slate-800 bg-slate-950/70 p-2">
        <Button
          type="button"
          variant={dealSection === 'active' ? 'default' : 'ghost'}
          onClick={() => setDealSection('active')}
          className="h-auto min-h-12 flex-col gap-0.5 px-2 py-2 sm:flex-row sm:gap-2"
        >
          <Activity className="h-4 w-4" />
          <span>Activos</span>
        </Button>

        <Button
          type="button"
          variant={dealSection === 'recovery' ? 'default' : 'ghost'}
          onClick={async () => {
            setDealSection('recovery');
            await fetchRecentHistory();
          }}
          className="h-auto min-h-12 flex-col gap-0.5 px-2 py-2 sm:flex-row sm:gap-2"
        >
          <AlertTriangle className="h-4 w-4" />
          <span>Recuperación</span>
        </Button>

        <Button
          type="button"
          variant={dealSection === 'sold' ? 'default' : 'ghost'}
          onClick={() => setDealSection('sold')}
          className="h-auto min-h-12 flex-col gap-0.5 px-2 py-2 sm:flex-row sm:gap-2"
        >
          <Trophy className="h-4 w-4" />
          <span>Vendidos</span>
        </Button>
      </div>

      {/* Kanban View */}
      {viewMode === 'kanban' && dealSection === 'active' && (
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

                                    {(deal.last_contact || deal.created_at) && (
                                      <p
                                        className="mt-2 text-xs text-muted-foreground"
                                        title={new Date(deal.last_contact || deal.created_at).toLocaleString()}
                                      >
                                        {deal.last_contact ? 'Último contacto' : 'Creado'} ·{' '}
                                        {new Date(deal.last_contact || deal.created_at).toLocaleString([], {
                                          month: 'short',
                                          day: 'numeric',
                                          hour: 'numeric',
                                          minute: '2-digit'
                                        })}
                                      </p>
                                    )}
                                  </div>
                                  <Button variant="ghost" size="sm" onClick={() => {
                                      if (!deal.id) return;
                                      navigate(`/clients?client_id=${deal.id}`, {
                                        state: {
                                          openClientId: deal.id,
                                          openClientTab: 'opportunities'
                                        }
                                      });
                                    }}
                                    disabled={!deal.id} aria-label="View">
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

      {/* RECOVERY / SOLD COMPACT VIEWS */}
      {viewMode === 'kanban' && ['recovery', 'sold'].includes(dealSection) && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={() => setDealSection('history')}
            >
              <History className="mr-2 h-4 w-4" />
              Historial de Deals
            </Button>
          </div>

          {dealSection === 'recovery' && (
            <Card className="border-border">
              <CardContent className="p-4 sm:p-6">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <div>
                    <h2 className="flex items-center gap-2 text-lg font-semibold">
                      <AlertTriangle className="h-5 w-5" />
                      No vendidos / Recuperación
                    </h2>
                    <p className="text-sm text-muted-foreground">
                      Últimos 5 clientes enviados a recuperación.
                    </p>
                  </div>
                  <Badge variant="outline">{recentHistory.lost.length}</Badge>
                </div>

                <div className="space-y-2">
                  {recentHistory.lost.length === 0 ? (
                    <div className="py-10 text-center text-sm text-muted-foreground">
                      No hay oportunidades recientes en recuperación.
                    </div>
                  ) : (
                    recentHistory.lost.map(item => {
                      const client = item.client || {};
                      return (
                        <div
                          key={item.event_id}
                          className="flex flex-col gap-3 rounded-xl border border-border p-4 sm:flex-row sm:items-center sm:justify-between"
                        >
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-semibold">
                                {[client.first_name, client.last_name].filter(Boolean).join(' ') || 'Cliente'}
                              </span>
                              <Badge variant="outline">No vendido</Badge>
                            </div>

                            <div className="mt-1 text-sm text-muted-foreground">
                              {client.vehicle_interest || client.vehicle || 'Vehículo no especificado'}
                            </div>

                            <div className="mt-2 text-xs text-muted-foreground">
                              {item.created_at
                                ? `No vendido: ${new Date(item.created_at).toLocaleString()}`
                                : 'Fecha no disponible'}
                            </div>

                            {item.reason && (
                              <div className="mt-1 text-sm">
                                <span className="font-medium">Motivo:</span> {item.reason}
                              </div>
                            )}

                            {item.note && (
                              <div className="mt-1 text-sm text-muted-foreground">
                                <span className="font-medium text-foreground">Descripción:</span>{' '}
                                {item.note}
                              </div>
                            )}
                          </div>

                          <Button
                            type="button"
                            size="sm"
                            onClick={() => reactivateDeal(item)}
                          >
                            Reactivar Deal
                          </Button>

                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => navigate(`/clients?client_id=${item.client_id}`)}
                          >
                            <ExternalLink className="mr-2 h-4 w-4" />
                            Ver cliente
                          </Button>
                        </div>
                      );
                    })
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {dealSection === 'sold' && (
            <Card className="border-border">
              <CardContent className="p-4 sm:p-6">
                <div className="mb-4 flex items-center justify-between gap-3">
                  <div>
                    <h2 className="flex items-center gap-2 text-lg font-semibold">
                      <Trophy className="h-5 w-5" />
                      Vendidos
                    </h2>
                    <p className="text-sm text-muted-foreground">
                      Últimas 5 ventas cerradas.
                    </p>
                  </div>
                  <Badge variant="outline">{recentHistory.sold.length}</Badge>
                </div>

                <div className="space-y-2">
                  {recentHistory.sold.length === 0 ? (
                    <div className="py-10 text-center text-sm text-muted-foreground">
                      Todavía no hay ventas recientes registradas.
                    </div>
                  ) : (
                    recentHistory.sold.map(item => {
                      const client = item.client || {};
                      return (
                        <div
                          key={item.event_id}
                          className="flex flex-col gap-3 rounded-xl border border-border p-4 sm:flex-row sm:items-center sm:justify-between"
                        >
                          <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                              <span className="font-semibold">
                                {[client.first_name, client.last_name].filter(Boolean).join(' ') || 'Cliente'}
                              </span>
                              <Badge className="gap-1">
                                <Trophy className="h-3 w-3" />
                                Vendido
                              </Badge>
                            </div>

                            <div className="mt-1 text-sm text-muted-foreground">
                              {client.vehicle_interest || client.vehicle || 'Vehículo no especificado'}
                            </div>

                            <div className="mt-2 text-xs text-muted-foreground">
                              {item.created_at
                                ? `Vendido: ${new Date(item.created_at).toLocaleString()}`
                                : 'Fecha no disponible'}
                            </div>

                            {item.actor_name && (
                              <div className="mt-1 text-sm">
                                <span className="font-medium">Vendedor:</span> {item.actor_name}
                              </div>
                            )}
                          </div>

                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => navigate(`/clients?client_id=${item.client_id}`)}
                          >
                            <ExternalLink className="mr-2 h-4 w-4" />
                            Ver cliente
                          </Button>
                        </div>
                      );
                    })
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* UNIFIED DEALS HISTORY */}
      {viewMode === 'kanban' && dealSection === 'history' && (
        <Card className="border-border">
          <CardContent className="p-4 sm:p-6">
            <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="flex items-center gap-2 text-xl font-semibold">
                  <History className="h-5 w-5" />
                  Historial de Deals
                </h2>
                <p className="text-sm text-muted-foreground">
                  Consulta el recorrido comercial sin saturar el pipeline.
                </p>
              </div>

              <Button
                type="button"
                variant="outline"
                onClick={() => setDealSection('active')}
              >
                <ArrowRight className="mr-2 h-4 w-4 rotate-180" />
                Volver a Deals
              </Button>
            </div>

            <div className="mb-5 grid gap-3 md:grid-cols-3">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={historySearch}
                  onChange={(e) => setHistorySearch(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') fetchDealHistory(1);
                  }}
                  placeholder="Buscar cliente, vehículo, vendedor..."
                  className="pl-9"
                />
              </div>

              <Select
                value={historyEventType}
                onValueChange={setHistoryEventType}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Estado / evento" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos los eventos</SelectItem>
                  <SelectItem value="sold">Vendidos</SelectItem>
                  <SelectItem value="not_sold">No vendidos</SelectItem>
                  <SelectItem value="sales_attempt">Intentos de venta</SelectItem>
                  <SelectItem value="salesperson_assigned">Asignaciones</SelectItem>
                  <SelectItem value="salesperson_reassigned">Reasignaciones</SelectItem>
                  <SelectItem value="reengaged">Reactivados</SelectItem>
                  <SelectItem value="lead_captured">Leads captados</SelectItem>
                  <SelectItem value="ai_followup">Seguimiento IA</SelectItem>
                </SelectContent>
              </Select>

              <Select
                value={historyPeriod}
                onValueChange={setHistoryPeriod}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Período" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todo el historial</SelectItem>
                  <SelectItem value="month">Este mes</SelectItem>
                  <SelectItem value="3months">Últimos 3 meses</SelectItem>
                  <SelectItem value="year">Este año</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="mb-4 flex items-center justify-between gap-3">
              <span className="text-sm text-muted-foreground">
                {dealHistory.total} movimientos encontrados
              </span>

              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fetchDealHistory(1)}
              >
                <Search className="mr-2 h-4 w-4" />
                Buscar
              </Button>
            </div>

            {historyLoading ? (
              <div className="py-12 text-center text-sm text-muted-foreground">
                Cargando historial...
              </div>
            ) : dealHistory.items.length === 0 ? (
              <div className="py-12 text-center text-sm text-muted-foreground">
                No se encontraron movimientos con estos filtros.
              </div>
            ) : (
              <div className="space-y-2">
                {dealHistory.items.map(item => {
                  const client = item.client || {};

                  const labels = {
                    sold: 'Vendido',
                    not_sold: 'No vendido',
                    sales_attempt: 'Intento de venta',
                    salesperson_assigned: 'Vendedor asignado',
                    salesperson_reassigned: 'Vendedor reasignado',
                    reengaged: 'Reactivado',
                    lead_captured: 'Lead captado',
                    ai_followup: 'Seguimiento IA'
                  };

                  return (
                    <div
                      key={item.event_id}
                      className="rounded-xl border border-border p-4"
                    >
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="font-semibold">
                              {[client.first_name, client.last_name]
                                .filter(Boolean)
                                .join(' ') || 'Cliente'}
                            </span>

                            <Badge variant={item.event_type === 'sold' ? 'default' : 'outline'}>
                              {labels[item.event_type] || item.event_type}
                            </Badge>
                          </div>

                          <div className="mt-1 text-sm text-muted-foreground">
                            {client.vehicle_interest ||
                              client.vehicle ||
                              'Vehículo no especificado'}
                          </div>

                          <div className="mt-2 text-xs text-muted-foreground">
                            {item.created_at
                              ? new Date(item.created_at).toLocaleString()
                              : 'Fecha no disponible'}
                          </div>

                          {item.actor_name && (
                            <div className="mt-1 text-sm">
                              <span className="font-medium">Responsable:</span>{' '}
                              {item.actor_name}
                            </div>
                          )}

                          {item.reason && (
                            <div className="mt-1 text-sm">
                              <span className="font-medium">Motivo:</span>{' '}
                              {item.reason}
                            </div>
                          )}

                          {item.note && (
                            <div className="mt-1 text-sm text-muted-foreground">
                              {item.note}
                            </div>
                          )}
                        </div>

                        {item.client_id && (
                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() =>
                              navigate(`/clients?client_id=${item.client_id}`)
                            }
                          >
                            <ExternalLink className="mr-2 h-4 w-4" />
                            Ver cliente
                          </Button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {dealHistory.pages > 1 && (
              <div className="mt-5 flex items-center justify-center gap-3">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={dealHistory.page <= 1 || historyLoading}
                  onClick={() => fetchDealHistory(dealHistory.page - 1)}
                >
                  Anterior
                </Button>

                <span className="text-sm text-muted-foreground">
                  Página {dealHistory.page} de {dealHistory.pages}
                </span>

                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  disabled={
                    dealHistory.page >= dealHistory.pages || historyLoading
                  }
                  onClick={() => fetchDealHistory(dealHistory.page + 1)}
                >
                  Siguiente
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
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
                          <Button variant="ghost" size="sm" onClick={() => {
                                      if (!deal.id) return;
                                      navigate(`/clients?client_id=${deal.id}`, {
                                        state: {
                                          openClientId: deal.id,
                                          openClientTab: 'opportunities'
                                        }
                                      });
                                    }}
                                    disabled={!deal.id}>
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

      <Dialog
        open={soldDialogOpen}
        onOpenChange={(open) => {
          if (savingSold) return;
          if (!open) {
            cancelSoldDeal();
          } else {
            setSoldDialogOpen(true);
          }
        }}
      >
        <DialogContent className="w-[calc(100vw-2rem)] max-w-lg max-h-[90vh] overflow-y-auto border-slate-700 bg-slate-950 text-slate-100">
          <DialogHeader>
            <div className="flex flex-col items-center text-center sm:items-start sm:text-left">
              <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-full border border-emerald-500/40 bg-emerald-500/10 shadow-lg shadow-emerald-950/30">
                <Trophy className="h-7 w-7 text-emerald-400" />
              </div>

              <DialogTitle className="text-xl font-semibold text-white">
                Confirmar venta
              </DialogTitle>

              <p className="mt-1 text-sm text-slate-400">
                Verifica la información antes de registrar esta venta.
              </p>
            </div>
          </DialogHeader>

          <div className="mt-2 rounded-lg border border-emerald-800/60 bg-emerald-950/20 p-4">
            <p className="text-sm text-slate-200">
              Esta acción registrará la oportunidad como vendida y agregará
              la venta al historial comercial. Confirma que la venta realmente
              se realizó.
            </p>
          </div>

          {pendingSoldDeal && (
            <div className="mt-4 rounded-lg border border-slate-800 bg-slate-900/70 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Cliente
              </p>

              <p className="mt-1 font-semibold text-white">
                {[pendingSoldDeal.first_name, pendingSoldDeal.last_name]
                  .filter(Boolean)
                  .join(' ') || pendingSoldDeal.name || 'Cliente'}
              </p>

              {pendingSoldDeal.vehicle_interest && (
                <p className="mt-2 text-sm text-slate-400">
                  Vehículo: {pendingSoldDeal.vehicle_interest}
                </p>
              )}

              {pendingSoldDeal.assigned_salesperson_name && (
                <p className="mt-1 text-sm text-slate-400">
                  Vendedor: {pendingSoldDeal.assigned_salesperson_name}
                </p>
              )}
            </div>
          )}

          <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={cancelSoldDeal}
              disabled={savingSold}
              className="w-full sm:w-auto"
            >
              Cancelar
            </Button>

            <Button
              type="button"
              onClick={confirmSoldDeal}
              disabled={savingSold}
              className="w-full sm:w-auto bg-emerald-600 hover:bg-emerald-500 text-white"
            >
              {savingSold ? 'Confirmando...' : 'Confirmar venta'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Reactivated Deal Dialog */}
      {/* Reactivate Deal Confirmation */}
      <Dialog
        open={reactivatedDialogOpen}
        onOpenChange={(open) => {
          setReactivatedDialogOpen(open);

          if (!open) {
            setReactivatedDeal(null);
          }
        }}
      >
        <DialogContent className="w-[calc(100vw-2rem)] max-w-lg rounded-2xl border border-slate-800 bg-slate-950 p-0 text-slate-100 shadow-2xl sm:w-full">
          <div className="p-5 sm:p-6">
            <DialogHeader className="text-left">
              <DialogTitle className="text-xl font-semibold text-slate-100">
                Reactivar este Deal
              </DialogTitle>

              <p className="mt-2 text-sm leading-6 text-slate-400">
                ¿Deseas reactivar este cliente y devolverlo al seguimiento comercial?
              </p>
            </DialogHeader>

            <div className="mt-5 rounded-xl border border-slate-800 bg-slate-900/70 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                Cliente
              </p>

              <p className="mt-1 font-medium text-slate-100">
                {reactivatedDeal?.client
                  ? [reactivatedDeal.client.first_name, reactivatedDeal.client.last_name]
                      .filter(Boolean)
                      .join(' ') || 'Cliente'
                  : 'Cliente'}
              </p>

              <p className="mt-3 text-sm leading-6 text-slate-400">
                El registro de No vendido permanecerá en el historial.
                Si cancelas, no se realizará ningún cambio.
              </p>
            </div>

            <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
              <Button
                type="button"
                variant="outline"
                className="w-full sm:w-auto"
                onClick={() => {
                  setReactivatedDialogOpen(false);
                  setReactivatedDeal(null);
                }}
              >
                Cancelar
              </Button>

              <Button
                type="button"
                className="w-full sm:w-auto"
                onClick={confirmReactivateDeal}
              >
                Reactivar e ir al cliente
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog
        open={lostDialogOpen}
        onOpenChange={(open) => {
          if (!open) cancelLostDeal();
        }}
      >
        <DialogContent className="w-[calc(100vw-2rem)] max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-800 bg-slate-950 p-0 text-slate-100 shadow-2xl sm:w-full">
          <div className="p-5 sm:p-6">
            <DialogHeader className="text-left">
              <div className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl border border-red-500/30 bg-red-500/10">
                <XCircle className="h-5 w-5 text-red-400" />
              </div>

              <DialogTitle className="text-xl font-semibold text-slate-100">
                Marcar como No vendido
              </DialogTitle>

              <p className="mt-2 text-sm leading-6 text-slate-400">
                Registra por qué no se concretó esta venta. El cliente se
                conservará en el CRM y podrá recuperarse o reasignarse después.
              </p>
            </DialogHeader>

            {pendingLostDeal && (
              <div className="mt-5 rounded-xl border border-slate-800 bg-slate-900/70 p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                  Cliente
                </p>
                <p className="mt-1 font-medium text-slate-100">
                  {[pendingLostDeal.first_name, pendingLostDeal.last_name]
                    .filter(Boolean)
                    .join(' ') || pendingLostDeal.name || 'Cliente'}
                </p>

                {pendingLostDeal.assigned_salesperson_name && (
                  <p className="mt-1 text-sm text-slate-400">
                    Vendedor: {pendingLostDeal.assigned_salesperson_name}
                  </p>
                )}
              </div>
            )}

            <div className="mt-5 space-y-5">
              <div className="space-y-2">
                <Label
                  htmlFor="lost-reason"
                  className="text-sm font-medium text-slate-200"
                >
                  Motivo <span className="text-red-400">*</span>
                </Label>

                <Input
                  id="lost-reason"
                  value={lostReason}
                  onChange={(e) => setLostReason(e.target.value)}
                  placeholder="Ej. No encontró el vehículo que buscaba"
                  autoComplete="off"
                  className="h-11 border-slate-700 bg-slate-900 text-slate-100 placeholder:text-slate-500"
                  disabled={savingLost}
                />
              </div>

              <div className="space-y-2">
                <Label
                  htmlFor="lost-note"
                  className="text-sm font-medium text-slate-200"
                >
                  Notas adicionales
                  <span className="ml-2 font-normal text-slate-500">
                    Opcional
                  </span>
                </Label>

                <textarea
                  id="lost-note"
                  value={lostNote}
                  onChange={(e) => setLostNote(e.target.value)}
                  placeholder="Agrega contexto útil para un futuro seguimiento..."
                  rows={4}
                  disabled={savingLost}
                  className="w-full resize-none rounded-md border border-slate-700 bg-slate-900 px-3 py-3 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-slate-500 focus:ring-1 focus:ring-slate-500 disabled:opacity-50"
                />
              </div>
            </div>

            <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
              <Button
                type="button"
                variant="outline"
                onClick={cancelLostDeal}
                disabled={savingLost}
                className="w-full border-slate-700 sm:w-auto"
              >
                Cancelar
              </Button>

              <Button
                type="button"
                onClick={confirmLostDeal}
                disabled={savingLost || !lostReason.trim()}
                className="w-full bg-red-600 text-white hover:bg-red-500 sm:w-auto"
              >
                {savingLost ? 'Guardando...' : 'Confirmar No vendido'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}