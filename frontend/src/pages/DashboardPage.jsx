import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { ScrollArea } from '../components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import {
  Calendar, Clock, Users, UserPlus, MessageSquare, FileText,
  Target, AlertTriangle, Phone, Send, Plus, ExternalLink,
  Package, DollarSign, CheckCircle, AlertCircle,
  ChevronRight, RefreshCw
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function DashboardPage() {
  const { t } = useTranslation();
  const { user, isAdmin, isBDCManager } = useAuth();
  const navigate = useNavigate();
  const [actionItems, setActionItems] = useState({});
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('all');
  const [selectedMonth, setSelectedMonth] = useState('');
  const [availableMonths, setAvailableMonths] = useState([]);

  const fetchActionItems = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedMonth) {
        params.append('month', selectedMonth);
      } else {
        params.append('period', period);
      }
      
      if (isAdmin) {
        // Admin sees all
      } else if (isBDCManager) {
        // BDC manager sees all except admin
      } else {
        params.append('user_id', user.id);
      }

      const [statsRes, apptRes, leadsRes, docsRes, prequalRes, recordsRes, inventoryRes] = await Promise.all([
        axios.get(`${API}/dashboard/stats?${params.toString()}`),
        axios.get(`${API}/appointments/agenda`),
        axios.get(`${API}/clients?exclude_sold=false&sort_by=created_at`),
        axios.get(`${API}/clients?exclude_sold=false&sort_by=created_at`),
        axios.get(`${API}/prequalify/submissions`),
        axios.get(`${API}/user-records`),
        Promise.resolve({ data: [] }) // Inventory - no backend yet
      ]);

      const stats = statsRes.data;
      const appointments = apptRes.data;
      const allClients = leadsRes.data;
      const prequals = prequalRes.data;
      const records = recordsRes.data;

      const now = new Date();
      const todayStr = now.toISOString().split('T')[0];
      const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString();
      const fortyEightHoursAgo = new Date(now.getTime() - 48 * 60 * 60 * 1000).toISOString();

      // Today's appointments
      const todaysAppointments = appointments.filter(a => a.date === todayStr);
      
      // Appointments awaiting confirmation (sin_configurar)
      const awaitingConfirmation = appointments.filter(a => a.status === 'sin_configurar');
      
      // New leads (last 24h)
      const dayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();
      const newLeads = allClients.filter(c => c.created_at && c.created_at >= dayAgo);
      
      // Leads older than 48 hours without contact
      const leadsOver48h = allClients.filter(c => 
        c.created_at && c.created_at <= fortyEightHoursAgo && 
        (!c.last_contact || c.last_contact <= fortyEightHoursAgo)
      );
      
      // Stale leads (no contact in 7 days, not sold)
      const staleLeads = allClients.filter(c => 
        !c.is_sold && 
        c.last_contact && c.last_contact <= weekAgo &&
        c.commercial_stage && !['SOLD', 'LOST'].includes(c.commercial_stage)
      );
      
      // Unread conversations (from inbox)
      const unreadCount = stats.inbox_unread_count || 0;
      
      // Incomplete documents
      const incompleteDocs = stats.documents?.pending || 0;
      
      // Prequal status (pending)
      const pendingPrequals = prequals.filter(p => p.status === 'pending' || p.status === 'PENDING_EXTERNAL');
      
      // Near-close deals (PENDING DEAL, NEGOTIATING, APPROVED, CONDITIONAL)
      const nearCloseStages = ['PENDING DEAL', 'NEGOTIATING', 'APPROVED', 'CONDITIONAL'];
      const nearCloseDeals = allClients.filter(c => nearCloseStages.includes(c.commercial_stage));
      
      // Follow-ups due (comments with reminder_at <= now)
      // This would need a separate API call, using stats for now
      const followupsDue = stats.followups_due || 0;
      
      // Inventory attention (placeholder - no inventory backend)
      const inventoryAttention = 0;

      setActionItems({
        todaysAppointments: { count: todaysAppointments.length, items: todaysAppointments.slice(0, 5) },
        awaitingConfirmation: { count: awaitingConfirmation.length, items: awaitingConfirmation.slice(0, 5) },
        newLeads: { count: newLeads.length, items: newLeads.slice(0, 5) },
        leadsOver48h: { count: leadsOver48h.length, items: leadsOver48h.slice(0, 5) },
        staleLeads: { count: staleLeads.length, items: staleLeads.slice(0, 5) },
        unreadConversations: { count: unreadCount, items: [] },
        incompleteDocs: { count: incompleteDocs, items: [] },
        pendingPrequals: { count: pendingPrequals.length, items: pendingPrequals.slice(0, 5) },
        nearCloseDeals: { count: nearCloseDeals.length, items: nearCloseDeals.slice(0, 5) },
        followupsDue: { count: followupsDue, items: [] },
        inventoryAttention: { count: inventoryAttention, items: [] },
      });

      if (statsRes.data.available_months) {
        setAvailableMonths(statsRes.data.available_months);
      }
    } catch (error) {
      console.error('Failed to fetch action items:', error);
    } finally {
      setLoading(false);
    }
  }, [period, selectedMonth, user, isAdmin, isBDCManager]);

  useEffect(() => {
    fetchActionItems();
  }, [fetchActionItems]);

  const handlePeriodChange = (value) => {
    setPeriod(value);
    setSelectedMonth('');
  };

  const handleMonthChange = (value) => {
    setSelectedMonth(value === 'none' ? '' : value);
    if (value !== 'none') setPeriod('');
  };

  const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  
  const formatMonthLabel = (monthStr) => {
    if (!monthStr) return '';
    const [year, month] = monthStr.split('-');
    return `${monthNames[parseInt(month) - 1]} ${year}`;
  };

  const getPeriodLabel = () => {
    if (selectedMonth) return formatMonthLabel(selectedMonth);
    switch (period) {
      case 'month': return t('common.thisMonth') || 'This Month';
      case '6months': return t('common.last6Months') || 'Last 6 Months';
      default: return t('common.allTime') || 'All Time';
    }
  };

  const actionSections = [
    { key: 'todaysAppointments', label: t('dashboard.todayAppointments'), icon: Calendar, color: 'bg-blue-500', href: '/appointments?filter=today' },
    { key: 'awaitingConfirmation', label: t('dashboard.awaitingConfirmation'), icon: Clock, color: 'bg-orange-500', href: '/appointments?status=sin_configurar' },
    { key: 'newLeads', label: t('dashboard.newLeads'), icon: UserPlus, color: 'bg-emerald-500', href: '/leads?filter=new' },
    { key: 'leadsOver48h', label: t('dashboard.leadsOver48h'), icon: AlertTriangle, color: 'bg-amber-500', href: '/leads?filter=over48h' },
    { key: 'staleLeads', label: t('dashboard.staleLeads'), icon: Target, color: 'bg-rose-500', href: '/leads?filter=stale' },
    { key: 'unreadConversations', label: t('dashboard.unreadConversations'), icon: MessageSquare, color: 'bg-purple-500', href: '/conversations?filter=unread' },
    { key: 'incompleteDocs', label: t('dashboard.incompleteDocs'), icon: FileText, color: 'bg-slate-500', href: '/documents?filter=pending' },
    { key: 'pendingPrequals', label: t('dashboard.prequalStatus'), icon: CheckCircle, color: 'bg-indigo-500', href: '/prequalify' },
    { key: 'nearCloseDeals', label: t('dashboard.nearCloseDeals'), icon: DollarSign, color: 'bg-cyan-500', href: '/deals?filter=nearclose' },
    { key: 'followupsDue', label: t('dashboard.followupsDue'), icon: AlertCircle, color: 'bg-red-500', href: '/leads?filter=followups' },
    { key: 'inventoryAttention', label: t('dashboard.inventoryAttention'), icon: Package, color: 'bg-teal-500', href: '/inventory?filter=attention' },
  ];

  const quickActions = [
    { key: 'call', label: t('dashboard.call'), icon: Phone, onClick: () => navigate('/leads?action=call'), color: 'bg-green-500' },
    { key: 'sms', label: t('dashboard.sms'), icon: Send, onClick: () => navigate('/conversations?action=sms'), color: 'bg-blue-500' },
    { key: 'openLead', label: t('dashboard.openLead'), icon: ExternalLink, onClick: () => navigate('/leads'), color: 'bg-purple-500' },
    { key: 'confirmAppt', label: t('dashboard.confirmAppt'), icon: CheckCircle, onClick: () => navigate('/appointments?action=confirm'), color: 'bg-emerald-500' },
    { key: 'createAppt', label: t('dashboard.createAppt'), icon: Plus, onClick: () => navigate('/appointments?action=create'), color: 'bg-blue-500' },
    { key: 'addLead', label: t('dashboard.addLead'), icon: UserPlus, onClick: () => navigate('/leads?action=add'), color: 'bg-indigo-500' },
    { key: 'addVehicle', label: t('dashboard.addVehicle'), icon: Package, onClick: () => navigate('/inventory?action=add'), color: 'bg-teal-500', disabled: true, pending: true },
  ];

  if (loading && Object.keys(actionItems).length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner" />
      </div>
    );
  }

  const totalActions = Object.values(actionItems).reduce((sum, item) => sum + item.count, 0);

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      {/* Header with Period Filter */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('dashboard.title')}</h1>
          <p className="text-muted-foreground mt-1">
            {t('dashboard.subtitle')} · {getPeriodLabel()}
            {totalActions > 0 && <span className="ml-2 px-2 py-0.5 text-xs font-medium bg-primary/20 text-primary rounded-full">{totalActions} action items</span>}
          </p>
        </div>
        
        <div className="flex flex-wrap items-center gap-2">
          <Select value={period} onValueChange={handlePeriodChange}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Period" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('common.allTime') || 'All Time'}</SelectItem>
              <SelectItem value="6months">{t('common.last6Months') || 'Last 6 Months'}</SelectItem>
              <SelectItem value="month">{t('common.thisMonth') || 'This Month'}</SelectItem>
            </SelectContent>
          </Select>
          
          <Select value={selectedMonth || "none"} onValueChange={handleMonthChange}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="Month" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">-- {t('common.none') || 'None'} --</SelectItem>
              {availableMonths.map((m) => (
                <SelectItem key={m} value={m}>{formatMonthLabel(m)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
          
          <Button variant="outline" size="sm" onClick={fetchActionItems}>
            <RefreshCw className="w-4 h-4 mr-2" />
            {t('common.refresh') || 'Refresh'}
          </Button>
        </div>
      </div>

      {/* Action Center Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {actionSections.map((section) => {
          const data = actionItems[section.key];
          const count = data?.count || 0;
          const hasItems = count > 0;
          const borderColor = hasItems ? `hsl(var(--${section.color.replace('bg-', '').replace('-500', '')}))` : undefined;
          
          return (
            <Card 
              key={section.key} 
              className={`action-card transition-all duration-200 hover:shadow-lg ${hasItems ? 'border-l-4' : ''}`}
              style={{ borderLeftColor: borderColor }}
            >
              <CardContent className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <div className={`p-2 rounded-lg ${section.color} text-white`}>
                        <section.icon className="w-5 h-5" aria-hidden="true" />
                      </div>
                      <h3 className="font-semibold text-sm text-foreground truncate">{section.label}</h3>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <p className="text-3xl font-bold tabular-nums text-foreground">{count}</p>
                      {hasItems && (
                        <Badge variant="outline" className="text-xs">
                          {count} {count === 1 ? 'item' : 'items'}
                        </Badge>
                      )}
                    </div>
                    {hasItems && data.items.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-border">
                        <ScrollArea className="max-h-32" type="always">
                          <ul className="space-y-2" role="list">
                            {data.items.slice(0, 3).map((item, idx) => (
                              <li key={`${section.key}-${idx}`} className="text-xs text-muted-foreground truncate flex items-center gap-1">
                                {item.client_name || item.name || item.first_name + ' ' + item.last_name || 'Unknown'}
                                {item.date && <span className="text-slate-500">· {item.date}</span>}
                                {item.time && <span className="text-slate-500">· {item.time}</span>}
                              </li>
                            ))}
                            {data.items.length > 3 && (
                              <li className="text-xs text-primary font-medium">
                                +{data.items.length - 3} more
                              </li>
                            )}
                          </ul>
                        </ScrollArea>
                      </div>
                    )}
                  </div>
                  {hasItems && (
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="flex-shrink-0"
                      onClick={() => navigate(section.href)}
                      aria-label={`View ${section.label}`}
                    >
                      <ChevronRight className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-semibold text-foreground mb-4">{t('dashboard.quickActions')}</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3">
          {quickActions.map((action) => (
            <Button
              key={action.key}
              variant={action.disabled || action.pending ? 'outline' : 'default'}
              className={`h-24 flex flex-col gap-2 ${action.color} text-white hover:opacity-90 ${action.disabled || action.pending ? 'opacity-50 cursor-not-allowed' : ''}`}
              onClick={action.onClick}
              disabled={action.disabled || action.pending}
              aria-disabled={action.disabled || action.pending}
            >
              <div className="p-2 rounded-lg bg-white/10">
                <action.icon className="w-6 h-6" aria-hidden="true" />
              </div>
              <span className="font-medium text-sm">{action.label}</span>
              {action.pending && <Badge variant="secondary" className="text-xs mt-auto">{t('common.pending')}</Badge>}
            </Button>
          ))}
        </div>
      </div>

      {/* Empty State */}
      {totalActions === 0 && !loading && (
        <Card className="border-2 border-dashed border-border/50">
          <CardContent className="py-16 text-center">
            <CheckCircle className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">{t('dashboard.noActionItems')}</h3>
            <p className="text-muted-foreground">All caught up. Enjoy the calm.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

