import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Users, Calendar, DollarSign, FileCheck, TrendingUp } from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend } from 'recharts';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function DashboardPage() {
  const { t } = useTranslation();
  const { isAdmin } = useAuth();
  const [stats, setStats] = useState(null);
  const [performance, setPerformance] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [statsRes, perfRes] = await Promise.all([
        axios.get(`${API}/dashboard/stats`),
        isAdmin ? axios.get(`${API}/dashboard/salesperson-performance`) : Promise.resolve({ data: [] })
      ]);
      setStats(statsRes.data);
      setPerformance(perfRes.data);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
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

  const statCards = [
    {
      title: t('dashboard.totalClients'),
      value: stats?.total_clients || 0,
      icon: Users,
      color: 'text-blue-600',
      bg: 'bg-blue-50'
    },
    {
      title: t('dashboard.todayAppointments'),
      value: stats?.today_appointments || 0,
      icon: Calendar,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50'
    },
    {
      title: t('dashboard.sales'),
      value: stats?.sales || 0,
      icon: DollarSign,
      color: 'text-amber-600',
      bg: 'bg-amber-50'
    },
    {
      title: t('dashboard.documentsComplete'),
      value: stats?.documents?.complete || 0,
      icon: FileCheck,
      color: 'text-purple-600',
      bg: 'bg-purple-50'
    }
  ];

  return (
    <div className="space-y-6" data-testid="dashboard-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">{t('dashboard.title')}</h1>
          <p className="text-slate-500 mt-1">Welcome back! Here's your overview.</p>
        </div>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card, index) => (
          <Card key={index} className="dashboard-card" data-testid={`stat-card-${index}`}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-slate-500">{card.title}</p>
                  <p className="text-3xl font-bold text-slate-900 mt-1">{card.value}</p>
                </div>
                <div className={`w-12 h-12 rounded-xl ${card.bg} flex items-center justify-center`}>
                  <card.icon className={`w-6 h-6 ${card.color}`} />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Appointments by Status */}
        <Card className="dashboard-card">
          <CardHeader>
            <CardTitle className="text-lg font-semibold">{t('dashboard.appointmentsByStatus')}</CardTitle>
          </CardHeader>
          <CardContent>
            {appointmentData.length > 0 ? (
              <div className="chart-container">
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={appointmentData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="value"
                    >
                      {appointmentData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-64 flex items-center justify-center text-slate-400">
                {t('common.noData')}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Performance Chart (Admin only) */}
        {isAdmin && (
          <Card className="dashboard-card">
            <CardHeader>
              <CardTitle className="text-lg font-semibold flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-blue-600" />
                {t('dashboard.performance')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {performance.length > 0 ? (
                <div className="chart-container">
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={performance}>
                      <XAxis dataKey="salesperson_name" tick={{ fontSize: 12 }} />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="total_records" name="Records" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="sales" name="Sales" fill="#10b981" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="completed_appointments" name="Completed" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-64 flex items-center justify-center text-slate-400">
                  {t('common.noData')}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Status Legend */}
        {!isAdmin && (
          <Card className="dashboard-card">
            <CardHeader>
              <CardTitle className="text-lg font-semibold">Appointment Status Legend</CardTitle>
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
        <CardHeader>
          <CardTitle className="text-lg font-semibold">{t('clients.documents')} Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-xl bg-emerald-50 flex items-center justify-center">
                <FileCheck className="w-8 h-8 text-emerald-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{stats?.documents?.complete || 0}</p>
                <p className="text-sm text-slate-500">Complete Documents</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-xl bg-orange-50 flex items-center justify-center">
                <FileCheck className="w-8 h-8 text-orange-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900">{stats?.documents?.pending || 0}</p>
                <p className="text-sm text-slate-500">Pending Documents</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
