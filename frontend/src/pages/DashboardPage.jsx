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
  ChevronRight, RefreshCw, Filter, Bell, Sparkles,
  Activity, TrendingUp, TrendingDown, Minus
} from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const actionSections = [
  { key: 'todaysAppointments', label: 'dashboard.todayAppointments', defaultLabel: "Today's Appointments", icon: Calendar, color: 'primary', href: '/appointments?filter=today' },
  { key: 'awaitingConfirmation', label: 'dashboard.awaitingConfirmation', defaultLabel: 'Awaiting Confirmation', icon: Clock, color: 'warning', href: '/appointments?status=sin_configurar' },
  { key: 'newLeads', label: 'dashboard.newLeads', defaultLabel: 'New Leads (24h)', icon: UserPlus, color: 'success', href: '/leads?filter=new' },
  { key: 'leadsOver48h', label: 'dashboard.leadsOver48h', defaultLabel: 'Leads > 48h', icon: AlertTriangle, color: 'amber', href: '/leads?filter=over48h' },
  { key: 'staleLeads', label: 'dashboard.staleLeads', defaultLabel: 'Stale Leads', icon: Target, color: 'destructive', href: '/leads?filter=stale' },
  { key: 'unreadConversations', label: 'dashboard.unreadConversations', defaultLabel: 'Unread Conversations', icon: MessageSquare, color: 'purple', href: '/conversations?filter=unread' },
  { key: 'incompleteDocs', label: 'dashboard.incompleteDocs', defaultLabel: 'Incomplete Documents', icon: FileText, color: 'muted', href: '/documents?filter=pending' },
  { key: 'pendingPrequals', label: 'dashboard.prequalStatus', defaultLabel: 'Prequal Status', icon: CheckCircle, color: 'indigo', href: '/prequalify' },
  { key: 'nearCloseDeals', label: 'dashboard.nearCloseDeals', defaultLabel: 'Near-Close Deals', icon: DollarSign, color: 'cyan', href: '/deals?filter=nearclose' },
  { key: 'followupsDue', label: 'dashboard.followupsDue', defaultLabel: 'Follow-ups Due', icon: AlertCircle, color: 'red', href: '/leads?filter=followups' },
  { key: 'inventoryAttention', label: 'dashboard.inventoryAttention', defaultLabel: 'Inventory Attention', icon: Package, color: 'teal', href: '/inventory?filter=attention' },
];

const colorClasses = {
  primary: 'bg-primary/10 text-primary border-primary/20',
  warning: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
  success: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
  amber: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
  destructive: 'bg-rose-500/10 text-rose-500 border-rose-500/20',
  purple: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
  muted: 'bg-slate-500/10 text-slate-500 border-slate-500/20',
  indigo: 'bg-indigo-500/10 text-indigo-500 border-indigo-500/20',
  cyan: 'bg-cyan-500/10 text-cyan-500 border-cyan-500/20',
  red: 'bg-red-500/10 text-red-500 border-red-500/20',
  teal: 'bg-teal-500/10 text-teal-500 border-teal-500/20',
};

const iconBgClasses = {
  primary: 'bg-primary/20 text-primary',
  warning: 'bg-amber-500/20 text-amber-500',
  success: 'bg-emerald-500/20 text-emerald-500',
  amber: 'bg-amber-500/20 text-amber-500',
  destructive: 'bg-rose-500/20 text-rose-500',
  purple: 'bg-purple-500/20 text-purple-500',
  muted: 'bg-slate-500/20 text-slate-500',
  indigo: 'bg-indigo-500/20 text-indigo-500',
  cyan: 'bg-cyan-500/20 text-cyan-500',
  red: 'bg-red-500/20 text-red-500',
  teal: 'bg-teal-500/20 text-teal-500',
};

const borderColorMap = {
  primary: 'hsl(var(--primary))',
  warning: 'hsl(45 93% 47%)',
  success: 'hsl(142 76% 36%)',
  amber: 'hsl(45 93% 47%)',
  destructive: 'hsl(346 87% 49%)',
  purple: 'hsl(262 83% 58%)',
  muted: 'hsl(140 8% 45%)',
  indigo: 'hsl(239 84% 67%)',
  cyan: 'hsl(189 85% 46%)',
  red: 'hsl(0 84% 60%)',
  teal: 'hsl(173 80% 40%)',
};

const quickActions = [
  { key: 'call', label: 'dashboard.call', defaultLabel: 'Call', icon: Phone, href: '/leads?action=call', color: 'success' },
  { key: 'sms', label: 'dashboard.sms', defaultLabel: 'SMS', icon: Send, href: '/conversations?action=sms', color: 'primary' },
  { key: 'openLead', label: 'dashboard.openLead', defaultLabel: 'Open Lead', icon: ExternalLink, href: '/leads', color: 'purple' },
  { key: 'confirmAppt', label: 'dashboard.confirmAppt', defaultLabel: 'Confirm Appt', icon: CheckCircle, href: '/appointments?action=confirm', color: 'success' },
  { key: 'createAppt', label: 'dashboard.createAppt', defaultLabel: 'Create Appt', icon: Plus, href: '/appointments?action=create', color: 'primary' },
  { key: 'addLead', label: 'dashboard.addLead', defaultLabel: 'Add Lead', icon: UserPlus, href: '/leads?action=add', color: 'indigo' },
  { key: 'addVehicle', label: 'dashboard.addVehicle', defaultLabel: 'Add Vehicle', icon: Package, href: '/inventory?action=add', color: 'teal', disabled: true, pending: true },
];

export default function DashboardPage() {
  const { t } = useTranslation();
  const { user, isAdmin, isBDCManager, isDemo } = useAuth();
  const navigate = useNavigate();
  const [actionItems, setActionItems] = useState({});
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('all');
  const [selectedMonth, setSelectedMonth] = useState('');
  const [availableMonths, setAvailableMonths] = useState([]);
  const [recentActivity, setRecentActivity] = useState([]);
  const [activityLoading, setActivityLoading] = useState(true);

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

  const fetchRecentActivity = useCallback(async () => {
    setActivityLoading(true);
    try {
      const params = new URLSearchParams({ limit: '10' });
      if (!isAdmin && !isBDCManager) {
        params.append('user_id', user.id);
      }
      const response = await axios.get(`${API}/activity/recent?${params.toString()}`);
      setRecentActivity(response.data || []);
    } catch (error) {
      console.error('Failed to fetch recent activity:', error);
      setRecentActivity([]);
    } finally {
      setActivityLoading(false);
    }
  }, [user, isAdmin, isBDCManager]);

  useEffect(() => {
    fetchActionItems();
    fetchRecentActivity();
  }, [fetchActionItems, fetchRecentActivity]);

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

  const totalActions = Object.values(actionItems).reduce((sum, item) => sum + item.count, 0);

  const formatActivityTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const getActivityIcon = (type) => {
    switch (type) {
      case 'appointment_created': return { icon: Calendar, color: 'primary' };
      case 'appointment_updated': return { icon: Clock, color: 'warning' };
      case 'lead_created': return { icon: UserPlus, color: 'success' };
      case 'lead_updated': return { icon: Users, color: 'primary' };
      case 'message_received': return { icon: MessageSquare, color: 'purple' };
      case 'document_uploaded': return { icon: FileText, color: 'indigo' };
      case 'deal_updated': return { icon: DollarSign, color: 'cyan' };
      case 'vehicle_added': return { icon: Package, color: 'teal' };
      default: return { icon: Activity, color: 'muted' };
    }
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
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <Card>
              <CardContent className="p-6">
                <Skeleton className="h-6 w-1/4 mb-4 rounded" />
                <div className="space-y-4">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} className="h-16 rounded-lg" />
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
          <Card>
            <CardContent className="p-6">
              <Skeleton className="h-6 w-1/4 mb-4 rounded" />
              <div className="space-y-3">
                {[...Array(4)].map((_, i) => (
                  <Skeleton key={i} className="h-12 rounded-lg" />
                ))}
              </div>
            </CardContent>
          </Card>
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
          <p className="text-muted-foreground mt-1 flex items-center gap-2 flex-wrap">
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
          const borderColor = hasItems ? borderColorMap[section.color] : 'transparent';
          const iconBg = iconBgClasses[section.color] || iconBgClasses.muted;
          const badgeClass = colorClasses[section.color] || colorClasses.muted;
          
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
                      <div className={`p-2 rounded-lg ${iconBg}`}>
                        <section.icon className="w-5 h-5" aria-hidden="true" />
                      </div>
                      <h3 className="font-semibold text-sm text-foreground truncate">{t(section.label) || section.defaultLabel}</h3>
                    </div>
                    <div className="flex items-baseline gap-2 flex-wrap">
                      <p className="text-3xl font-bold tabular-nums text-foreground">{count}</p>
                      {hasItems && (
                        <Badge variant="secondary" className="text-xs">
                          {count} {count === 1 ? (t('common.item') || 'item') : (t('common.items') || 'items')}
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
                      aria-label={`View ${t(section.label) || section.defaultLabel}`}
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
          {quickActions.map((action) => {
            const iconBg = iconBgClasses[action.color] || iconBgClasses.muted;
            const isDisabled = action.disabled || action.pending;
            
            return (
              <Button
                key={action.key}
                variant={isDisabled ? 'outline' : 'default'}
                className={`h-24 flex flex-col gap-2 ${iconBg} hover:opacity-90 ${isDisabled ? 'opacity-50 cursor-not-allowed' : 'hover:shadow-lg'} text-foreground`}
                onClick={() => navigate(action.href)}
                disabled={isDisabled}
                aria-disabled={isDisabled}
              >
                <div className="p-2 rounded-lg bg-white/5">
                  <action.icon className="w-6 h-6" aria-hidden="true" />
                </div>
                <span className="font-medium text-sm">{t(action.label) || action.defaultLabel}</span>
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
            );
          })}
        </div>
      </div>

      {/* Recent Activity + Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Activity */}
        <div className="lg:col-span-2">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-foreground">{t('dashboard.recentActivity') || 'Recent Activity'}</h2>
                <Button variant="ghost" size="sm" onClick={() => navigate('/activity')}>
                  <ChevronRight className="w-4 h-4 mr-1" />
                  {t('common.viewAll') || 'View all'}
                </Button>
              </div>
              {activityLoading ? (
                <div className="space-y-4">
                  {[...Array(5)].map((_, i) => (
                    <Skeleton key={i} className="h-16 rounded-lg" />
                  ))}
                </div>
              ) : recentActivity.length > 0 ? (
                <div className="space-y-3">
                  {recentActivity.slice(0, 10).map((activity, idx) => {
                    const { icon, color } = getActivityIcon(activity.type);
                    const iconBg = iconBgClasses[color] || iconBgClasses.muted;
                    return (
                      <div key={idx} className="flex items-center gap-3 p-3 rounded-lg hover:bg-muted/50 transition-colors">
                        <div className={`p-2 rounded-lg ${iconBg} flex-shrink-0`}>
                          <icon className="w-4 h-4" aria-hidden="true" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-foreground truncate">{activity.description || 'Activity'}</p>
                          <p className="text-xs text-muted-foreground">{activity.user_name || 'System'} · {formatActivityTime(activity.created_at)}</p>
                        </div>
                        {activity.metadata?.deal_value && (
                          <span className="text-sm font-semibold text-emerald-500">
                            ${Number(activity.metadata.deal_value).toLocaleString()}
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Activity className="w-10 h-10 mx-auto mb-3 text-muted-foreground/30" />
                  <p>{t('dashboard.noRecentActivity') || 'No recent activity'}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Insights / KPI Summary */}
        <Card>
          <CardContent className="p-6">
            <h2 className="text-lg font-semibold text-foreground mb-4">{t('dashboard.insights') || 'Insights'}</h2>
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-primary/5 border border-primary/10">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 rounded-lg bg-primary/20 text-primary">
                    <TrendingUp className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="font-medium text-sm text-foreground">{t('dashboard.insightConversion') || 'Conversion trending up'}</p>
                    <p className="text-xs text-muted-foreground">{t('dashboard.insightConversionDesc') || 'Up 2.3% vs last month'}</p>
                  </div>
                </div>
              </div>
              <div className="p-4 rounded-lg bg-amber-500/5 border border-amber-500/10">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 rounded-lg bg-amber-500/20 text-amber-500">
                    <AlertTriangle className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="font-medium text-sm text-foreground">{t('dashboard.insightStale') || 'Stale leads increasing'}</p>
                    <p className="text-xs text-muted-foreground">{t('dashboard.insightStaleDesc') || '5 leads over 7 days without contact'}</p>
                  </div>
                </div>
              </div>
              <div className="p-4 rounded-lg bg-emerald-500/5 border border-emerald-500/10">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 rounded-lg bg-emerald-500/20 text-emerald-500">
                    <CheckCircle className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="font-medium text-sm text-foreground">{t('dashboard.insightAppointments') || 'Appointment confirmation rate high'}</p>
                    <p className="text-xs text-muted-foreground">{t('dashboard.insightAppointmentsDesc') || '92% confirmed this week'}</p>
                  </div>
                </div>
              </div>
              <div className="p-4 rounded-lg bg-cyan-500/5 border border-cyan-500/10">
                <div className="flex items-center gap-3 mb-2">
                  <div className="p-2 rounded-lg bg-cyan-500/20 text-cyan-500">
                    <DollarSign className="w-4 h-4" />
                  </div>
                  <div>
                    <p className="font-medium text-sm text-foreground">{t('dashboard.insightPipeline') || 'Pipeline value growing'}</p>
                    <p className="text-xs text-muted-foreground">{t('dashboard.insightPipelineDesc') || '$485K in near-close deals'}</p>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
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