import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Users, Calendar, TrendingUp, Award, Target, UserCheck } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

export default function VendedoresPage() {
  const { user } = useAuth();
  const [performance, setPerformance] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState('sales_month');

  useEffect(() => {
    fetchPerformance();
  }, []);

  const fetchPerformance = async () => {
    try {
      const res = await axios.get(`${API}/bdc/salesperson-performance`);
      setPerformance(res.data);
    } catch (error) {
      console.error('Error fetching performance:', error);
    } finally {
      setLoading(false);
    }
  };

  const sortedPerformance = [...performance].sort((a, b) => {
    switch (sortBy) {
      case 'sales_month':
        return b.sales.month - a.sales.month;
      case 'sales_total':
        return b.sales.total - a.sales.total;
      case 'clients_month':
        return b.clients.month - a.clients.month;
      case 'appointments_month':
        return b.appointments.month - a.appointments.month;
      default:
        return 0;
    }
  });

  const getTotalStats = () => {
    return {
      clients_today: performance.reduce((sum, p) => sum + p.clients.today, 0),
      clients_week: performance.reduce((sum, p) => sum + p.clients.week, 0),
      clients_month: performance.reduce((sum, p) => sum + p.clients.month, 0),
      sales_today: performance.reduce((sum, p) => sum + p.sales.today, 0),
      sales_week: performance.reduce((sum, p) => sum + p.sales.week, 0),
      sales_month: performance.reduce((sum, p) => sum + p.sales.month, 0),
      appointments_today: performance.reduce((sum, p) => sum + p.appointments.today, 0),
      appointments_week: performance.reduce((sum, p) => sum + p.appointments.week, 0),
      appointments_month: performance.reduce((sum, p) => sum + p.appointments.month, 0),
    };
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner"></div>
      </div>
    );
  }

  const totals = getTotalStats();

  return (
    <div className="space-y-6" data-testid="vendedores-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Rendimiento de Telemarketers</h1>
          <p className="text-slate-500 mt-1">Métricas y análisis del equipo de TM</p>
        </div>
        <Select value={sortBy} onValueChange={setSortBy}>
          <SelectTrigger className="w-48">
            <SelectValue placeholder="Ordenar por..." />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="sales_month">Ventas (Mes)</SelectItem>
            <SelectItem value="sales_total">Ventas (Total)</SelectItem>
            <SelectItem value="clients_month">Clientes (Mes)</SelectItem>
            <SelectItem value="appointments_month">Citas (Mes)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-blue-500 to-blue-600 text-white">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-100 text-sm">Telemarketers</p>
                <p className="text-3xl font-bold">{performance.length}</p>
              </div>
              <Users className="w-10 h-10 text-blue-200" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-green-500 to-green-600 text-white">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-green-100 text-sm">Ventas (Mes)</p>
                <p className="text-3xl font-bold">{totals.sales_month}</p>
              </div>
              <TrendingUp className="w-10 h-10 text-green-200" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-purple-500 to-purple-600 text-white">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-purple-100 text-sm">Clientes (Mes)</p>
                <p className="text-3xl font-bold">{totals.clients_month}</p>
              </div>
              <UserCheck className="w-10 h-10 text-purple-200" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-amber-500 to-amber-600 text-white">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-amber-100 text-sm">Citas (Mes)</p>
                <p className="text-3xl font-bold">{totals.appointments_month}</p>
              </div>
              <Calendar className="w-10 h-10 text-amber-200" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Salesperson Performance Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Award className="w-5 h-5 text-amber-500" />
            Ranking de Vendedores
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-2 text-sm font-medium text-slate-600">#</th>
                  <th className="text-left py-3 px-2 text-sm font-medium text-slate-600">Vendedor</th>
                  <th className="text-center py-3 px-2 text-sm font-medium text-slate-600" colSpan="3">Clientes</th>
                  <th className="text-center py-3 px-2 text-sm font-medium text-slate-600" colSpan="3">Citas</th>
                  <th className="text-center py-3 px-2 text-sm font-medium text-slate-600" colSpan="3">Ventas</th>
                  <th className="text-center py-3 px-2 text-sm font-medium text-slate-600">Records</th>
                </tr>
                <tr className="border-b bg-slate-50">
                  <th className="py-2 px-2"></th>
                  <th className="py-2 px-2"></th>
                  <th className="text-center py-2 px-1 text-xs text-slate-500">Hoy</th>
                  <th className="text-center py-2 px-1 text-xs text-slate-500">Sem</th>
                  <th className="text-center py-2 px-1 text-xs text-slate-500">Mes</th>
                  <th className="text-center py-2 px-1 text-xs text-slate-500">Hoy</th>
                  <th className="text-center py-2 px-1 text-xs text-slate-500">Sem</th>
                  <th className="text-center py-2 px-1 text-xs text-slate-500">Mes</th>
                  <th className="text-center py-2 px-1 text-xs text-slate-500">Hoy</th>
                  <th className="text-center py-2 px-1 text-xs text-slate-500">Sem</th>
                  <th className="text-center py-2 px-1 text-xs text-slate-500">Mes</th>
                  <th className="text-center py-2 px-1 text-xs text-slate-500">Total</th>
                </tr>
              </thead>
              <tbody>
                {sortedPerformance.map((sp, index) => (
                  <tr key={sp.id} className="border-b hover:bg-slate-50">
                    <td className="py-3 px-2">
                      <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold ${
                        index === 0 ? 'bg-yellow-100 text-yellow-700' :
                        index === 1 ? 'bg-slate-200 text-slate-700' :
                        index === 2 ? 'bg-amber-100 text-amber-700' :
                        'bg-slate-100 text-slate-500'
                      }`}>
                        {index + 1}
                      </span>
                    </td>
                    <td className="py-3 px-2">
                      <div>
                        <p className="font-medium text-slate-900">{sp.name}</p>
                        <p className="text-xs text-slate-400">{sp.email}</p>
                      </div>
                    </td>
                    {/* Clients */}
                    <td className="text-center py-3 px-1 text-sm">{sp.clients.today}</td>
                    <td className="text-center py-3 px-1 text-sm">{sp.clients.week}</td>
                    <td className="text-center py-3 px-1 text-sm font-medium text-blue-600">{sp.clients.month}</td>
                    {/* Appointments */}
                    <td className="text-center py-3 px-1 text-sm">{sp.appointments.today}</td>
                    <td className="text-center py-3 px-1 text-sm">{sp.appointments.week}</td>
                    <td className="text-center py-3 px-1 text-sm font-medium text-purple-600">{sp.appointments.month}</td>
                    {/* Sales */}
                    <td className="text-center py-3 px-1 text-sm">{sp.sales.today}</td>
                    <td className="text-center py-3 px-1 text-sm">{sp.sales.week}</td>
                    <td className="text-center py-3 px-1 text-sm font-bold text-green-600">{sp.sales.month}</td>
                    {/* Records Total */}
                    <td className="text-center py-3 px-1 text-sm text-slate-600">{sp.records_total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
