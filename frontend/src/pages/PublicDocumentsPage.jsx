import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast, Toaster } from 'sonner';
import { Upload, FileText, CheckCircle2, AlertCircle, Car, Loader2, Globe, Image, File } from 'lucide-react';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Translations
const translations = {
  en: {
    title: "CARPLUS AUTOSALE",
    subtitle: "Upload your documents",
    requiredDocuments: "Required Documents",
    hello: "Hello",
    uploadInstructions: "please upload the following documents to continue with your process.",
    required: "Required",
    optional: "Optional",
    idLabel: "ID / Driver's License",
    incomeLabel: "Proof of Income (Pay Stub / Tax Return)",
    residenceLabel: "Proof of Residence (Utility Bill / Bank Statement)",
    clickToUpload: "Click to upload your",
    id: "ID",
    incomeProof: "income proof",
    residenceProof: "residence proof",
    allowedFormats: "JPG, PNG, WEBP or PDF (max. 10MB per file)",
    multipleFiles: "You can upload multiple files - they will be combined into one PDF",
    clickToChange: "Click to change",
    filesSelected: "files selected",
    submitDocuments: "Submit Documents",
    submitting: "Submitting...",
    // Messages
    invalidLink: "Invalid Link",
    invalidLinkDesc: "Invalid or expired link",
    contactSalesperson: "Please contact your salesperson to get a new link.",
    documentsReceived: "Documents Received!",
    thankYou: "Thank you",
    documentsReceivedDesc: "we have received your documents successfully.",
    teamWillReview: "Our team will review the information and contact you soon.",
    privacyNote: "Your documents are protected and will only be used for your purchase process.",
    // Errors
    fileTooLarge: "File is too large. Maximum 10MB per file",
    invalidFileType: "Invalid file type. Use JPG, PNG, WEBP or PDF",
    pleaseUploadId: "Please upload your ID",
    errorSubmitting: "Error submitting documents",
    successSubmit: "Documents submitted successfully!",
    // Language
    languagePreference: "Language Preference",
    languageNote: "This also indicates your preferred language",
    english: "English",
    spanish: "Spanish"
  },
  es: {
    title: "CARPLUS AUTOSALE",
    subtitle: "Suba sus documentos",
    requiredDocuments: "Documentos Requeridos",
    hello: "Hola",
    uploadInstructions: "por favor suba los siguientes documentos para continuar con su proceso.",
    required: "Requerido",
    optional: "Opcional",
    idLabel: "Identificación (ID / Licencia de Conducir)",
    incomeLabel: "Comprobante de Ingresos (Pay Stub / Tax Return)",
    residenceLabel: "Comprobante de Residencia (Factura de Servicios / Estado de Cuenta)",
    clickToUpload: "Click para subir su",
    id: "ID",
    incomeProof: "comprobante de ingresos",
    residenceProof: "comprobante de residencia",
    allowedFormats: "JPG, PNG, WEBP o PDF (máx. 10MB por archivo)",
    multipleFiles: "Puede subir múltiples archivos - se combinarán en un solo PDF",
    clickToChange: "Click para cambiar",
    filesSelected: "archivos seleccionados",
    submitDocuments: "Enviar Documentos",
    submitting: "Enviando...",
    // Messages
    invalidLink: "Link Inválido",
    invalidLinkDesc: "Link inválido o expirado",
    contactSalesperson: "Por favor contacte a su vendedor para obtener un nuevo link.",
    documentsReceived: "¡Documentos Recibidos!",
    thankYou: "Gracias",
    documentsReceivedDesc: "hemos recibido sus documentos correctamente.",
    teamWillReview: "Nuestro equipo revisará la información y le contactaremos pronto.",
    privacyNote: "Sus documentos están protegidos y solo serán utilizados para su proceso de compra.",
    // Errors
    fileTooLarge: "El archivo es muy grande. Máximo 10MB por archivo",
    invalidFileType: "Tipo de archivo no permitido. Use JPG, PNG, WEBP o PDF",
    pleaseUploadId: "Por favor suba su identificación (ID)",
    errorSubmitting: "Error al enviar documentos",
    successSubmit: "¡Documentos enviados exitosamente!",
    // Language
    languagePreference: "Preferencia de Idioma",
    languageNote: "Esto también indica su idioma preferido",
    english: "Inglés",
    spanish: "Español"
  }
};

export default function PublicDocumentsPage() {
  const { token } = useParams();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [clientInfo, setClientInfo] = useState(null);
  const [error, setError] = useState(null);
  const [submitted, setSubmitted] = useState(false);
  
  // Language - default English
  const [language, setLanguage] = useState('en');
  const t = translations[language];
  
  // File states - now arrays for multiple files
  const [idFiles, setIdFiles] = useState([]);
  const [incomeFiles, setIncomeFiles] = useState([]);
  const [residenceFiles, setResidenceFiles] = useState([]);

  useEffect(() => {
    validateToken();
  }, [token]);

  const validateToken = async () => {
    try {
      const response = await axios.get(`${API}/public/documents/${token}`);
      setClientInfo(response.data);
      
      // Set language from saved preference if available
      if (response.data.preferred_language) {
        setLanguage(response.data.preferred_language);
      }
      
      if (response.data.documents_submitted) {
        setSubmitted(true);
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid or expired link');
    } finally {
      setLoading(false);
    }
  };

  const handleLanguageChange = async (newLang) => {
    setLanguage(newLang);
    
    // Save language preference to backend
    try {
      await axios.put(`${API}/public/documents/${token}/language`, {
        language: newLang
      });
    } catch (err) {
      console.error('Failed to save language preference:', err);
    }
  };

  const handleFileChange = (e, type) => {
    const files = Array.from(e.target.files);
    if (!files.length) return;

    // Validate each file
    const validFiles = [];
    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf'];
    
    for (const file of files) {
      // Validate file size (max 10MB per file)
      if (file.size > 10 * 1024 * 1024) {
        toast.error(`${file.name}: ${t.fileTooLarge}`);
        continue;
      }

      // Validate file type
      if (!allowedTypes.includes(file.type)) {
        toast.error(`${file.name}: ${t.invalidFileType}`);
        continue;
      }
      
      validFiles.push(file);
    }

    if (type === 'id') {
      setIdFiles(prev => [...prev, ...validFiles]);
    } else if (type === 'income') {
      setIncomeFiles(prev => [...prev, ...validFiles]);
    } else if (type === 'residence') {
      setResidenceFiles(prev => [...prev, ...validFiles]);
    }
  };

  const removeFile = (type, index) => {
    if (type === 'id') {
      setIdFiles(prev => prev.filter((_, i) => i !== index));
    } else if (type === 'income') {
      setIncomeFiles(prev => prev.filter((_, i) => i !== index));
    } else if (type === 'residence') {
      setResidenceFiles(prev => prev.filter((_, i) => i !== index));
    }
  };

  const getFileIcon = (file) => {
    if (!file) return null;
    if (file.type === 'application/pdf') {
      return <File className="w-6 h-6 text-red-500" />;
    }
    return <Image className="w-6 h-6 text-blue-500" />;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (idFiles.length === 0) {
      toast.error(t.pleaseUploadId);
      return;
    }

    setSubmitting(true);
    
    try {
      const formData = new FormData();
      
      // Append all ID files
      idFiles.forEach((file, index) => {
        formData.append('id_documents', file);
      });
      
      // Append all income files
      incomeFiles.forEach((file, index) => {
        formData.append('income_documents', file);
      });
      
      // Append all residence files
      residenceFiles.forEach((file, index) => {
        formData.append('residence_documents', file);
      });
      
      formData.append('language', language);

      await axios.post(`${API}/public/documents/${token}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      setSubmitted(true);
      toast.success(t.successSubmit);
    } catch (err) {
      toast.error(err.response?.data?.detail || t.errorSubmitting);
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
            <h2 className="text-xl font-semibold text-slate-800 mb-2">{t.invalidLink}</h2>
            <p className="text-slate-600">{t.invalidLinkDesc}</p>
            <p className="text-sm text-slate-400 mt-4">{t.contactSalesperson}</p>
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
            <h2 className="text-xl font-semibold text-slate-800 mb-2">{t.documentsReceived}</h2>
            <p className="text-slate-600">
              {t.thankYou} {clientInfo?.first_name}, {t.documentsReceivedDesc}
            </p>
            <p className="text-sm text-slate-400 mt-4">{t.teamWillReview}</p>
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
          <img src="/logo.png" alt="CARPLUS AUTOSALE" className="w-20 h-20 object-contain mx-auto mb-3" />
          <h1 className="text-2xl font-bold text-slate-800">{t.title}</h1>
          <p className="text-red-500 font-semibold text-sm">Friendly Brokerage</p>
          <p className="text-slate-500 mt-1">{t.subtitle}</p>
        </div>

        {/* Language Selector */}
        <Card className="mb-4">
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Globe className="w-5 h-5 text-blue-600" />
                <div>
                  <p className="font-medium text-sm text-slate-700">{t.languagePreference}</p>
                  <p className="text-xs text-slate-400">{t.languageNote}</p>
                </div>
              </div>
              <Select value={language} onValueChange={handleLanguageChange}>
                <SelectTrigger className="w-32">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="en">🇺🇸 {t.english}</SelectItem>
                  <SelectItem value="es">🇲🇽 {t.spanish}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5 text-blue-600" />
              {t.requiredDocuments}
            </CardTitle>
            <CardDescription>
              {t.hello} <strong>{clientInfo?.first_name}</strong>, {t.uploadInstructions}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-6">
              {/* ID Document */}
              <div className="space-y-2">
                <Label htmlFor="id-upload" className="flex items-center gap-2">
                  <span className="bg-red-100 text-red-600 px-2 py-0.5 rounded text-xs font-medium">{t.required}</span>
                  {t.idLabel}
                </Label>
                <div className="border-2 border-dashed border-slate-200 rounded-lg p-4 hover:border-blue-400 transition-colors">
                  <Input
                    id="id-upload"
                    type="file"
                    accept="image/jpeg,image/png,image/webp,application/pdf"
                    onChange={(e) => handleFileChange(e, 'id')}
                    className="hidden"
                    multiple
                  />
                  <label htmlFor="id-upload" className="cursor-pointer block text-center">
                    {idFiles.length > 0 ? (
                      <div className="space-y-2">
                        <div className="flex flex-wrap gap-2 justify-center">
                          {idFiles.map((file, idx) => (
                            <div key={idx} className="flex items-center gap-1 bg-green-50 px-2 py-1 rounded text-sm">
                              {getFileIcon(file)}
                              <span className="text-green-700 max-w-[100px] truncate">{file.name}</span>
                              <button 
                                type="button"
                                onClick={(e) => { e.preventDefault(); removeFile('id', idx); }}
                                className="text-red-500 hover:text-red-700 ml-1"
                              >×</button>
                            </div>
                          ))}
                        </div>
                        <p className="text-xs text-green-600">{idFiles.length} {t.filesSelected}</p>
                        <p className="text-xs text-slate-400">{t.clickToUpload} más archivos</p>
                      </div>
                    ) : (
                      <div className="py-4">
                        <Upload className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                        <p className="text-sm text-slate-500">{t.clickToUpload} {t.id}</p>
                        <p className="text-xs text-slate-400">{t.allowedFormats}</p>
                        <p className="text-xs text-blue-500 mt-1">{t.multipleFiles}</p>
                      </div>
                    )}
                  </label>
                </div>
              </div>

              {/* Income Proof */}
              <div className="space-y-2">
                <Label htmlFor="income-upload" className="flex items-center gap-2">
                  <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-xs font-medium">{t.optional}</span>
                  {t.incomeLabel}
                </Label>
                <div className="border-2 border-dashed border-slate-200 rounded-lg p-4 hover:border-blue-400 transition-colors">
                  <Input
                    id="income-upload"
                    type="file"
                    accept="image/jpeg,image/png,image/webp,application/pdf"
                    onChange={(e) => handleFileChange(e, 'income')}
                    className="hidden"
                    multiple
                  />
                  <label htmlFor="income-upload" className="cursor-pointer block text-center">
                    {incomeFiles.length > 0 ? (
                      <div className="space-y-2">
                        <div className="flex flex-wrap gap-2 justify-center">
                          {incomeFiles.map((file, idx) => (
                            <div key={idx} className="flex items-center gap-1 bg-green-50 px-2 py-1 rounded text-sm">
                              {getFileIcon(file)}
                              <span className="text-green-700 max-w-[100px] truncate">{file.name}</span>
                              <button 
                                type="button"
                                onClick={(e) => { e.preventDefault(); removeFile('income', idx); }}
                                className="text-red-500 hover:text-red-700 ml-1"
                              >×</button>
                            </div>
                          ))}
                        </div>
                        <p className="text-xs text-green-600">{incomeFiles.length} {t.filesSelected}</p>
                        <p className="text-xs text-slate-400">{t.clickToUpload} más archivos</p>
                      </div>
                    ) : (
                      <div className="py-4">
                        <Upload className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                        <p className="text-sm text-slate-500">{t.clickToUpload} {t.incomeProof}</p>
                        <p className="text-xs text-slate-400">{t.allowedFormats}</p>
                        <p className="text-xs text-blue-500 mt-1">{t.multipleFiles}</p>
                      </div>
                    )}
                  </label>
                </div>
              </div>

              {/* Residence Proof - NEW */}
              <div className="space-y-2">
                <Label htmlFor="residence-upload" className="flex items-center gap-2">
                  <span className="bg-slate-100 text-slate-600 px-2 py-0.5 rounded text-xs font-medium">{t.optional}</span>
                  {t.residenceLabel}
                </Label>
                <div className="border-2 border-dashed border-slate-200 rounded-lg p-4 hover:border-blue-400 transition-colors">
                  <Input
                    id="residence-upload"
                    type="file"
                    accept="image/jpeg,image/png,image/webp,application/pdf"
                    onChange={(e) => handleFileChange(e, 'residence')}
                    className="hidden"
                    multiple
                  />
                  <label htmlFor="residence-upload" className="cursor-pointer block text-center">
                    {residenceFiles.length > 0 ? (
                      <div className="space-y-2">
                        <div className="flex flex-wrap gap-2 justify-center">
                          {residenceFiles.map((file, idx) => (
                            <div key={idx} className="flex items-center gap-1 bg-green-50 px-2 py-1 rounded text-sm">
                              {getFileIcon(file)}
                              <span className="text-green-700 max-w-[100px] truncate">{file.name}</span>
                              <button 
                                type="button"
                                onClick={(e) => { e.preventDefault(); removeFile('residence', idx); }}
                                className="text-red-500 hover:text-red-700 ml-1"
                              >×</button>
                            </div>
                          ))}
                        </div>
                        <p className="text-xs text-green-600">{residenceFiles.length} {t.filesSelected}</p>
                        <p className="text-xs text-slate-400">{t.clickToUpload} más archivos</p>
                      </div>
                    ) : (
                      <div className="py-4">
                        <Upload className="w-10 h-10 text-slate-300 mx-auto mb-2" />
                        <p className="text-sm text-slate-500">{t.clickToUpload} {t.residenceProof}</p>
                        <p className="text-xs text-slate-400">{t.allowedFormats}</p>
                        <p className="text-xs text-blue-500 mt-1">{t.multipleFiles}</p>
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
                disabled={submitting || idFiles.length === 0}
              >
                {submitting ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    {t.submitting}
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2" />
                    {t.submitDocuments}
                  </>
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Footer */}
        <p className="text-center text-xs text-slate-400 mt-6">{t.privacyNote}</p>
      </div>
    </div>
  );
}
