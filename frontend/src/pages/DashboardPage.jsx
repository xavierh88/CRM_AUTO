import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { 
  Users, Calendar, DollarSign, FileCheck, TrendingUp, 
  UserPlus, CarFront, Clock, Activity, Target, Users2, Filter
} from 'lucide-react';
import { 
  PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, 
  XAxis, YAxis, Tooltip, Legend, AreaChart, Area
} from 'recharts';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function DashboardPage() {
  const { t } = useTranslation();
  const { isAdmin } = useAuth();
  const [stats, setStats] = useState(null);
  const [performance, setPerformance] = useState([]);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('all');
  const [selectedMonth, setSelectedMonth] = useState('');
  const [availableMonths, setAvailableMonths] = useState([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (selectedMonth) {
        params.append('month', selectedMonth);
      } else {
        params.append('period', period);
      }
      
      const [statsRes, perfRes] = await Promise.all([
        axios.get(`${API}/dashboard/stats?${params.toString()}`),
        isAdmin ? axios.get(`${API}/dashboard/salesperson-performance`) : Promise.resolve({ data: [] })
      ]);
      setStats(statsRes.data);
      setPerformance(perfRes.data);
      if (statsRes.data.available_months) {
        setAvailableMonths(statsRes.data.available_months);
      }
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  }, [period, selectedMonth, isAdmin]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handlePeriodChange = (value) => {
    setPeriod(value);
    setSelectedMonth(''); // Clear specific month when changing period
  };

  const handleMonthChange = (value) => {
    setSelectedMonth(value);
    if (value) {
      setPeriod(''); // Clear period when selecting specific month
    }
  };

  const monthNames = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
  
  const formatMonthLabel = (monthStr) => {
    if (!monthStr) return '';
    const [year, month] = monthStr.split('-');
    return `${monthNames[parseInt(month) - 1]} ${year}`;
  };

  const getPeriodLabel = () => {
    if (selectedMonth) return formatMonthLabel(selectedMonth);
    switch (period) {
      case 'month': return 'Este Mes';
      case '6months': return 'Últimos 6 Meses';
      default: return 'Todo el Tiempo';
    }
  };

  if (loading && !stats) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  const statusColors = {
    agendado: '#10b981',
    sin_configurar: '#f97316',
    cambio_hora: '#3b82f6',
    tres_semanas: '#f43f5e',
    no_show: '#94a3b8',
    cumplido: '#f59e0b'
  };

  const appointmentData = stats ? Object.entries(stats.appointments).map(([key, value]) => ({
    name: t(`status.${key}`),
    value,
    color: statusColors[key]
  })).filter(item => item.value > 0) : [];

  const financeData = stats?.finance_breakdown ? [
    { name: 'Financiado', value: stats.finance_breakdown.financiado || 0, color: '#3b82f6' },
    { name: 'Lease', value: stats.finance_breakdown.lease || 0, color: '#10b981' }
  ].filter(item => item.value > 0) : [];

  const monthlySalesData = stats?.monthly_sales?.map(item => ({
    month: monthNames[parseInt(item.month.split('-')[1]) - 1] || item.month,
    ventas: item.sales
  })) || [];

  // Calculate conversion rate
  const totalClientsForRate = stats?.total_clients_all || stats?.total_clients || 0;
  const conversionRate = totalClientsForRate > 0 
    ? ((stats.sales / totalClientsForRate) * 100).toFixed(1) 
    : 0;

  // Calculate appointment completion rate
  const totalAppointments = Object.values(stats?.appointments || {}).reduce((a, b) => a + b, 0);
  const completionRate = totalAppointments > 0 
    ? ((stats.appointments.cumplido / totalAppointments) * 100).toFixed(1) 
    : 0;

  return (
    <div className="space-y-4 sm:space-y-6" data-testid="dashboard-page">
      {/* Header with Filters */}
      <div className="flex flex-col gap-3 sm:gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900">{t('dashboard.title')}</h1>
          <p className="text-slate-500 mt-1 text-sm sm:text-base">
            Mostrando: <span className="font-medium text-blue-600">{getPeriodLabel()}</span>
          </p>
        </div>
        
        {/* Period Filters */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <div className="flex items-center gap-2 text-sm text-slate-500">
            <Filter className="w-4 h-4" />
            <span>Filtrar:</span>
          </div>
          
          <Select value={period} onValueChange={handlePeriodChange}>
            <SelectTrigger className="w-32 sm:w-40">
              <SelectValue placeholder="Período" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Todo el Tiempo</SelectItem>
              <SelectItem value="6months">Últimos 6 Meses</SelectItem>
              <SelectItem value="month">Este Mes</SelectItem>
            </SelectContent>
          </Select>
          
          <Select value={selectedMonth || "none"} onValueChange={(v) => handleMonthChange(v === "none" ? "" : v)}>
            <SelectTrigger className="w-28 sm:w-36">
              <SelectValue placeholder="Mes específico" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="none">-- Ninguno --</SelectItem>
              {availableMonths.map((m) => (
                <SelectItem key={m} value={m}>{formatMonthLabel(m)}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Loading overlay - only show briefly */}
      {loading && stats && (
        <div className="fixed inset-0 bg-white/50 flex items-center justify-center z-50">
          <div className="loading-spinner"></div>
        </div>
      )}

      {/* Main Stat Cards - Row 1 */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 sm:gap-4">
        <Card className="dashboard-card">
          <CardContent className="p-3 sm:p-4">
            <div className="flex flex-col items-center text-center sm:flex-row sm:text-left gap-2 sm:gap-3">
              <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center flex-shrink-0">
                <Users className="w-5 h-5 text-blue-600" />
              </div>
              <div className="min-w-0">
                <p className="text-xl sm:text-2xl font-bold text-slate-900">{stats?.total_clients || 0}</p>
                <p className="text-xs text-slate-500">Clientes Total</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="dashboard-card">
          <CardContent className="p-3 sm:p-4">
            <div className="flex flex-col items-center text-center sm:flex-row sm:text-left gap-2 sm:gap-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-50 flex items-center justify-center flex-shrink-0">
                <UserPlus className="w-5 h-5 text-emerald-600" />
              </div>
              <div className="min-w-0">
                <p className="text-xl sm:text-2xl font-bold text-slate-900">{stats?.new_clients_month || 0}</p>
                <p className="text-xs text-slate-500">Nuevos (Mes)</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="dashboard-card">
          <CardContent className="p-3 sm:p-4">
            <div className="flex flex-col items-center text-center sm:flex-row sm:text-left gap-2 sm:gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-50 flex items-center justify-center flex-shrink-0">
                <DollarSign className="w-5 h-5 text-amber-600" />
              </div>
              <div className="min-w-0">
                <p className="text-xl sm:text-2xl font-bold text-slate-900">{stats?.sales || 0}</p>
                <p className="text-xs text-slate-500">Ventas Total</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="dashboard-card">
          <CardContent className="p-3 sm:p-4">
            <div className="flex flex-col items-center text-center sm:flex-row sm:text-left gap-2 sm:gap-3">
              <div className="w-10 h-10 rounded-lg bg-purple-50 flex items-center justify-center flex-shrink-0">
                <CarFront className="w-5 h-5 text-purple-600" />
              </div>
              <div className="min-w-0">
                <p className="text-xl sm:text-2xl font-bold text-slate-900">{stats?.sales_month || 0}</p>
                <p className="text-xs text-slate-500">Ventas (Mes)</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="dashboard-card">
          <CardContent className="p-3 sm:p-4">
            <div className="flex flex-col items-center text-center sm:flex-row sm:text-left gap-2 sm:gap-3">
              <div className="w-10 h-10 rounded-lg bg-rose-50 flex items-center justify-center flex-shrink-0">
                <Calendar className="w-5 h-5 text-rose-600" />
              </div>
              <div className="min-w-0">
                <p className="text-xl sm:text-2xl font-bold text-slate-900">{stats?.today_appointments || 0}</p>
                <p className="text-xs text-slate-500">Citas Hoy</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="dashboard-card">
          <CardContent className="p-3 sm:p-4">
            <div className="flex flex-col items-center text-center sm:flex-row sm:text-left gap-2 sm:gap-3">
              <div className="w-10 h-10 rounded-lg bg-cyan-50 flex items-center justify-center flex-shrink-0">
                <Clock className="w-5 h-5 text-cyan-600" />
              </div>
              <div className="min-w-0">
                <p className="text-xl sm:text-2xl font-bold text-slate-900">{stats?.week_appointments || 0}</p>
                <p className="text-xs text-slate-500">Citas Semana</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* KPI Cards - Row 2 */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <Card className="dashboard-card bg-gradient-to-br from-blue-500 to-blue-600 text-white">
          <CardContent className="p-3 sm:p-4">
            <div className="flex flex-col items-center text-center sm:flex-row sm:items-center sm:justify-between sm:text-left">
              <div className="min-w-0">
                <p className="text-blue-100 text-xs sm:text-sm">Conversión</p>
                <p className="text-2xl sm:text-3xl font-bold mt-1">{conversionRate}%</p>
              </div>
              <Target className="w-8 h-8 text-blue-200 mt-2 sm:mt-0 flex-shrink-0" />
            </div>
          </CardContent>
        </Card>

        <Card className="dashboard-card bg-gradient-to-br from-emerald-500 to-emerald-600 text-white">
          <CardContent className="p-3 sm:p-4">
            <div className="flex flex-col items-center text-center sm:flex-row sm:items-center sm:justify-between sm:text-left">
              <div className="min-w-0">
                <p className="text-emerald-100 text-xs sm:text-sm">Citas OK</p>
                <p className="text-2xl sm:text-3xl font-bold mt-1">{completionRate}%</p>
              </div>
              <Activity className="w-8 h-8 text-emerald-200 mt-2 sm:mt-0 flex-shrink-0" />
            </div>
          </CardContent>
        </Card>

        <Card className="dashboard-card bg-gradient-to-br from-purple-500 to-purple-600 text-white">
          <CardContent className="p-3 sm:p-4">
            <div className="flex flex-col items-center text-center sm:flex-row sm:items-center sm:justify-between sm:text-left">
              <div className="min-w-0">
                <p className="text-purple-100 text-xs sm:text-sm">Records</p>
                <p className="text-2xl sm:text-3xl font-bold mt-1">{stats?.total_records || 0}</p>
              </div>
              <FileCheck className="w-8 h-8 text-purple-200 mt-2 sm:mt-0 flex-shrink-0" />
            </div>
          </CardContent>
        </Card>

        <Card className="dashboard-card bg-gradient-to-br from-amber-500 to-amber-600 text-white">
          <CardContent className="p-3 sm:p-4">
            <div className="flex flex-col items-center text-center sm:flex-row sm:items-center sm:justify-between sm:text-left">
              <div className="min-w-0">
                <p className="text-amber-100 text-xs sm:text-sm">Co-Signers</p>
                <p className="text-2xl sm:text-3xl font-bold mt-1">{stats?.total_cosigners || 0}</p>
              </div>
              <Users2 className="w-8 h-8 text-amber-200 mt-2 sm:mt-0 flex-shrink-0" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Monthly Sales Trend */}
        <Card className="dashboard-card lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-semibold flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-blue-600" />
              Tendencia de Ventas (Últimos 6 Meses)
            </CardTitle>
          </CardHeader>
          <CardContent>
            {monthlySalesData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <AreaChart data={monthlySalesData}>
                  <defs>
                    <linearGradient id="colorVentas" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="month" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Area 
                    type="monotone" 
                    dataKey="ventas" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    fillOpacity={1} 
                    fill="url(#colorVentas)" 
                  />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-64 flex items-center justify-center text-slate-400">
                Sin datos de ventas aún
              </div>
            )}
          </CardContent>
        </Card>

        {/* Finance Type Breakdown */}
        <Card className="dashboard-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-semibold">Tipo de Financiamiento</CardTitle>
          </CardHeader>
          <CardContent>
            {financeData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={financeData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value}`}
                  >
                    {financeData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-64 flex items-center justify-center text-slate-400">
                Sin ventas en este período
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Second Row Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Appointments by Status */}
        <Card className="dashboard-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-semibold">{t('dashboard.appointmentsByStatus')}</CardTitle>
          </CardHeader>
          <CardContent>
            {appointmentData.length > 0 ? (
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={appointmentData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={90}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {appointmentData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend verticalAlign="bottom" height={36} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-64 flex items-center justify-center text-slate-400">
                Sin citas en este período
              </div>
            )}
          </CardContent>
        </Card>

        {/* Performance Chart (Admin only) */}
        {isAdmin && (
          <Card className="dashboard-card">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg font-semibold flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-blue-600" />
                {t('dashboard.performance')} por Vendedor
              </CardTitle>
            </CardHeader>
            <CardContent>
              {performance.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <BarChart data={performance} layout="vertical">
                    <XAxis type="number" tick={{ fontSize: 11 }} />
                    <YAxis dataKey="salesperson_name" type="category" tick={{ fontSize: 11 }} width={100} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="total_records" name="Records" fill="#3b82f6" radius={[0, 4, 4, 0]} />
                    <Bar dataKey="sales" name="Ventas" fill="#10b981" radius={[0, 4, 4, 0]} />
                    <Bar dataKey="completed_appointments" name="Citas OK" fill="#f59e0b" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-64 flex items-center justify-center text-slate-400">
                  {t('common.noData')}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Status Legend for non-admin */}
        {!isAdmin && (
          <Card className="dashboard-card">
            <CardHeader className="pb-2">
              <CardTitle className="text-lg font-semibold">Leyenda de Estados</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                {Object.entries(statusColors).map(([status, color]) => (
                  <div key={status} className="flex items-center gap-3">
                    <div className="w-4 h-4 rounded-full" style={{ backgroundColor: color }}></div>
                    <span className="text-sm text-slate-600">{t(`status.${status}`)}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Document Status */}
      <Card className="dashboard-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-semibold">{t('clients.documents')} - Estado General</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            <div className="flex items-center gap-4 p-4 bg-emerald-50 rounded-xl">
              <div className="w-14 h-14 rounded-xl bg-emerald-100 flex items-center justify-center">
                <FileCheck className="w-7 h-7 text-emerald-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-emerald-700">{stats?.documents?.complete || 0}</p>
                <p className="text-sm text-emerald-600">Documentos Completos</p>
              </div>
            </div>
            <div className="flex items-center gap-4 p-4 bg-orange-50 rounded-xl">
              <div className="w-14 h-14 rounded-xl bg-orange-100 flex items-center justify-center">
                <FileCheck className="w-7 h-7 text-orange-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-orange-700">{stats?.documents?.pending || 0}</p>
                <p className="text-sm text-orange-600">Documentos Pendientes</p>
              </div>
            </div>
            <div className="flex items-center gap-4 p-4 bg-blue-50 rounded-xl">
              <div className="w-14 h-14 rounded-xl bg-blue-100 flex items-center justify-center">
                <Activity className="w-7 h-7 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-blue-700">{stats?.active_clients || 0}</p>
                <p className="text-sm text-blue-600">Clientes Activos (7 días)</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
