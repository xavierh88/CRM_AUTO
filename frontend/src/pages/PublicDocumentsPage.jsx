import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { toast, Toaster } from 'sonner';
import { Upload, FileText, CheckCircle2, AlertCircle, Car, Loader2 } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function PublicDocumentsPage() {
  const { token } = useParams();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [clientInfo, setClientInfo] = useState(null);
  const [error, setError] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  
  // File states
  const [idFile, setIdFile] = useState(null);
  const [incomeFile, setIncomeFile] = useState(null);
  const [idPreview, setIdPreview] = useState(null);
  const [incomePreview, setIncomePreview] = useState(null);

  useEffect(() => {
    validateToken();
  }, [token]);

  const validateToken = async () => {
    try {
      const response = await axios.get(`${API}/public/documents/${token}`);
      setClientInfo(response.data);
      if (response.data.documents_submitted) {
        setSubmitted(true);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Link inválido o expirado');
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e, type) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      toast.error('El archivo es muy grande. Máximo 10MB');
      return;
    }

    // Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Tipo de archivo no permitido. Use JPG, PNG, WEBP o PDF');
      return;
    }

    if (type === 'id') {
      setIdFile(file);
      if (file.type.startsWith('image/')) {
        setIdPreview(URL.createObjectURL(file));
      } else {
        setIdPreview(null);
      }
    } else {
      setIncomeFile(file);
      if (file.type.startsWith('image/')) {
        setIncomePreview(URL.createObjectURL(file));
      } else {
        setIncomePreview(null);
      }
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!idFile) {
      toast.error('Por favor suba su identificación (ID)');
      return;
    }

    setSubmitting(true);
    
    try {
      const formData = new FormData();
      formData.append('id_document', idFile);
      if (incomeFile) {
        formData.append('income_proof', incomeFile);
      }

      await axios.post(`${API}/public/documents/${token}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setSubmitted(true);
      toast.success('¡Documentos enviados exitosamente!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al enviar documentos');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-slate-100 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-slate-100 flex items-center justify-center p-4">
        <Card className="max-w-md w-full">
          <CardContent className="pt-6 text-center">
            <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-slate-800 mb-2">Link Inválido</h2>
            <p className="text-slate-600">{error}</p>
            <p className="text-sm text-slate-400 mt-4">
              Por favor contacte a su vendedor para obtener un nuevo link.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (submitted) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-green-50 to-slate-100 flex items-center justify-center p-4">
        <Card className="max-w-md w-full">
          <CardContent className="pt-6 text-center">
            <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-slate-800 mb-2">¡Documentos Recibidos!</h2>
            <p className="text-slate-600">
              Gracias {clientInfo?.first_name}, hemos recibido sus documentos correctamente.
            </p>
            <p className="text-sm text-slate-400 mt-4">
              Nuestro equipo revisará la información y le contactaremos pronto.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-slate-100 py-8 px-4">
      <Toaster position="top-center" richColors />
      
      <div className="max-w-lg mx-auto">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="w-16 h-16 bg-blue-600 rounded-full flex items-center justify-center mx-auto mb-4">
            <Car className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-slate-800">DealerCRM</h1>
          <p className="text-slate-500">Suba sus documentos</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-600" />
              Documentos Requeridos
            </CardTitle>
            <CardDescription>
              Hola <strong>{clientInfo?.first_name}</strong>, por favor suba los siguientes documentos para continuar con su proceso.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* ID Document */}
              <div className="space-y-2">
                <Label htmlFor="id-upload" className="flex items-center gap-2">
                  <span className="bg-red-100 text-red-600 px-2 py-0.5 rounded text-xs font-medium">Requerido</span>
                  Identificación (ID / Licencia de Conducir)
                </Label>
                <div className="border-2 border-dashed border-slate-200 rounded-lg p-4 hover:border-blue-400 transition-colors">
                  <Input
                    id="id-upload"
                    type="file"
                    accept="image/*,.pdf"
                    onChange={(e) => handleFileChange(e, 'id')}
                    className="hidden"
                  />
                  <label htmlFor="id-upload" className="cursor-pointer block text-center">
                    {idFile ? (
                      <div className="space-y-2">
                        {idPreview && (
                          <img src={idPreview} alt="ID Preview" className="max-h-32 mx-auto rounded" />
                        )}
                        <p className="text-sm text-green-600 font-medium flex items-center justify-center gap-1">
                          <CheckCircle2 className="w-4 h-4" />
                          {idFile.name}
                        </p>
                        <p className="text-xs text-slate-400">Click para cambiar</p>
                      </div>
                    ) : (
                      <div className="py-4">
                        <Upload className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                        <p className="text-sm text-slate-500">Click para subir su ID</p>
                        <p className="text-xs text-slate-400">JPG, PNG, WEBP o PDF (máx. 10MB)</p>
                      </div>
                    )}
                  </label>
                </div>
              </div>

              {/* Income Proof */}
              <div className="space-y-2">
                <Label htmlFor="income-upload" className="flex items-center gap-2">
                  <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-xs font-medium">Opcional</span>
                  Comprobante de Ingresos (Pay Stub / Tax Return)
                </Label>
                <div className="border-2 border-dashed border-slate-200 rounded-lg p-4 hover:border-blue-400 transition-colors">
                  <Input
                    id="income-upload"
                    type="file"
                    accept="image/*,.pdf"
                    onChange={(e) => handleFileChange(e, 'income')}
                    className="hidden"
                  />
                  <label htmlFor="income-upload" className="cursor-pointer block text-center">
                    {incomeFile ? (
                      <div className="space-y-2">
                        {incomePreview && (
                          <img src={incomePreview} alt="Income Preview" className="max-h-32 mx-auto rounded" />
                        )}
                        <p className="text-sm text-green-600 font-medium flex items-center justify-center gap-1">
                          <CheckCircle2 className="w-4 h-4" />
                          {incomeFile.name}
                        </p>
                        <p className="text-xs text-slate-400">Click para cambiar</p>
                      </div>
                    ) : (
                      <div className="py-4">
                        <Upload className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                        <p className="text-sm text-slate-500">Click para subir comprobante</p>
                        <p className="text-xs text-slate-400">JPG, PNG, WEBP o PDF (máx. 10MB)</p>
                      </div>
                    )}
                  </label>
                </div>
              </div>

              {/* Submit Button */}
              <Button 
                type="submit" 
                className="w-full" 
                size="lg"
                disabled={submitting || !idFile}
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    Enviando...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2" />
                    Enviar Documentos
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-xs text-slate-400 mt-6">
          Sus documentos están protegidos y solo serán utilizados para su proceso de compra.
        </p>
      </div>
    </div>
  );
}
