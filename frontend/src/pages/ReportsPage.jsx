import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import {
  BarChart3, DollarSign, Users, Calendar, TrendingUp, Target,
  Package, Download, Filter, RefreshCw, Loader2,
  FileSpreadsheet, FileText
} from 'lucide-react';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Legend,
  PieChart, Pie, Cell, AreaChart, Area, LineChart, Line
} from 'recharts';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function ReportsPage() {
  const { t } = useTranslation();
  const { user, isAdmin, isBDCManager } = useAuth();
  const [period, setPeriod] = useState('month');
  const [loading, setLoading] = useState(false);
  const [salesReport, setSalesReport] = useState([]);
  const [leadsReport, setLeadsReport] = useState([]);
  const [appointmentsReport, setAppointmentsReport] = useState([]);
  const [financialSummary, setFinancialSummary] = useState({});
  const [inventoryReport, setInventoryReport] = useState([]);
  const [attributionReport, setAttributionReport] = useState([]);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ period });
      if (!isAdmin && !isBDCManager) {
        params.append('user_id', user.id);
      }

      const [salesRes, leadsRes, apptRes, financeRes, invRes, attrRes] = await Promise.all([
        axios.get(`${API}/reports/sales?${params.toString()}`).catch(() => ({ data: [] })),
        axios.get(`${API}/reports/leads?${params.toString()}`).catch(() => ({ data: [] })),
        axios.get(`${API}/reports/appointments?${params.toString()}`).catch(() => ({ data: [] })),
        axios.get(`${API}/reports/financial?${params.toString()}`).catch(() => ({ data: {} })),
        axios.get(`${API}/reports/inventory?${params.toString()}`).catch(() => ({ data: [] })),
        axios.get(`${API}/reports/attribution?${params.toString()}`).catch(() => ({ data: [] })),
      ]);

      setSalesReport(salesRes.data);
      setLeadsReport(leadsRes.data);
      setAppointmentsReport(apptRes.data);
      setFinancialSummary(financeRes.data);
      setInventoryReport(invRes.data);
      setAttributionReport(attrRes.data);
    } catch (error) {
      console.error('Failed to fetch reports:', error);
      // Mock data for demo
      setSalesReport([
        { month: 'Jan', sales: 12, revenue: 340000 },
        { month: 'Feb', sales: 15, revenue: 420000 },
        { month: 'Mar', sales: 18, revenue: 510000 },
        { month: 'Apr', sales: 14, revenue: 390000 },
        { month: 'May', sales: 20, revenue: 560000 },
        { month: 'Jun', sales: 22, revenue: 620000 },
      ]);
      setLeadsReport([
        { source: 'Website', count: 45, converted: 12 },
        { source: 'Walk-in', count: 30, converted: 8 },
        { source: 'Referral', count: 20, converted: 10 },
        { source: 'Social Media', count: 25, converted: 5 },
        { source: 'Phone', count: 15, converted: 4 },
      ]);
      setAppointmentsReport([
        { status: 'agendado', count: 35 },
        { status: 'cumplido', count: 28 },
        { status: 'no_show', count: 5 },
        { status: 'sin_configurar', count: 12 },
        { status: 'cambio_hora', count: 3 },
      ]);
      setFinancialSummary({
        total_revenue: 2840000,
        avg_deal: 32000,
        total_gross: 420000,
        total_down_payment: 580000,
      });
      setInventoryReport([
        { make: 'Toyota', count: 15, avg_days: 32 },
        { make: 'Honda', count: 12, avg_days: 28 },
        { make: 'Ford', count: 10, avg_days: 45 },
        { make: 'Chevrolet', count: 8, avg_days: 38 },
        { make: 'Nissan', count: 6, avg_days: 41 },
      ]);
      setAttributionReport([
        { campaign: 'Google Ads', leads: 35, sales: 8, cost: 5000, roi: 4.2 },
        { campaign: 'Facebook', leads: 28, sales: 5, cost: 3500, roi: 3.8 },
        { campaign: 'Email', leads: 20, sales: 4, cost: 800, roi: 12.5 },
        { campaign: 'Referral', leads: 15, sales: 6, cost: 0, roi: 0 },
        { campaign: 'Organic', leads: 22, sales: 5, cost: 0, roi: 0 },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, [period, user, isAdmin, isBDCManager]);

  const handleExport = (type) => {
    toast.info(`Exporting ${type} report... (Feature pending backend)`);
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 0 }).format(value);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="loading-spinner" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="reports-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('reports.title')}</h1>
          <p className="text-muted-foreground mt-1">{t('reports.subtitle') || 'Business intelligence and analytics'}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Select value={period} onValueChange={setPeriod}>
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="week">{t('common.thisWeek')}</SelectItem>
              <SelectItem value="month">{t('common.thisMonth')}</SelectItem>
              <SelectItem value="quarter">{t('common.thisQuarter')}</SelectItem>
              <SelectItem value="year">{t('common.thisYear')}</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" onClick={() => handleExport('all')}>
            <Download className="w-4 h-4 mr-2" />
            Export All
          </Button>
        </div>
      </div>

      {/* Financial Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('reports.totalRevenue') || 'Total Revenue'}</p>
                <p className="text-2xl font-bold">{formatCurrency(financialSummary.total_revenue || 0)}</p>
              </div>
              <div className="p-3 bg-green-500/10 rounded-lg">
                <DollarSign className="w-6 h-6 text-green-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('reports.avgDeal') || 'Avg Deal Size'}</p>
                <p className="text-2xl font-bold">{formatCurrency(financialSummary.avg_deal || 0)}</p>
              </div>
              <div className="p-3 bg-blue-500/10 rounded-lg">
                <Target className="w-6 h-6 text-blue-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('reports.totalGross') || 'Total Gross'}</p>
                <p className="text-2xl font-bold">{formatCurrency(financialSummary.total_gross || 0)}</p>
              </div>
              <div className="p-3 bg-amber-500/10 rounded-lg">
                <TrendingUp className="w-6 h-6 text-amber-500" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('reports.downPayment') || 'Down Payments'}</p>
                <p className="text-2xl font-bold">{formatCurrency(financialSummary.total_down_payment || 0)}</p>
              </div>
              <div className="p-3 bg-emerald-500/10 rounded-lg">
                <DollarSign className="w-6 h-6 text-emerald-500" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs for different reports */}
      <Tabs defaultValue="sales" className="space-y-4">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="sales">{t('reports.sales')}</TabsTrigger>
          <TabsTrigger value="leads">{t('reports.leads')}</TabsTrigger>
          <TabsTrigger value="appointments">{t('reports.appointments')}</TabsTrigger>
          <TabsTrigger value="inventory">{t('reports.inventory')}</TabsTrigger>
          <TabsTrigger value="financial">{t('reports.financial')}</TabsTrigger>
          <TabsTrigger value="attribution">{t('reports.attribution')}</TabsTrigger>
        </TabsList>

        {/* Sales Report */}
        <TabsContent value="sales" className="space-y-4">
          <div className="flex justify-between">
            <CardTitle className="text-lg">{t('reports.salesTrend') || 'Sales Trend'}</CardTitle>
            <Button variant="outline" onClick={() => handleExport('sales')}>
              <FileSpreadsheet className="w-4 h-4 mr-1" /> Export
            </Button>
          </div>
          <Card>
            <CardContent className="p-4">
              <ResponsiveContainer width="100%" height={350}>
                <AreaChart data={salesReport}>
                  <defs>
                    <linearGradient id="colorSales" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="hsl(var(--accent))" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="hsl(var(--accent))" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="month" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                  <YAxis tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                  <Tooltip />
                  <Legend />
                  <Area type="monotone" dataKey="sales" name="Units Sold" stroke="hsl(var(--primary))" strokeWidth={2} fillOpacity={1} fill="url(#colorSales)" />
                  <Area type="monotone" dataKey="revenue" name="Revenue" stroke="hsl(var(--accent))" strokeWidth={2} fillOpacity={1} fill="url(#colorRevenue)" yAxisId="right" />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Leads Report */}
        <TabsContent value="leads" className="space-y-4">
          <div className="flex justify-between">
            <CardTitle className="text-lg">{t('reports.leadsBySource') || 'Leads by Source'}</CardTitle>
            <Button variant="outline" onClick={() => handleExport('leads')}>
              <FileSpreadsheet className="w-4 h-4 mr-1" /> Export
            </Button>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardContent className="p-4">
                <ResponsiveContainer width="100%" height={350}>
                  <PieChart>
                    <Pie
                      data={leadsReport}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="count"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {leadsReport.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={`hsl(var(--chart-${(index % 5) + 1}))`} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart data={leadsReport} layout="vertical">
                    <XAxis type="number" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                    <YAxis dataKey="source" type="category" tick={{ fill: 'hsl(var(--muted-foreground))' }} width={100} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="count" name="Total Leads" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
                    <Bar dataKey="converted" name="Converted" fill="hsl(var(--accent))" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Appointments Report */}
        <TabsContent value="appointments" className="space-y-4">
          <div className="flex justify-between">
            <CardTitle className="text-lg">{t('reports.appointmentsByStatus') || 'Appointments by Status'}</CardTitle>
            <Button variant="outline" onClick={() => handleExport('appointments')}>
              <FileSpreadsheet className="w-4 h-4 mr-1" /> Export
            </Button>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card>
              <CardContent className="p-4">
                <ResponsiveContainer width="100%" height={350}>
                  <PieChart>
                    <Pie
                      data={appointmentsReport}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={2}
                      dataKey="count"
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    >
                      {appointmentsReport.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={`hsl(var(--chart-${(index % 5) + 1}))`} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
            <Card>
              <CardContent className="p-4">
                <ResponsiveContainer width="100%" height={350}>
                  <BarChart data={appointmentsReport}>
                    <XAxis dataKey="status" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                    <YAxis tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="hsl(var(--primary))" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Inventory Report */}
        <TabsContent value="inventory" className="space-y-4">
          <div className="flex justify-between">
            <CardTitle className="text-lg">{t('reports.inventoryAging') || 'Inventory Aging'}</CardTitle>
            <Button variant="outline" onClick={() => handleExport('inventory')}>
              <FileSpreadsheet className="w-4 h-4 mr-1" /> Export
            </Button>
          </div>
          <Card>
            <CardContent className="p-4">
              <ResponsiveContainer width="100%" height={350}>
                <BarChart data={inventoryReport} layout="vertical">
                  <XAxis type="number" tick={{ fill: 'hsl(var(--muted-foreground))' }} />
                  <YAxis dataKey="make" type="category" tick={{ fill: 'hsl(var(--muted-foreground))' }} width={100} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="count" name="Units" fill="hsl(var(--primary))" radius={[0, 4, 4, 0]} />
                  <Bar dataKey="avg_days" name="Avg Days on Lot" fill="hsl(var(--accent))" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Financial Report */}
        <TabsContent value="financial" className="space-y-4">
          <div className="flex justify-between">
            <CardTitle className="text-lg">{t('reports.financialSummary') || 'Financial Summary'}</CardTitle>
            <Button variant="outline" onClick={() => handleExport('financial')}>
              <FileSpreadsheet className="w-4 h-4 mr-1" /> Export
            </Button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { label: t('reports.grossProfit') || 'Gross Profit', value: formatCurrency(financialSummary.total_gross || 0), icon: TrendingUp, color: 'text-emerald-500' },
              { label: t('reports.avgDownPayment') || 'Avg Down Payment', value: formatCurrency((financialSummary.total_down_payment || 0) / Math.max(salesReport.reduce((s, r) => s + r.sales, 0), 1)), icon: DollarSign, color: 'text-blue-500' },
              { label: t('reports.vehiclesSold') || 'Vehicles Sold', value: salesReport.reduce((s, r) => s + r.sales, 0), icon: Package, color: 'text-amber-500' },
              { label: t('reports.closeRate') || 'Close Rate', value: `${((leadsReport.reduce((s, r) => s + r.converted, 0) / Math.max(leadsReport.reduce((s, r) => s + r.count, 0), 1)) * 100).toFixed(1)}%`, icon: Target, color: 'text-purple-500' },
            ].map((stat, i) => (
              <Card key={i} className="text-center">
                <CardContent className="py-6">
                  <div className={`p-3 rounded-lg ${stat.color}/10 inline-flex`}>
                    <stat.icon className={`w-6 h-6 ${stat.color}`} />
                  </div>
                  <p className="text-3xl font-bold mt-3">{stat.value}</p>
                  <p className="text-sm text-muted-foreground mt-1">{stat.label}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Attribution Report */}
        <TabsContent value="attribution" className="space-y-4">
          <div className="flex justify-between">
            <CardTitle className="text-lg">{t('reports.attribution') || 'Marketing Attribution'}</CardTitle>
            <Button variant="outline" onClick={() => handleExport('attribution')}>
              <FileSpreadsheet className="w-4 h-4 mr-1" /> Export
            </Button>
          </div>
          <Card>
            <CardContent className="p-4">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="p-4 text-left font-medium text-muted-foreground">Campaign</th>
                      <th className="p-4 text-right font-medium text-muted-foreground">Leads</th>
                      <th className="p-4 text-right font-medium text-muted-foreground">Sales</th>
                      <th className="p-4 text-right font-medium text-muted-foreground">Cost</th>
                      <th className="p-4 text-right font-medium text-muted-foreground">ROI</th>
                      <th className="p-4 text-right font-medium text-muted-foreground">Cost/Lead</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attributionReport.map((row, i) => (
                      <tr key={i} className="border-b border-border/50 hover:bg-muted/50">
                        <td className="p-4 font-medium">{row.campaign}</td>
                        <td className="p-4 text-right">{row.leads}</td>
                        <td className="p-4 text-right font-semibold">{row.sales}</td>
                        <td className="p-4 text-right">{formatCurrency(row.cost)}</td>
                        <td className="p-4 text-right font-medium text-emerald-500">{row.roi}x</td>
                        <td className="p-4 text-right">{row.leads > 0 ? formatCurrency(row.cost / row.leads) : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}