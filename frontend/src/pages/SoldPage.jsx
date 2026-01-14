import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { useAuth } from '../context/AuthContext';
import { Search, Trophy, User, Phone, Mail, Car, Building2, Calendar, DollarSign } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function SoldPage() {
  const { user, token } = useAuth();
  const [soldClients, setSoldClients] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSalesperson, setSelectedSalesperson] = useState('');
  const [salespersons, setSalespersons] = useState([]);

  const isAdmin = user?.role === 'admin';
  const isBDCManager = user?.role === 'bdc_manager' || user?.role === 'bdc';
  const canFilterBySalesperson = isAdmin || isBDCManager;

  useEffect(() => {
    fetchSoldClients();
    if (canFilterBySalesperson) {
      fetchSalespersons();
    }
  }, [token, selectedSalesperson]);

  const fetchSoldClients = async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams();
      if (searchTerm) params.append('search', searchTerm);
      if (selectedSalesperson) params.append('salesperson_id', selectedSalesperson);
      
      const response = await axios.get(`${API}/clients/sold/list?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSoldClients(response.data);
    } catch (error) {
      console.error('Error fetching sold clients:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchSalespersons = async () => {
    try {
      const response = await axios.get(`${API}/salespersons`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSalespersons(response.data);
    } catch (error) {
      console.error('Error fetching salespersons:', error);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    fetchSoldClients();
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('es-MX', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <div className="space-y-6" data-testid="sold-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
            <Trophy className="w-7 h-7 text-amber-500" />
            Clientes Vendidos
          </h1>
          <p className="text-slate-500 mt-1">
            {soldClients.length} cliente{soldClients.length !== 1 ? 's' : ''} vendido{soldClients.length !== 1 ? 's' : ''}
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto">
          {canFilterBySalesperson && (
            <select
              value={selectedSalesperson}
              onChange={(e) => setSelectedSalesperson(e.target.value)}
              className="px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              data-testid="salesperson-filter"
            >
              <option value="">Todos los Telemarketers</option>
              {salespersons.map((sp) => (
                <option key={sp.id} value={sp.id}>
                  {sp.name || sp.email}
                </option>
              ))}
            </select>
          )}

          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
              <Input
                type="text"
                placeholder="Buscar cliente..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-9 w-64"
                data-testid="search-input"
              />
            </div>
          </form>
        </div>
      </div>

      {/* Sold Clients Grid */}
      {loading ? (
        <div className="flex justify-center items-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-500"></div>
        </div>
      ) : soldClients.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Trophy className="w-12 h-12 mx-auto text-slate-300 mb-4" />
            <h3 className="text-lg font-medium text-slate-700">No hay clientes vendidos</h3>
            <p className="text-slate-500 mt-1">Los clientes aparecerán aquí cuando se marquen como vendidos</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {soldClients.map((client) => (
            <Card key={client.id} className="hover:shadow-lg transition-shadow border-l-4 border-l-amber-500" data-testid={`sold-client-${client.id}`}>
              <CardHeader className="pb-2">
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <User className="w-4 h-4 text-slate-400" />
                      {client.first_name} {client.last_name}
                    </CardTitle>
                    <Badge variant="outline" className="mt-1 bg-amber-50 text-amber-700 border-amber-200">
                      <Trophy className="w-3 h-3 mr-1" />
                      VENDIDO
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* Contact Info */}
                <div className="space-y-1 text-sm">
                  <div className="flex items-center gap-2 text-slate-600">
                    <Phone className="w-4 h-4 text-slate-400" />
                    {client.phone || 'Sin teléfono'}
                  </div>
                  {client.email && (
                    <div className="flex items-center gap-2 text-slate-600">
                      <Mail className="w-4 h-4 text-slate-400" />
                      {client.email}
                    </div>
                  )}
                </div>

                {/* Sale Info */}
                {client.sold_record && (
                  <div className="pt-2 border-t border-slate-100 space-y-1 text-sm">
                    {client.sold_record.auto && (
                      <div className="flex items-center gap-2 text-slate-600">
                        <Car className="w-4 h-4 text-slate-400" />
                        {client.sold_record.auto}
                      </div>
                    )}
                    {client.sold_record.bank && (
                      <div className="flex items-center gap-2 text-slate-600">
                        <Building2 className="w-4 h-4 text-slate-400" />
                        {client.sold_record.bank}
                      </div>
                    )}
                    {client.sold_record.finance_status && (
                      <div className="flex items-center gap-2 text-slate-600">
                        <DollarSign className="w-4 h-4 text-slate-400" />
                        {client.sold_record.finance_status === 'financiado' ? 'Financiado' : 
                         client.sold_record.finance_status === 'lease' ? 'Lease' : 
                         client.sold_record.finance_status}
                      </div>
                    )}
                  </div>
                )}

                {/* Sale Date */}
                <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                  <div className="flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    Vendido: {formatDate(client.sold_at)}
                  </div>
                  {canFilterBySalesperson && client.salesperson_name && (
                    <span className="text-slate-400">
                      {client.salesperson_name}
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
