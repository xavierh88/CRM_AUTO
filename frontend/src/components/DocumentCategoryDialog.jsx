import { useState, useEffect, useCallback } from 'react';
import { 
  X, Upload, Download, Eye, Trash2, FileText, Image, 
  AlertCircle, CheckCircle, ChevronDown, ChevronUp, MoreHorizontal
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';
import axios from 'axios';

const API = '/api';

const CATEGORY_CONFIG = {
  id: { labelKey: 'documents.id', label: 'Identificación', icon: FileText, color: 'blue' },
  income: { labelKey: 'documents.income', label: 'Comprobante de Ingresos', icon: FileText, color: 'emerald' },
  residence: { labelKey: 'documents.residence', label: 'Comprobante de Residencia', icon: FileText, color: 'amber' }
};

function formatFileSize(bytes) {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  try {
    return new Date(dateStr).toLocaleDateString('es-ES', {
      day: '2-digit', month: 'short', year: 'numeric'
    });
  } catch {
    return dateStr;
  }
}

function getFileType(filename, mimeType) {
  if (mimeType) {
    if (['image/jpeg', 'image/jpg', 'image/png', 'image/webp'].includes(mimeType)) return 'image';
    if (mimeType === 'application/pdf') return 'pdf';
  }
  const ext = filename?.split('.').pop()?.toLowerCase();
  if (['jpg', 'jpeg', 'png', 'webp'].includes(ext)) return 'image';
  if (ext === 'pdf') return 'pdf';
  return 'other';
}

function getFileIcon(type, mimeType) {
  if (type === 'image') return Image;
  if (type === 'pdf') return FileText;
  return FileText;
}

export default function DocumentCategoryDialog({ 
  isOpen, 
  onClose, 
  clientId, 
  clientName,
  category,
  onUploadComplete,
  onPreview
}) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [expandedDoc, setExpandedDoc] = useState(null);

  const config = CATEGORY_CONFIG[category] || { label: category, icon: FileText, color: 'slate' };
  const CategoryIcon = config.icon;
  const displayLimit = showAll ? documents.length : Math.min(documents.length, 5);

  const fetchDocuments = useCallback(async () => {
    if (!clientId) return;
    setLoading(true);
    try {
      const response = await axios.get(`${API}/clients/${clientId}/documents/list/${category}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      setDocuments((response.data.documents || []).map(d => ({ ...d, client_id: clientId, doc_type: category })));
    } catch (err) {
      console.error('Failed to load documents:', err);
      toast.error('Error al cargar documentos');
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, [clientId, category]);

  useEffect(() => {
    if (isOpen) {
      fetchDocuments();
      setShowAll(false);
      setExpandedDoc(null);
    }
  }, [isOpen, fetchDocuments]);

  const handleUpload = async (files) => {
    if (!files || files.length === 0) return;
    
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('doc_type', category);
      Array.from(files).forEach(file => formData.append('files', file));

      const response = await axios.post(
        `${API}/clients/${clientId}/documents/upload`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data', 'Authorization': `Bearer ${localStorage.getItem('token')}` } }
      );

      toast.success(`${response.data.files?.length || 1} documento(s) subido(s)`);
      await fetchDocuments();
      if (onUploadComplete) onUploadComplete();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al subir documento');
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (docId) => {
    if (!window.confirm('¿Eliminar este documento?')) return;
    
    try {
      await axios.delete(`${API}/clients/${clientId}/documents/${category}/${docId}`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      toast.success('Documento eliminado');
      await fetchDocuments();
      if (onUploadComplete) onUploadComplete();
    } catch (err) {
      toast.error('Error al eliminar');
    }
  };

  const handleDownload = async (doc) => {
    try {
      let url = `${API}/clients/${clientId}/documents/download/${category}`;
      if (doc.id && doc.id !== 'legacy') {
        url += `?doc_id=${doc.id}`;
      }

      const response = await axios.get(url, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` },
        responseType: 'blob'
      });

      const blob = new Blob([response.data], { type: response.data?.type || doc.type || 'application/octet-stream' });
      const reader = new FileReader();
      reader.onload = () => {
        const link = document.createElement('a');
        link.href = reader.result;
        link.download = doc.original_name || doc.filename || `documento_${category}`;
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        link.remove();
        toast.success('Descarga iniciada');
      };
      reader.onerror = () => toast.error('Error al preparar la descarga');
      reader.readAsDataURL(blob);
    } catch (err) {
      toast.error('Error al descargar');
    }
  };

  const handlePreview = (doc) => {
    if (onPreview) {
      const viewableDocs = documents.filter(d => {
        const ext = d.filename?.split('.').pop()?.toLowerCase();
        return ['jpg', 'jpeg', 'png', 'webp', 'pdf'].includes(ext) || 
               ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'application/pdf'].includes(d.type);
      });
      const index = viewableDocs.findIndex(d => d.id === doc.id);
      if (index >= 0) {
        onPreview(viewableDocs, index, clientName, CATEGORY_CONFIG[category]?.label || category);
      }
    } else {
      setExpandedDoc(doc);
    }
  };

  const getStatusConfig = () => {
    if (documents.length === 0) {
      return { label: 'Missing', color: 'rose', icon: AlertCircle, bg: 'bg-rose-500/20 text-rose-400 border-rose-800' };
    }
    return { label: 'Completo', color: 'emerald', icon: CheckCircle, bg: 'bg-emerald-500/20 text-emerald-400 border-emerald-800' };
  };

  const statusConfig = getStatusConfig();
  const StatusIcon = statusConfig.icon;
  const formats = [...new Set(documents.map(d => {
    const ext = d.filename?.split('.').pop()?.toUpperCase() || d.type?.split('/')[1]?.toUpperCase();
    return ext;
  }).filter(Boolean))];

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl w-full max-h-[90vh] p-0 bg-slate-950 border-slate-800">
        <DialogHeader className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/95">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg bg-${config.color}-500/15 border border-${config.color}-500/30 flex items-center justify-center`}>
              <CategoryIcon className={`w-5 h-5 text-${config.color}-400`} />
            </div>
            <div>
              <DialogTitle className="text-white font-semibold">{config.label}</DialogTitle>
              <p className="text-xs text-slate-400">{clientName}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${statusConfig.bg}`}>
              <StatusIcon className="w-3 h-3" />
              {statusConfig.label}
            </span>
            <span className="text-xs text-slate-400 px-2 py-1 bg-slate-800 rounded">
              {documents.length} archivo{documents.length !== 1 ? 's' : ''}
            </span>
            <Button variant="ghost" size="icon" onClick={onClose} className="text-slate-300 hover:text-white">
              <X className="w-4 h-4" />
            </Button>
          </div>
        </DialogHeader>

        <div className="p-4">
          <div className="flex items-center justify-between gap-2 mb-4">
            <label className="cursor-pointer flex-1 sm:flex-none">
              <input 
                type="file" 
                accept=".pdf,.jpg,.jpeg,.png,.webp,.doc,.docx,.xls,.xlsx" 
                multiple
                className="sr-only" 
                onChange={(e) => e.target.files?.length && handleUpload(e.target.files)} 
                disabled={uploading}
              />
              <Button variant="outline" size="sm" disabled={uploading} className="w-full sm:w-auto">
                <Upload className="w-4 h-4 mr-1" />
                {uploading ? 'Subiendo...' : 'Subir más'}
              </Button>
            </label>
          </div>

          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="w-8 h-8 border-3 border-slate-700 border-t-cyan-500 rounded-full animate-spin" />
            </div>
          ) : documents.length === 0 ? (
            <div className="border-2 border-dashed border-slate-700/50 rounded-lg p-8 text-center">
              <CategoryIcon className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <p className="text-slate-400">No hay documentos en esta categoría</p>
              <p className="text-xs text-slate-500 mt-1">Use "Subir más" para agregar el primero</p>
            </div>
          ) : (
            <>
              <div className="space-y-2" role="list">
                {documents.slice(0, displayLimit).map((doc, index) => {
                  const fileType = getFileType(doc.filename || doc.original_name, doc.type);
                  const FileIcon = getFileIcon(fileType, doc.type);
                  const isExpanded = expandedDoc?.id === doc.id;
                  const canPreview = fileType === 'image' || fileType === 'pdf';

                  return (
                    <div key={doc.id} className="group bg-slate-900/60 border border-slate-800 rounded-lg p-3 transition-all" role="listitem">
                      <div className="flex items-center gap-3 min-w-0">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                          fileType === 'image' ? 'bg-emerald-500/15 border border-emerald-500/30' :
                          fileType === 'pdf' ? 'bg-rose-500/15 border border-rose-500/30' :
                          'bg-slate-800 border border-slate-700'
                        }`}>
                          <FileIcon className={`w-5 h-5 ${
                            fileType === 'image' ? 'text-emerald-400' :
                            fileType === 'pdf' ? 'text-rose-400' :
                            'text-slate-400'
                          }`} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="font-medium text-sm truncate text-white">{doc.original_name || doc.filename || 'documento'}</p>
                          <div className="flex flex-wrap items-center gap-3 mt-1 text-xs text-slate-400">
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 border border-slate-700 font-mono">
                              {(doc.filename?.split('.').pop()?.toUpperCase() || 'FILE')}
                            </span>
                            {doc.size && <span>{formatFileSize(doc.size)}</span>}
                            {doc.uploaded_at && <span>{formatDate(doc.uploaded_at)}</span>}
                          </div>
                        </div>
                        <div className="flex items-center gap-1 flex-shrink-0">
                          {canPreview && (
                            <Button 
                              variant="ghost" 
                              size="icon" 
                              onClick={() => handlePreview(doc)}
                              className="text-slate-400 hover:text-white h-8 w-8"
                              title="Ver"
                            >
                              <Eye className="w-4 h-4" />
                            </Button>
                          )}
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            onClick={() => handleDownload(doc)}
                            className="text-slate-400 hover:text-white h-8 w-8"
                            title="Descargar"
                          >
                            <Download className="w-4 h-4" />
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="icon" 
                            onClick={() => handleDelete(doc.id)}
                            className="text-slate-400 hover:text-rose-400 h-8 w-8"
                            title="Eliminar"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                      
                      {isExpanded && canPreview && (
                        <div className="mt-3 pt-3 border-t border-slate-800 animate-slide-down">
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-slate-400">Vista previa</span>
                            <Button variant="ghost" size="icon" onClick={() => setExpandedDoc(null)} className="text-slate-400 hover:text-white">
                              <X className="w-4 h-4" />
                            </Button>
                          </div>
                          <div className="mt-2 rounded-lg overflow-hidden bg-slate-950 border border-slate-800">
                            {fileType === 'image' && (
                              <img 
                                src={`${API}/clients/${clientId}/documents/download/${category}?doc_id=${doc.id}`} 
                                alt={doc.original_name || doc.filename}
                                className="w-full h-auto max-h-64 object-contain"
                              />
                            )}
                            {fileType === 'pdf' && (
                              <iframe
                                src={`${API}/clients/${clientId}/documents/download/${category}?doc_id=${doc.id}`}
                                className="w-full h-64 border-0 bg-white"
                                sandbox="allow-scripts allow-same-origin"
                              />
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              {documents.length > 5 && (
                <Button 
                  variant="ghost" 
                  size="sm" 
                  className="w-full mt-3"
                  onClick={() => setShowAll(!showAll)}
                >
                  {showAll ? (
                    <>
                      <ChevronUp className="w-4 h-4 mr-1" />
                      Mostrar menos
                    </>
                  ) : (
                    <>
                      Ver todos ({documents.length})
                      <ChevronDown className="w-4 h-4 ml-1" />
                    </>
                  )}
                </Button>
              )}
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}