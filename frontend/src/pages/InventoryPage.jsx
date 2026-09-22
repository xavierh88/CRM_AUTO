import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Label } from '../components/ui/label';
import { toast } from 'sonner';
import {
  Plus, Search, Filter, Truck, Car, Package, DollarSign,
  ChevronDown, ChevronUp, Edit, Trash2, Eye, MoreHorizontal,
  AlertTriangle, CheckCircle, XCircle, LayoutGrid, LayoutList
} from 'lucide-react';
import { Skeleton } from '../components/ui/skeleton';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const STATUS_OPTIONS = [
  { value: 'available', label: 'Available' },
  { value: 'reserved', label: 'Reserved' },
  { value: 'sold', label: 'Sold' },
  { value: 'in_transit', label: 'In Transit' },
  { value: 'service', label: 'Service' },
];

const MAKES = ['Toyota', 'Honda', 'Ford', 'Chevrolet', 'Nissan', 'Hyundai', 'Kia', 'BMW', 'Mercedes-Benz', 'Audi', 'Lexus', 'Acura', 'Infiniti', 'Cadillac', 'Lincoln', 'Buick', 'GMC', 'Dodge', 'Jeep', 'Ram', 'Chrysler', 'Subaru', 'Mazda', 'Mitsubishi', 'Volkswagen', 'Volvo', 'Porsche', 'Tesla', 'Rivian', 'Lucid', 'Other'];

const statusBadgeVariant = {
  available: 'default',
  reserved: 'secondary',
  sold: 'destructive',
  in_transit: 'outline',
  service: 'outline',
};

const statusColors = {
  available: 'bg-emerald-500/20 text-emerald-500 border-emerald-500/30',
  reserved: 'bg-amber-500/20 text-amber-500 border-amber-500/30',
  sold: 'bg-rose-500/20 text-rose-500 border-rose-500/30',
  in_transit: 'bg-blue-500/20 text-blue-500 border-blue-500/30',
  service: 'bg-purple-500/20 text-purple-500 border-purple-500/30',
};

export default function InventoryPage() {
  const { t } = useTranslation();
  const { user, isAdmin, isBDCManager } = useAuth();
  const navigate = useNavigate();
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [makeFilter, setMakeFilter] = useState('all');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [selectedVehicle, setSelectedVehicle] = useState(null);
  const [totalCount, setTotalCount] = useState(0);
  const [viewMode, setViewMode] = useState('table'); // 'table' | 'card'

  // Form state
  const [formData, setFormData] = useState({
    vin: '', make: '', model: '', year: '', trim: '',
    color: '', mileage: '', price: '', cost: '',
    status: 'available', dealer: '', stock_number: '',
    description: '', features: '', images: []
  });
  const [formErrors, setFormErrors] = useState({});
  const [submitting, setSubmitting] = useState(false);

  const fetchVehicles = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (searchTerm) params.append('search', searchTerm);
      if (statusFilter !== 'all') params.append('status', statusFilter);
      if (makeFilter !== 'all') params.append('make', makeFilter);
      params.append('sort_by', sortBy);
      params.append('sort_order', sortOrder);
      
      // Role-based filtering
      if (!isAdmin && !isBDCManager) {
        params.append('dealer', user?.dealer_id || '');
      }

      const response = await axios.get(`${API}/inventory?${params.toString()}`);
      setVehicles(response.data.vehicles || []);
      setTotalCount(response.data.total || 0);
    } catch (error) {
      console.error('Failed to fetch vehicles:', error);
      // Mock data for demo
      if (error.response?.status === 404) {
        setVehicles([
          { id: '1', vin: '1HGCM82633A123456', make: 'Honda', model: 'Accord', year: 2023, trim: 'EX-L', color: 'White', mileage: 15000, price: 28500, cost: 25000, status: 'available', dealer: 'Main', stock_number: 'H23-001', days_on_lot: 45, created_at: '2024-01-15' },
          { id: '2', vin: '5TDZZRFH0MS123456', make: 'Toyota', model: 'RAV4', year: 2024, trim: 'XLE', color: 'Blue', mileage: 500, price: 34500, cost: 31000, status: 'available', dealer: 'Main', stock_number: 'T24-002', days_on_lot: 12, created_at: '2024-03-01' },
          { id: '3', vin: '1FTFW1E50MFA12345', make: 'Ford', model: 'F-150', year: 2023, trim: 'Lariat', color: 'Black', mileage: 22000, price: 42000, cost: 38000, status: 'reserved', dealer: 'North', stock_number: 'F23-003', days_on_lot: 78, created_at: '2023-11-20' },
          { id: '4', vin: '1G1BE5SM0N7123456', make: 'Chevrolet', model: 'Malibu', year: 2024, trim: 'LT', color: 'Silver', mileage: 100, price: 26500, cost: 23500, status: 'available', dealer: 'Main', stock_number: 'C24-004', days_on_lot: 8, created_at: '2024-03-10' },
          { id: '5', vin: 'KM8K33AG0NU123456', make: 'Hyundai', model: 'Santa Fe', year: 2023, trim: 'Limited', color: 'Red', mileage: 18000, price: 36500, cost: 32500, status: 'sold', dealer: 'South', stock_number: 'H23-005', days_on_lot: 120, created_at: '2023-09-01' },
        ]);
        setTotalCount(5);
      }
    } finally {
      setLoading(false);
    }
  }, [searchTerm, statusFilter, makeFilter, sortBy, sortOrder, user, isAdmin, isBDCManager]);

  useEffect(() => {
    fetchVehicles();
  }, [fetchVehicles]);

  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  };

  const getStatusBadge = (status) => {
    const variant = statusBadgeVariant[status] || 'outline';
    return (
      <Badge variant={variant} className="capitalize">
        {status.replace('_', ' ')}
      </Badge>
    );
  };

  const getStatusBadgeCard = (status) => {
    const className = statusColors[status] || statusColors.available;
    return (
      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${className}`}>
        {status.replace('_', ' ')}
      </span>
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setFormErrors({});
    
    // Validation
    const errors = {};
    if (!formData.vin) errors.vin = 'VIN is required';
    if (!formData.make) errors.make = 'Make is required';
    if (!formData.model) errors.model = 'Model is required';
    if (!formData.year) errors.year = 'Year is required';
    if (!formData.price) errors.price = 'Price is required';
    
    if (Object.keys(errors).length > 0) {
      setFormErrors(errors);
      setSubmitting(false);
      return;
    }

    try {
      if (selectedVehicle) {
        await axios.put(`${API}/inventory/${selectedVehicle.id}`, formData);
        toast.success('Vehicle updated');
      } else {
        await axios.post(`${API}/inventory`, formData);
        toast.success('Vehicle added');
      }
      setShowAddDialog(false);
      resetForm();
      fetchVehicles();
    } catch (error) {
      console.error('Failed to save vehicle:', error);
      toast.error(error.response?.data?.detail || 'Failed to save vehicle');
    } finally {
      setSubmitting(false);
    }
  };

  const resetForm = () => {
    setFormData({
      vin: '', make: '', model: '', year: '', trim: '',
      color: '', mileage: '', price: '', cost: '',
      status: 'available', dealer: '', stock_number: '',
      description: '', features: '', images: []
    });
    setSelectedVehicle(null);
    setFormErrors({});
  };

  const handleEdit = (vehicle) => {
    setSelectedVehicle(vehicle);
    setFormData({
      vin: vehicle.vin, make: vehicle.make, model: vehicle.model, year: vehicle.year, trim: vehicle.trim || '',
      color: vehicle.color || '', mileage: vehicle.mileage || '', price: vehicle.price, cost: vehicle.cost || '',
      status: vehicle.status, dealer: vehicle.dealer || '', stock_number: vehicle.stock_number || '',
      description: vehicle.description || '', features: vehicle.features || '', images: vehicle.images || []
    });
    setShowAddDialog(true);
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this vehicle?')) return;
    try {
      await axios.delete(`${API}/inventory/${id}`);
      toast.success('Vehicle deleted');
      fetchVehicles();
    } catch (error) {
      toast.error('Failed to delete vehicle');
    }
  };

  const filteredVehicles = vehicles.filter(v => {
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      return v.vin?.toLowerCase().includes(term) ||
             v.make?.toLowerCase().includes(term) ||
             v.model?.toLowerCase().includes(term) ||
             v.stock_number?.toLowerCase().includes(term);
    }
    return true;
  });

  const formatPrice = (price) => price ? `$${Number(price).toLocaleString()}` : '-';
  const formatMileage = (mileage) => mileage ? Number(mileage).toLocaleString() : '-';

  if (loading) {
    return (
      <div className="space-y-6" data-testid="inventory-page">
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground">{t('inventory.title')}</h1>
            <p className="text-muted-foreground mt-1">
              {totalCount} {totalCount === 1 ? 'vehicle' : 'vehicles'} in inventory
            </p>
          </div>
        </div>
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input placeholder={t('inventory.search')} disabled className="pl-10" />
              </div>
            </div>
          </CardContent>
        </Card>
        {viewMode === 'table' ? (
          <Card>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-b border-border">
                      {[...Array(10)].map((_, i) => (
                        <TableHead key={i} className="w-24 h-12">
                          <Skeleton className="h-4 w-3/4" />
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {[...Array(5)].map((_, i) => (
                      <TableRow key={i}>
                        {[...Array(10)].map((_, j) => (
                          <TableCell key={j} className="h-12">
                            <Skeleton className="h-4 w-full" />
                          </TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {[...Array(6)].map((_, i) => (
              <Card key={i} className="p-4">
                <Skeleton className="h-32 w-full rounded-lg mb-3" />
                <Skeleton className="h-5 w-3/4 mb-2" />
                <Skeleton className="h-4 w-1/2 mb-1" />
                <Skeleton className="h-4 w-1/3" />
              </Card>
            ))}
          </div>
        )}
      </div>
    );
  }

  const VehicleCard = ({ vehicle }) => (
    <Card className="p-4 hover:shadow-lg transition-shadow group flex flex-col h-full">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-foreground truncate">
            {vehicle.year} {vehicle.make} {vehicle.model}
            {vehicle.trim && <span className="text-muted-foreground ml-1">{vehicle.trim}</span>}
          </h3>
          <p className="text-xs text-muted-foreground font-mono">VIN: {vehicle.vin?.slice(-8)}</p>
        </div>
        {getStatusBadgeCard(vehicle.status)}
      </div>
      <div className="flex items-center gap-4 text-sm text-muted-foreground mb-3 flex-wrap">
        <span className="flex items-center gap-1">
          <Package className="w-3.5 h-3.5" />
          {vehicle.stock_number}
        </span>
        <span className="flex items-center gap-1">
          <Car className="w-3.5 h-3.5" />
          {vehicle.color}
        </span>
        <span className="flex items-center gap-1">
          <Truck className="w-3.5 h-3.5" />
          {formatMileage(vehicle.mileage)} mi
        </span>
        <span className="flex items-center gap-1">
          <Calendar className="w-3.5 h-3.5" />
          {vehicle.days_on_lot} days
        </span>
      </div>
      <div className="mt-auto pt-3 border-t border-border flex items-center justify-between">
        <div className="font-bold text-lg text-foreground">{formatPrice(vehicle.price)}</div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => handleEdit(vehicle)} aria-label={t('common.edit') || 'Edit'}>
            <Eye className="w-4 h-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => handleDelete(vehicle.id)} aria-label={t('common.delete') || 'Delete'} className="text-destructive hover:text-destructive">
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </Card>
  );

  return (
    <div className="space-y-6" data-testid="inventory-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">{t('inventory.title')}</h1>
          <p className="text-muted-foreground mt-1">
            {totalCount} {totalCount === 1 ? 'vehicle' : 'vehicles'} in inventory
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="hidden sm:flex border-border bg-muted rounded-lg p-1" role="group" aria-label="View mode">
            <Button
              variant={viewMode === 'table' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('table')}
              aria-pressed={viewMode === 'table'}
              aria-label="Table view"
            >
              <LayoutList className="w-4 h-4" />
            </Button>
            <Button
              variant={viewMode === 'card' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('card')}
              aria-pressed={viewMode === 'card'}
              aria-label="Card view"
            >
              <LayoutGrid className="w-4 h-4" />
            </Button>
          </div>
          <Button onClick={() => { resetForm(); setShowAddDialog(true); }}>
            <Plus className="w-4 h-4 mr-2" />
            {t('inventory.addVehicle')}
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
                placeholder={t('inventory.search')}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-full sm:w-40">
                <SelectValue placeholder={t('inventory.status')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('common.all') || 'All'}</SelectItem>
                {STATUS_OPTIONS.map(opt => (
                  <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={makeFilter} onValueChange={setMakeFilter}>
              <SelectTrigger className="w-full sm:w-48">
                <SelectValue placeholder={t('inventory.make')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('common.all') || 'All'}</SelectItem>
                {MAKES.map(make => (
                  <SelectItem key={make} value={make}>{make}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Vehicle List */}
      {viewMode === 'table' ? (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow className="border-b border-border bg-muted/50">
                    <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('stock_number')}>
                      Stock # <span className={sortBy === 'stock_number' ? (sortOrder === 'asc' ? ' ↑' : ' ↓') : ''} />
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('year')}>
                      Year <span className={sortBy === 'year' ? (sortOrder === 'asc' ? ' ↑' : ' ↓') : ''} />
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('make')}>
                      Make <span className={sortBy === 'make' ? (sortOrder === 'asc' ? ' ↑' : ' ↓') : ''} />
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('model')}>
                      Model <span className={sortBy === 'model' ? (sortOrder === 'asc' ? ' ↑' : ' ↓') : ''} />
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('trim')}>
                      Trim
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('color')}>
                      Color
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('mileage')}>
                      Mileage <span className={sortBy === 'mileage' ? (sortOrder === 'asc' ? ' ↑' : ' ↓') : ''} />
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('price')}>
                      Price <span className={sortBy === 'price' ? (sortOrder === 'asc' ? ' ↑' : ' ↓') : ''} />
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('status')}>
                      Status <span className={sortBy === 'status' ? (sortOrder === 'asc' ? ' ↑' : ' ↓') : ''} />
                    </TableHead>
                    <TableHead className="cursor-pointer hover:bg-muted" onClick={() => handleSort('days_on_lot')}>
                      Days
                    </TableHead>
                    <TableHead className="text-right w-24">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredVehicles.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={11} className="text-center py-12 text-muted-foreground">
                        {t('inventory.noVehicles')}
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredVehicles.map((vehicle) => (
                      <TableRow key={vehicle.id} className="hover:bg-muted/50 border-b border-border/50">
                        <TableCell className="font-mono text-sm font-medium">{vehicle.stock_number || '-'}</TableCell>
                        <TableCell>{vehicle.year}</TableCell>
                        <TableCell>{vehicle.make}</TableCell>
                        <TableCell>{vehicle.model}</TableCell>
                        <TableCell>{vehicle.trim || '-'}</TableCell>
                        <TableCell>{vehicle.color || '-'}</TableCell>
                        <TableCell className="font-mono tabular-nums">{formatMileage(vehicle.mileage)}</TableCell>
                        <TableCell className="font-medium tabular-nums">{formatPrice(vehicle.price)}</TableCell>
                        <TableCell>{getStatusBadge(vehicle.status)}</TableCell>
                        <TableCell className="font-mono tabular-nums text-muted-foreground">{vehicle.days_on_lot || 0}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button variant="ghost" size="sm" onClick={() => handleEdit(vehicle)} aria-label={t('common.edit') || 'Edit'}>
                              <Eye className="w-4 h-4" />
                            </Button>
                            <Button variant="ghost" size="sm" onClick={() => handleDelete(vehicle.id)} aria-label={t('common.delete') || 'Delete'} className="text-destructive hover:text-destructive">
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {filteredVehicles.length === 0 ? (
            <div className="col-span-full text-center py-12 text-muted-foreground">
              <Package className="w-12 h-12 mx-auto mb-3 text-muted-foreground/30" />
              <p>{t('inventory.noVehicles')}</p>
            </div>
          ) : (
            filteredVehicles.map((vehicle) => (
              <VehicleCard key={vehicle.id} vehicle={vehicle} />
            ))
          )}
        </div>
      )}

      {/* Add/Edit Vehicle Dialog */}
      <Dialog open={showAddDialog} onOpenChange={setShowAddDialog}>
        <DialogContent className="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedVehicle ? 'Edit Vehicle' : t('inventory.addVehicle')}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="p-4 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="vin">VIN *</Label>
                <Input id="vin" value={formData.vin} onChange={(e) => setFormData({...formData, vin: e.target.value})} error={formErrors.vin} maxLength={17} />
              </div>
              <div>
                <Label htmlFor="stock_number">Stock #</Label>
                <Input id="stock_number" value={formData.stock_number} onChange={(e) => setFormData({...formData, stock_number: e.target.value})} />
              </div>
              <div>
                <Label htmlFor="make">Make *</Label>
                <Select value={formData.make} onValueChange={(v) => setFormData({...formData, make: v})}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select make" />
                  </SelectTrigger>
                  <SelectContent>
                    {MAKES.map(make => (
                      <SelectItem key={make} value={make}>{make}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="model">Model *</Label>
                <Input id="model" value={formData.model} onChange={(e) => setFormData({...formData, model: e.target.value})} error={formErrors.model} />
              </div>
              <div>
                <Label htmlFor="year">Year *</Label>
                <Input id="year" type="number" value={formData.year} onChange={(e) => setFormData({...formData, year: e.target.value})} error={formErrors.year} min={1990} max={new Date().getFullYear() + 1} />
              </div>
              <div>
                <Label htmlFor="trim">Trim</Label>
                <Input id="trim" value={formData.trim} onChange={(e) => setFormData({...formData, trim: e.target.value})} />
              </div>
              <div>
                <Label htmlFor="color">Color</Label>
                <Input id="color" value={formData.color} onChange={(e) => setFormData({...formData, color: e.target.value})} />
              </div>
              <div>
                <Label htmlFor="mileage">Mileage</Label>
                <Input id="mileage" type="number" value={formData.mileage} onChange={(e) => setFormData({...formData, mileage: e.target.value})} min={0} />
              </div>
              <div>
                <Label htmlFor="price">Price *</Label>
                <Input id="price" type="number" value={formData.price} onChange={(e) => setFormData({...formData, price: e.target.value})} error={formErrors.price} min={0} step={100} />
              </div>
              <div>
                <Label htmlFor="cost">Cost</Label>
                <Input id="cost" type="number" value={formData.cost} onChange={(e) => setFormData({...formData, cost: e.target.value})} min={0} step={100} />
              </div>
              <div>
                <Label htmlFor="status">Status</Label>
                <Select value={formData.status} onValueChange={(v) => setFormData({...formData, status: v})}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    {STATUS_OPTIONS.map(opt => (
                      <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label htmlFor="dealer">Dealer</Label>
                <Input id="dealer" value={formData.dealer} onChange={(e) => setFormData({...formData, dealer: e.target.value})} />
              </div>
            </div>
            <div>
              <Label htmlFor="description">Description</Label>
              <textarea id="description" className="w-full min-h-[80px] p-3 border border-border rounded-lg bg-background text-foreground" value={formData.description} onChange={(e) => setFormData({...formData, description: e.target.value})} />
            </div>
            <div>
              <Label htmlFor="features">Features (comma separated)</Label>
              <Input id="features" value={formData.features} onChange={(e) => setFormData({...formData, features: e.target.value})} placeholder="Bluetooth, Backup Camera, Leather Seats..." />
            </div>
            <div className="flex justify-end gap-2 pt-4 border-t">
              <Button type="button" variant="outline" onClick={() => { setShowAddDialog(false); resetForm(); }}>
                {t('common.cancel')}
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting ? 'Saving...' : t('common.save')}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
