import { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Checkbox } from './ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from './ui/dialog';
import { Textarea } from './ui/textarea';
import { Badge } from './ui/badge';
import { toast } from 'sonner';
import { 
  MessageSquare, Plus, Trash2, User, AlertTriangle, Car, DollarSign,
  CreditCard, RefreshCw, Loader2
} from 'lucide-react';
import { format, parseISO } from 'date-fns';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function OpportunityForm({ 
  record, 
  onSave, 
  onCancel, 
  isNew = false,
  configLists = {},
  clientId
}) {
  const [formData, setFormData] = useState({
    // ID fields
    has_id: false,
    id_type: '',
    // POI fields
    has_poi: false,
    poi_type: '',
    // Other checks
    ssn: false,
    itin: false,
    self_employed: false,
    // POR fields
    has_por: false,
    por_types: [],
    // Bank info
    bank: '',
    bank_deposit_type: '',
    // Other fields
    auto: '',
    credit: '',
    auto_loan: '',
    // Down Payment
    down_payment_type: '',
    down_payment_cash: '',
    down_payment_card: '',
    // Trade-in
    trade_make: '',
    trade_model: '',
    trade_year: '',
    trade_title: '',
    trade_miles: '',
    trade_plate: '',
    trade_estimated_value: '',
    // Dealer
    dealer: '',
    // Finance status
    finance_status: 'no',
    // Vehicle info
    vehicle_make: '',
    vehicle_year: '',
    sale_month: '',
    sale_day: '',
    sale_year: '',
    ...record
  });

  const [showCosignerAlert, setShowCosignerAlert] = useState(false);
  const [comments, setComments] = useState([]);
  const [newComment, setNewComment] = useState('');
  const [showComments, setShowComments] = useState(false);
  const [loadingComments, setLoadingComments] = useState(false);
  const [saving, setSaving] = useState(false);

  // Fetch comments if editing existing record
  useEffect(() => {
    if (record?.id) {
      fetchComments();
    }
  }, [record?.id]);

  // Check for cosigner alert condition
  useEffect(() => {
    if (formData.bank_deposit_type === 'No deposito directo' && formData.has_poi && formData.poi_type === 'Cash') {
      setShowCosignerAlert(true);
    } else {
      setShowCosignerAlert(false);
    }
  }, [formData.bank_deposit_type, formData.has_poi, formData.poi_type]);

  const fetchComments = async () => {
    if (!record?.id) return;
    setLoadingComments(true);
    try {
      const response = await axios.get(`${API}/user-records/${record.id}/comments`);
      setComments(response.data);
    } catch (error) {
      console.error('Failed to fetch comments:', error);
    } finally {
      setLoadingComments(false);
    }
  };

  const handleAddComment = async () => {
    if (!newComment.trim() || !record?.id) return;
    try {
      const formDataObj = new FormData();
      formDataObj.append('comment', newComment.trim());
      const response = await axios.post(`${API}/user-records/${record.id}/comments`, formDataObj);
      setComments([response.data, ...comments]);
      setNewComment('');
      toast.success('Comentario agregado');
    } catch (error) {
      toast.error('Error al agregar comentario');
    }
  };

  const handleDeleteComment = async (commentId) => {
    try {
      await axios.delete(`${API}/user-records/${record.id}/comments/${commentId}`);
      setComments(comments.filter(c => c.id !== commentId));
      toast.success('Comentario eliminado');
    } catch (error) {
      toast.error('Error al eliminar comentario');
    }
  };

  const handlePorTypeToggle = (type) => {
    const current = formData.por_types || [];
    if (current.includes(type)) {
      setFormData({ ...formData, por_types: current.filter(t => t !== type) });
    } else {
      setFormData({ ...formData, por_types: [...current, type] });
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const dataToSave = {
        ...formData,
        client_id: clientId || formData.client_id,
        // Convert legacy fields
        dl: formData.has_id,
        checks: formData.has_poi
      };
      await onSave(dataToSave);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Cosigner Alert */}
      {showCosignerAlert && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-amber-600 mt-0.5" />
          <div>
            <p className="font-medium text-amber-800">Atención</p>
            <p className="text-sm text-amber-700">
              Va a necesitar un Cosigner o probar ingreso adicional.
            </p>
          </div>
        </div>
      )}

      {/* ID Section */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <Checkbox
            checked={formData.has_id}
            onCheckedChange={(checked) => setFormData({ ...formData, has_id: checked, id_type: checked ? formData.id_type : '' })}
            id="has_id"
          />
          <Label htmlFor="has_id" className="font-medium">ID</Label>
        </div>
        {formData.has_id && (
          <Select value={formData.id_type} onValueChange={(value) => setFormData({ ...formData, id_type: value })}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Seleccionar tipo de ID" />
            </SelectTrigger>
            <SelectContent>
              {(configLists.id_type || []).map((item) => (
                <SelectItem key={item.id} value={item.name}>{item.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* POI Section (Proof of Income) */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <Checkbox
            checked={formData.has_poi}
            onCheckedChange={(checked) => setFormData({ ...formData, has_poi: checked, poi_type: checked ? formData.poi_type : '' })}
            id="has_poi"
          />
          <Label htmlFor="has_poi" className="font-medium">POI (Proof of Income)</Label>
        </div>
        {formData.has_poi && (
          <Select value={formData.poi_type} onValueChange={(value) => setFormData({ ...formData, poi_type: value })}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Seleccionar tipo de POI" />
            </SelectTrigger>
            <SelectContent>
              {(configLists.poi_type || []).map((item) => (
                <SelectItem key={item.id} value={item.name}>{item.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* Other Checkboxes Row */}
      <div className="flex flex-wrap gap-6">
        <div className="flex items-center gap-2">
          <Checkbox
            checked={formData.ssn}
            onCheckedChange={(checked) => setFormData({ ...formData, ssn: checked })}
            id="ssn"
          />
          <Label htmlFor="ssn">SSN</Label>
        </div>
        <div className="flex items-center gap-2">
          <Checkbox
            checked={formData.itin}
            onCheckedChange={(checked) => setFormData({ ...formData, itin: checked })}
            id="itin"
          />
          <Label htmlFor="itin">ITIN</Label>
        </div>
        <div className="flex items-center gap-2">
          <Checkbox
            checked={formData.self_employed}
            onCheckedChange={(checked) => setFormData({ ...formData, self_employed: checked })}
            id="self_employed"
          />
          <Label htmlFor="self_employed">Self Employed</Label>
        </div>
      </div>

      {/* POR Section (Proof of Residence) */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <Checkbox
            checked={formData.has_por}
            onCheckedChange={(checked) => setFormData({ ...formData, has_por: checked, por_types: checked ? formData.por_types : [] })}
            id="has_por"
          />
          <Label htmlFor="has_por" className="font-medium">POR (Proof of Residence)</Label>
        </div>
        {formData.has_por && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 ml-6">
            {(configLists.por_type || []).map((item) => (
              <div key={item.id} className="flex items-center gap-2">
                <Checkbox
                  checked={(formData.por_types || []).includes(item.name)}
                  onCheckedChange={() => handlePorTypeToggle(item.name)}
                  id={`por_${item.id}`}
                />
                <Label htmlFor={`por_${item.id}`} className="text-sm">{item.name}</Label>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Bank Section */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <Label className="form-label">Bank</Label>
          <Select value={formData.bank} onValueChange={(value) => setFormData({ ...formData, bank: value })}>
            <SelectTrigger>
              <SelectValue placeholder="Seleccionar banco" />
            </SelectTrigger>
            <SelectContent>
              {(configLists.bank || []).map((item) => (
                <SelectItem key={item.id} value={item.name}>{item.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label className="form-label">Tipo de Depósito</Label>
          <Select value={formData.bank_deposit_type} onValueChange={(value) => setFormData({ ...formData, bank_deposit_type: value })}>
            <SelectTrigger>
              <SelectValue placeholder="Seleccionar tipo" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Deposito Directo">Deposito Directo</SelectItem>
              <SelectItem value="No deposito directo">No deposito directo</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Auto, Credit, Auto Loan */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <Label className="form-label">Auto</Label>
          <Select value={formData.auto} onValueChange={(value) => setFormData({ ...formData, auto: value })}>
            <SelectTrigger>
              <SelectValue placeholder="Seleccionar auto" />
            </SelectTrigger>
            <SelectContent>
              {(configLists.car || []).map((item) => (
                <SelectItem key={item.id} value={item.name}>{item.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label className="form-label">Credit</Label>
          <Input
            value={formData.credit}
            onChange={(e) => setFormData({ ...formData, credit: e.target.value })}
            placeholder="Score"
          />
        </div>
        <div>
          <Label className="form-label">Auto Loan</Label>
          <Input
            value={formData.auto_loan}
            onChange={(e) => setFormData({ ...formData, auto_loan: e.target.value })}
            placeholder="Monto"
          />
        </div>
      </div>

      {/* Down Payment Section */}
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-base flex items-center gap-2">
            <DollarSign className="w-4 h-4" />
            Down Payment
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-4">
            {['Cash', 'Tarjeta', 'Trade'].map((type) => (
              <div key={type} className="flex items-center gap-2">
                <Checkbox
                  checked={formData.down_payment_type === type}
                  onCheckedChange={(checked) => setFormData({ 
                    ...formData, 
                    down_payment_type: checked ? type : '',
                    down_payment_cash: type !== 'Cash' ? '' : formData.down_payment_cash,
                    down_payment_card: type !== 'Tarjeta' ? '' : formData.down_payment_card
                  })}
                  id={`dp_${type}`}
                />
                <Label htmlFor={`dp_${type}`}>{type}</Label>
              </div>
            ))}
          </div>

          {formData.down_payment_type === 'Cash' && (
            <div>
              <Label className="form-label">Monto en Cash</Label>
              <Input
                type="text"
                value={formData.down_payment_cash}
                onChange={(e) => setFormData({ ...formData, down_payment_cash: e.target.value })}
                placeholder="$0.00"
              />
            </div>
          )}

          {formData.down_payment_type === 'Tarjeta' && (
            <div>
              <Label className="form-label">Monto en Tarjeta</Label>
              <Input
                type="text"
                value={formData.down_payment_card}
                onChange={(e) => setFormData({ ...formData, down_payment_card: e.target.value })}
                placeholder="$0.00"
              />
            </div>
          )}

          {formData.down_payment_type === 'Trade' && (
            <div className="space-y-4 p-4 bg-slate-50 rounded-lg">
              <h4 className="font-medium flex items-center gap-2">
                <Car className="w-4 h-4" />
                Vehículo en Trade
              </h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div>
                  <Label className="form-label text-xs">Make</Label>
                  <Input
                    value={formData.trade_make}
                    onChange={(e) => setFormData({ ...formData, trade_make: e.target.value })}
                    placeholder="Marca"
                  />
                </div>
                <div>
                  <Label className="form-label text-xs">Model</Label>
                  <Input
                    value={formData.trade_model}
                    onChange={(e) => setFormData({ ...formData, trade_model: e.target.value })}
                    placeholder="Modelo"
                  />
                </div>
                <div>
                  <Label className="form-label text-xs">Year</Label>
                  <Input
                    value={formData.trade_year}
                    onChange={(e) => setFormData({ ...formData, trade_year: e.target.value })}
                    placeholder="Año"
                  />
                </div>
                <div>
                  <Label className="form-label text-xs">Title</Label>
                  <Select value={formData.trade_title} onValueChange={(value) => setFormData({ ...formData, trade_title: value })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Título" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Clean Title">Clean Title</SelectItem>
                      <SelectItem value="Salvaged">Salvaged</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label className="form-label text-xs">Miles</Label>
                  <Input
                    value={formData.trade_miles}
                    onChange={(e) => setFormData({ ...formData, trade_miles: e.target.value })}
                    placeholder="Millas"
                  />
                </div>
                <div>
                  <Label className="form-label text-xs">Plate</Label>
                  <Select value={formData.trade_plate} onValueChange={(value) => setFormData({ ...formData, trade_plate: value })}>
                    <SelectTrigger>
                      <SelectValue placeholder="Estado" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="CA">CA</SelectItem>
                      <SelectItem value="Out of State">Out of State</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="col-span-2 sm:col-span-3">
                  <Label className="form-label text-xs">Estimated Value</Label>
                  <Input
                    value={formData.trade_estimated_value}
                    onChange={(e) => setFormData({ ...formData, trade_estimated_value: e.target.value })}
                    placeholder="$0.00"
                  />
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dealer */}
      <div>
        <Label className="form-label">Dealer</Label>
        <Select value={formData.dealer} onValueChange={(value) => setFormData({ ...formData, dealer: value })}>
          <SelectTrigger>
            <SelectValue placeholder="Seleccionar dealer" />
          </SelectTrigger>
          <SelectContent>
            {(configLists.dealer || []).map((item) => (
              <SelectItem key={item.id} value={item.name}>{item.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Finance Status */}
      <div>
        <Label className="form-label">Finance Status</Label>
        <Select value={formData.finance_status} onValueChange={(value) => setFormData({ ...formData, finance_status: value })}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="no">No</SelectItem>
            <SelectItem value="financiado">Financiado</SelectItem>
            <SelectItem value="lease">Lease</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Vehicle Info (when financiado or lease) */}
      {(formData.finance_status === 'financiado' || formData.finance_status === 'lease') && (
        <div className="grid grid-cols-2 gap-4 p-4 bg-blue-50 rounded-lg">
          <div>
            <Label className="form-label">Vehicle Make</Label>
            <Input
              value={formData.vehicle_make}
              onChange={(e) => setFormData({ ...formData, vehicle_make: e.target.value })}
            />
          </div>
          <div>
            <Label className="form-label">Vehicle Year</Label>
            <Input
              value={formData.vehicle_year}
              onChange={(e) => setFormData({ ...formData, vehicle_year: e.target.value })}
            />
          </div>
          <div>
            <Label className="form-label">Sale Month</Label>
            <Input
              type="number"
              min="1"
              max="12"
              value={formData.sale_month}
              onChange={(e) => setFormData({ ...formData, sale_month: e.target.value })}
            />
          </div>
          <div>
            <Label className="form-label">Sale Year</Label>
            <Input
              type="number"
              value={formData.sale_year}
              onChange={(e) => setFormData({ ...formData, sale_year: e.target.value })}
            />
          </div>
        </div>
      )}

      {/* Comments Section (only for existing records) */}
      {record?.id && (
        <div className="border-t pt-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowComments(!showComments)}
            className="mb-3"
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            Comentarios ({comments.length})
          </Button>

          {showComments && (
            <div className="space-y-3">
              <div className="flex gap-2">
                <Textarea
                  value={newComment}
                  onChange={(e) => setNewComment(e.target.value)}
                  placeholder="Escribir comentario..."
                  rows={2}
                  className="flex-1"
                />
                <Button onClick={handleAddComment} disabled={!newComment.trim()}>
                  <Plus className="w-4 h-4" />
                </Button>
              </div>

              {loadingComments ? (
                <div className="text-center py-4">
                  <Loader2 className="w-4 h-4 animate-spin mx-auto" />
                </div>
              ) : comments.length === 0 ? (
                <p className="text-sm text-slate-400 text-center py-4">No hay comentarios</p>
              ) : (
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {comments.map((comment) => (
                    <div key={comment.id} className="bg-slate-50 rounded-lg p-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <p className="text-sm">{comment.comment}</p>
                          <p className="text-xs text-slate-400 mt-1">
                            <span className="font-medium">{comment.user_name}</span>
                            {' · '}
                            {format(parseISO(comment.created_at), 'dd/MM/yyyy HH:mm')}
                          </p>
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDeleteComment(comment.id)}
                          className="text-red-500 hover:text-red-700"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex justify-end gap-3 pt-4 border-t">
        <Button variant="outline" onClick={onCancel}>
          Cancelar
        </Button>
        <Button onClick={handleSave} disabled={saving}>
          {saving ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Guardando...
            </>
          ) : (
            'Guardar'
          )}
        </Button>
      </div>
    </div>
  );
}
