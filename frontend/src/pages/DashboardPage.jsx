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
import { Skeleton } from '../components/ui/skeleton';
import { Separator } from '../components/ui/separator';
import {
  Calendar, Clock, Users, UserPlus, MessageSquare, FileText,
  Target, AlertTriangle, Phone, Send, Plus, ExternalLink,
  Package, DollarSign, CheckCircle, AlertCircle,
  ChevronRight, RefreshCw, Filter, Bell, Sparkles
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function DashboardPage() {
  const { t } = useTranslation();
  const { user, isAdmin, isBDCManager, isDemo } = useAuth();
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
      } else if (isBDCManager) {
      } else {
        params.append('user_id', user.id);
      }

      const [statsRes, apptRes, leadsRes, docsRes, prequalRes, recordsRes] = await Promise.all([
        axios.get(`${API}/dashboard/stats?${params.toString()}`),
        axios.get(`${API}/appointments/agenda`),
        axios.get(`${API}/clients?exclude_sold=false&sort_by=created_at`),
        axios.get(`${API}/clients?exclude_sold=false&sort_by=created_at`),
        axios.get(`${API}/prequalify/submissions`),
        axios.get(`${API}/user-records`),
      ]);

      const stats = statsRes.data;
      const appointments = apptRes.data;
      const allClients = leadsRes.data;
      const prequals = prequalRes.data;

      const now = new Date();
      const todayStr = now.toISOString().split('T')[0];
      const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000).toISOString();
      const fortyEightHoursAgo = new Date(now.getTime() - 48 * 60 * 60 * 1000).toISOString();

      const todaysAppointments = appointments.filter(a => a.date === todayStr);
      const awaitingConfirmation = appointments.filter(a => a.status === 'sin_configurar');
      
      const dayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000).toISOString();
      const newLeads = allClients.filter(c => c.created_at && c.created_at >= dayAgo);
      
      const leadsOver48h = allClients.filter(c => 
        c.created_at && c.created_at <= fortyEightHoursAgo && 
        (!c.last_contact || c.last_contact <= fortyEightHoursAgo)
      );
      
      const staleLeads = allClients.filter(c => 
        !c.is_sold && 
        c.last_contact && c.last_contact <= weekAgo &&
        c.commercial_stage && !['SOLD', 'LOST'].includes(c.commercial_stage)
      );
      
      const unreadCount = stats.inbox_unread_count || 0;
      const incompleteDocs = stats.documents?.pending || 0;
      const pendingPrequals = prequals.filter(p => p.status === 'pending' || p.status === 'PENDING_EXTERNAL');
      
      const nearCloseStages = ['PENDING DEAL', 'NEGOTIATING', 'APPROVED', 'CONDITIONAL'];
      const nearCloseDeals = allClients.filter(c => nearCloseStages.includes(c.commercial_stage));
      
      const followupsDue = stats.followups_due || 0;
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
    { key: 'todaysAppointments', label: t('dashboard.todayAppointments') || "Today's Appointments", icon: Calendar, color: 'blue', href: '/appointments?filter=today' },
    { key: 'awaitingConfirmation', label: t('dashboard.awaitingConfirmation') || 'Awaiting Confirmation', icon: Clock, color: 'orange', href: '/appointments?status=sin_configurar' },
    { key: 'newLeads', label: t('dashboard.newLeads') || 'New Leads (24h)', icon: UserPlus, color: 'emerald', href: '/leads?filter=new' },
    { key: 'leadsOver48h', label: t('dashboard.leadsOver48h') || 'Leads > 48h', icon: AlertTriangle, color: 'amber', href: '/leads?filter=over48h' },
    { key: 'staleLeads', label: t('dashboard.staleLeads') || 'Stale Leads', icon: Target, color: 'rose', href: '/leads?filter=stale' },
    { key: 'unreadConversations', label: t('dashboard.unreadConversations') || 'Unread Conversations', icon: MessageSquare, color: 'purple', href: '/conversations?filter=unread' },
    { key: 'incompleteDocs', label: t('dashboard.incompleteDocs') || 'Incomplete Documents', icon: FileText, color: 'slate', href: '/documents?filter=pending' },
    { key: 'pendingPrequals', label: t('dashboard.prequalStatus') || 'Prequal Status', icon: CheckCircle, color: 'indigo', href: '/prequalify' },
    { key: 'nearCloseDeals', label: t('dashboard.nearCloseDeals') || 'Near-Close Deals', icon: DollarSign, color: 'cyan', href: '/deals?filter=nearclose' },
    { key: 'followupsDue', label: t('dashboard.followupsDue') || 'Follow-ups Due', icon: AlertCircle, color: 'red', href: '/leads?filter=followups' },
    { key: 'inventoryAttention', label: t('dashboard.inventoryAttention') || 'Inventory Attention', icon: Package, color: 'teal', href: '/inventory?filter=attention' },
  ];

  const quickActions = [
    { key: 'call', label: t('dashboard.call') || 'Call', icon: Phone, onClick: () => navigate('/leads?action=call'), color: 'green', bgColor: 'bg-green-500' },
    { key: 'sms', label: t('dashboard.sms') || 'SMS', icon: Send, onClick: () => navigate('/conversations?action=sms'), color: 'blue', bgColor: 'bg-blue-500' },
    { key: 'openLead', label: t('dashboard.openLead') || 'Open Lead', icon: ExternalLink, onClick: () => navigate('/leads'), color: 'purple', bgColor: 'bg-purple-500' },
    { key: 'confirmAppt', label: t('dashboard.confirmAppt') || 'Confirm Appt', icon: CheckCircle, onClick: () => navigate('/appointments?action=confirm'), color: 'emerald', bgColor: 'bg-emerald-500' },
    { key: 'createAppt', label: t('dashboard.createAppt') || 'Create Appt', icon: Plus, onClick: () => navigate('/appointments?action=create'), color: 'blue', bgColor: 'bg-blue-600' },
    { key: 'addLead', label: t('dashboard.addLead') || 'Add Lead', icon: UserPlus, onClick: () => navigate('/leads?action=add'), color: 'indigo', bgColor: 'bg-indigo-500' },
    { key: 'addVehicle', label: t('dashboard.addVehicle') || 'Add Vehicle', icon: Package, onClick: () => navigate('/inventory?action=add'), color: 'teal', bgColor: 'bg-teal-500', disabled: true, pending: true },
  ];

  const totalActions = Object.values(actionItems).reduce((sum, item) => sum + item.count, 0);

  const getColorClasses = (color) => {
    const colors = {
      blue: 'bg-blue-500',
      orange: 'bg-orange-500',
      emerald: 'bg-emerald-500',
      amber: 'bg-amber-500',
      rose: 'bg-rose-500',
      purple: 'bg-purple-500',
      slate: 'bg-slate-500',
      indigo: 'bg-indigo-500',
      cyan: 'bg-cyan-500',
      red: 'bg-red-500',
      teal: 'bg-teal-500',
    };
    return colors[color] || 'bg-primary';
  };

  const getBorderColor = (color) => {
    const colors = {
      blue: 'hsl(199 89% 48%)',
      orange: 'hsl(25 95% 53%)',
      emerald: 'hsl(142 76% 36%)',
      amber: 'hsl(45 93% 47%)',
      rose: 'hsl(346 87% 49%)',
      purple: 'hsl(262 83% 58%)',
      slate: 'hsl(140 8% 45%)',
      indigo: 'hsl(239 84% 67%)',
      cyan: 'hsl(189 85% 46%)',
      red: 'hsl(0 84% 60%)',
      teal: 'hsl(173 80% 40%)',
    };
    return colors[color] || 'hsl(var(--primary))';
  };

  if (loading && Object.keys(actionItems).length === 0) {
    return (
      <div className="space-y-6" data-testid="dashboard-page">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground">{t('dashboard.title') || 'Action Center'}</h1>
            <p className="text-muted-foreground mt-1">{t('dashboard.subtitle') || 'Your operational priorities for today'}</p>
          </div>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {[...Array(11)].map((_, i) => (
            <Card key={i} className="action-card-skeleton">
              <CardContent className="p-5">
                <Skeleton className="h-5 w-3/4 mb-3 rounded" />
                <Skeleton className="h-8 w-1/4 mb-2 rounded" />
                <Skeleton className="h-4 w-1/2 rounded" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3">
          {[...Array(7)].map((_, i) => (
            <Skeleton key={i} className="h-24 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      {/* Header with Period Filter */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('dashboard.title') || 'Action Center'}</h1>
          <p className="text-muted-foreground mt-1 flex items-center gap-2">
            {t('dashboard.subtitle') || 'Your operational priorities for today'}
            <span className="text-xs px-2 py-0.5 bg-muted rounded-full text-muted-foreground">{getPeriodLabel()}</span>
            {totalActions > 0 && (
              <span className="ml-1 px-2 py-0.5 text-xs font-medium bg-primary/20 text-primary rounded-full">
                {totalActions} {t('dashboard.actionItems') || 'action items'}
              </span>
            )}
            {isDemo && (
              <span className="ml-1 px-2 py-0.5 text-xs font-medium bg-amber-500/20 text-amber-500 rounded-full">
                {t('nav.demo') || 'DEMO'}
              </span>
            )}
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
          
          <Button variant="outline" size="sm" onClick={fetchActionItems} disabled={loading}>
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
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
          const borderColor = hasItems ? getBorderColor(section.color) : 'transparent';
          
          return (
            <Card 
              key={section.key} 
              className={`action-card transition-all duration-200 hover:shadow-xl ${hasItems ? 'border-l-4' : 'opacity-70'} relative overflow-hidden`}
              style={{ borderLeftColor: borderColor }}
            >
              {hasItems && (
                <div className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r" style={{ background: `linear-gradient(90deg, ${borderColor}, ${borderColor}80)` }} />
              )}
              <CardContent className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <div className={`p-2 rounded-lg ${getColorClasses(section.color)} text-white`}>
                        <section.icon className="w-5 h-5" aria-hidden="true" />
                      </div>
                      <h3 className="font-semibold text-sm text-foreground truncate">{section.label}</h3>
                    </div>
                    <div className="flex items-baseline gap-2">
                      <p className="text-3xl font-bold tabular-nums text-foreground">{count}</p>
                      {hasItems && (
                        <Badge variant="secondary" className="text-xs">
                          {count} {count === 1 ? 'item' : 'items'}
                        </Badge>
                      )}
                    </div>
                    {hasItems && data.items.length > 0 && (
                      <div className="mt-3 pt-3 border-t border-border/50">
                        <ScrollArea className="max-h-32" type="always">
                          <ul className="space-y-2" role="list">
                            {data.items.slice(0, 3).map((item, idx) => (
                              <li key={`${section.key}-${idx}`} className="text-xs text-muted-foreground truncate flex items-center gap-1">
                                {item.client_name || item.name || (item.first_name && item.last_name ? `${item.first_name} ${item.last_name}` : 'Unknown')}
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
                      className="flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity"
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
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-foreground">{t('dashboard.quickActions') || 'Quick Actions'}</h2>
          {isDemo && (
            <Badge variant="outline" className="text-xs text-amber-500 border-amber-500/30">
              <Sparkles className="w-3 h-3 mr-1" />
              {t('common.demoData') || 'Demo data'}
            </Badge>
          )}
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3">
          {quickActions.map((action) => (
            <Button
              key={action.key}
              variant={action.disabled || action.pending ? 'outline' : 'default'}
              className={`h-24 flex flex-col gap-2 ${action.bgColor} text-white hover:opacity-90 ${action.disabled || action.pending ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-lg'}`}
              onClick={action.onClick}
              disabled={action.disabled || action.pending}
              aria-disabled={action.disabled || action.pending}
            >
              <div className="p-2 rounded-lg bg-white/10">
                <action.icon className="w-6 h-6" aria-hidden="true" />
              </div>
              <span className="font-medium text-sm">{action.label}</span>
              {action.pending && (
                <Badge variant="secondary" className="text-xs mt-auto">
                  {t('common.pending') || 'Pending'}
                </Badge>
              )}
              {action.disabled && !action.pending && (
                <Badge variant="secondary" className="text-xs mt-auto">
                  {t('common.disabled') || 'Disabled'}
                </Badge>
              )}
            </Button>
          ))}
        </div>
      </div>

      {/* Empty State */}
      {totalActions === 0 && !loading && (
        <Card className="border-2 border-dashed border-border/50">
          <CardContent className="py-16 text-center">
            <div className="w-16 h-16 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-emerald-500" />
            </div>
            <h3 className="text-lg font-semibold mb-2">{t('dashboard.noActionItems') || 'No action items — you\'re all caught up!'}</h3>
            <p className="text-muted-foreground">Enjoy the calm. Check back later for new priorities.</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}