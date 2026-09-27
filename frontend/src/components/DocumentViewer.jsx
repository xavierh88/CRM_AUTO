import { useState, useEffect, useRef, useCallback } from 'react';
import { X, Download, ChevronLeft, ChevronRight, RotateCw, RotateCcw, ZoomIn, ZoomOut } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { toast } from 'sonner';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const VIEWABLE_IMAGE_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];
const VIEWABLE_PDF_TYPE = 'application/pdf';

function getFileType(filename, mimeType) {
  if (mimeType) {
    if (VIEWABLE_IMAGE_TYPES.includes(mimeType)) return 'image';
    if (mimeType === VIEWABLE_PDF_TYPE) return 'pdf';
  }
  const ext = filename?.split('.').pop()?.toLowerCase();
  if (['jpg', 'jpeg', 'png', 'webp'].includes(ext)) return 'image';
  if (ext === 'pdf') return 'pdf';
  return 'other';
}

function formatFileSize(bytes) {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function DocumentViewer({ 
  isOpen, 
  onClose, 
  documents = [], 
  initialIndex = 0,
  clientName = '',
  docCategory = ''
}) {
  const [currentIndex, setCurrentIndex] = useState(initialIndex);
  const [rotation, setRotation] = useState(0);
  const [zoom, setZoom] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [docData, setDocData] = useState(null);
  const imgRef = useRef(null);
  const pdfRef = useRef(null);
  const objectUrlRef = useRef(null);

  const currentDoc = documents[currentIndex];

  useEffect(() => {
    setCurrentIndex(initialIndex);
    setRotation(0);
    setZoom(1);
  }, [initialIndex, documents.length]);

  useEffect(() => {
    if (!currentDoc) {
      setDocData(null);
      setLoading(false);
      return;
    }

    let cancelled = false;

    const fetchDocument = async () => {
      setLoading(true);
      setError(null);
      setDocData(null);

      try {
        let url = `${API}/clients/${currentDoc.client_id}/documents/download/${currentDoc.doc_type}`;
        if (currentDoc.id && currentDoc.id !== 'legacy') {
          url += `?doc_id=${currentDoc.id}`;
        }

        const token = localStorage.getItem('token');
        const response = await fetch(url, {
          headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        });

        if (!response.ok) {
          let detail = 'Failed to load document';
          try {
            const body = await response.json();
            if (typeof body?.detail === 'string') detail = body.detail;
          } catch (_) {}
          throw new Error(detail);
        }

        const blob = await response.blob();
        const resolvedType = getFileType(currentDoc.filename || currentDoc.original_name, blob.type);
        let viewUrl;
        if (resolvedType === 'image') {
          viewUrl = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => reject(new Error('No se pudo leer la imagen'));
            reader.readAsDataURL(blob);
          });
        } else {
          viewUrl = URL.createObjectURL(blob);
          objectUrlRef.current = viewUrl;
        }

        if (!cancelled) {
          setDocData({
            url: viewUrl,
            type: resolvedType,
            mimeType: blob.type,
            size: blob.size,
            name: currentDoc.original_name || currentDoc.filename || 'documento'
          });
        } else if (resolvedType !== 'image') {
          URL.revokeObjectURL(viewUrl);
        }
      } catch (err) {
        if (!cancelled) {
          console.error('Document load error:', err);
          setError(err.message || 'No se pudo cargar el documento');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchDocument();

    return () => {
      cancelled = true;
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
    };
  }, [currentDoc]);

  const handleDownload = async () => {
    if (!currentDoc) return;
    
    try {
      let url = `${API}/clients/${currentDoc.client_id}/documents/download/${currentDoc.doc_type}`;
      if (currentDoc.id && currentDoc.id !== 'legacy') {
        url += `?doc_id=${currentDoc.id}`;
      }

      const token = localStorage.getItem('token');
      const response = await fetch(url, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {}
      });

      if (!response.ok) {
        let detail = 'Download failed';
        try {
          const body = await response.json();
          if (typeof body?.detail === 'string') detail = body.detail;
        } catch (_) {}
        throw new Error(detail);
      }

      const blob = await response.blob();
      const downloadUrl = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = currentDoc.original_name || currentDoc.filename || `documento_${currentDoc.doc_type}`;
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      link.remove();
      setTimeout(() => URL.revokeObjectURL(downloadUrl), 3000);
      
      toast.success('Descarga iniciada');
    } catch (err) {
      console.error('Document download error:', err);
      toast.error(err.message || 'Error al descargar');
    }
  };

  const handleRotate = (direction) => {
    setRotation(prev => (prev + (direction === 'cw' ? 90 : -90)) % 360);
  };

  const handleZoom = (direction) => {
    setZoom(prev => {
      const newZoom = direction === 'in' ? prev * 1.2 : prev / 1.2;
      return Math.max(0.25, Math.min(4, newZoom));
    });
  };

  const handleResetView = () => {
    setRotation(0);
    setZoom(1);
  };

  const goToPrevious = useCallback(() => {
    if (currentIndex > 0) setCurrentIndex(prev => prev - 1);
  }, [currentIndex]);

  const goToNext = useCallback(() => {
    if (currentIndex < documents.length - 1) setCurrentIndex(prev => prev + 1);
  }, [currentIndex, documents.length]);

  const handleKeyDown = useCallback((e) => {
    if (e.key === 'ArrowLeft') goToPrevious();
    if (e.key === 'ArrowRight') goToNext();
    if (e.key === 'Escape') onClose();
  }, [goToPrevious, goToNext, onClose]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, handleKeyDown]);

  if (!isOpen) return null;

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-[95vw] max-h-[95vh] p-0 bg-slate-950 border-slate-800">
        <DialogHeader className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/95">
          <DialogTitle className="text-white font-semibold truncate max-w-[60%]">
            {docCategory ? `${docCategory} / ` : ''}{currentDoc?.original_name || currentDoc?.filename || currentDoc?.name || 'Documento'}
          </DialogTitle>
          <div className="flex items-center gap-2">
            {documents.length > 1 && (
              <span className="text-xs text-slate-400 px-2 py-1 bg-slate-800 rounded">
                {currentIndex + 1} / {documents.length}
              </span>
            )}
            {docData && (
              <>
                <Button variant="ghost" size="icon" onClick={handleDownload} className="text-slate-300 hover:text-white" title="Descargar">
                  <Download className="w-4 h-4" />
                </Button>
                {docData.type === 'image' && (
                  <>
                    <Button variant="ghost" size="icon" onClick={() => handleRotate('ccw')} className="text-slate-300 hover:text-white" title="Rotar izquierda">
                      <RotateCcw className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => handleRotate('cw')} className="text-slate-300 hover:text-white" title="Rotar derecha">
                      <RotateCw className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => handleZoom('in')} className="text-slate-300 hover:text-white" title="Acercar">
                      <ZoomIn className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => handleZoom('out')} className="text-slate-300 hover:text-white" title="Alejar">
                      <ZoomOut className="w-4 h-4" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={handleResetView} className="text-slate-300 hover:text-white" title="Restablecer">
                      <span className="text-xs font-mono">100%</span>
                    </Button>
                  </>
                )}
                <Button variant="ghost" size="icon" onClick={onClose} className="text-slate-300 hover:text-white">
                  <X className="w-4 h-4" />
                </Button>
              </>
            )}
          </div>
        </DialogHeader>

        <div className="relative h-[calc(100vh-120px)] max-h-[calc(100vh-120px)] flex items-center justify-center overflow-auto bg-slate-950" 
             onWheel={(e) => {
               if (e.ctrlKey) {
                 e.preventDefault();
                 handleZoom(e.deltaY > 0 ? 'out' : 'in');
               }
             }}>
         
          {loading && (
            <div className="flex flex-col items-center gap-4 text-slate-400">
              <div className="w-10 h-10 border-3 border-slate-700 border-t-cyan-500 rounded-full animate-spin" />
              <p>Cargando documento...</p>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center gap-4 text-slate-400 p-8">
              <p className="text-rose-400">{error}</p>
              <p className="text-xs">El archivo podría no ser previsualizable. Use el botón de descarga.</p>
              <Button variant="outline" onClick={handleDownload}>
                <Download className="w-4 h-4 mr-2" /> Descargar archivo
              </Button>
            </div>
          )}

          {docData && docData.type === 'image' && (
            <img
              ref={imgRef}
              src={docData.url}
              alt={docData.name}
              style={{
                transform: `rotate(${rotation}deg) scale(${zoom})`,
                transformOrigin: 'center center',
                maxWidth: '95vw',
                maxHeight: '90vh',
                cursor: zoom > 1 ? 'grab' : 'default'
              }}
              onLoad={() => setError(null)}
              onError={() => setError('No se puede previsualizar esta imagen')}
            />
          )}

          {docData && docData.type === 'pdf' && (
            <div className="w-full h-full flex items-center justify-center p-4">
              <iframe
                ref={pdfRef}
                src={docData.url}
                className="w-full h-full border-0 bg-white"
                title={docData.name}
                sandbox="allow-scripts allow-same-origin"
              />
            </div>
          )}

          {docData && docData.type === 'other' && (
            <div className="flex flex-col items-center gap-4 text-slate-400 p-8">
              <p>Este formato no se puede previsualizar en el navegador</p>
              <p className="text-xs text-slate-500">{docData.name} • {formatFileSize(docData.size)}</p>
              <Button variant="outline" onClick={handleDownload}>
                <Download className="w-4 h-4 mr-2" /> Descargar para ver
              </Button>
            </div>
          )}
        </div>

        {documents.length > 1 && (
          <div className="flex items-center justify-center gap-3 p-4 border-t border-slate-800 bg-slate-900/50">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={goToPrevious} 
              disabled={currentIndex === 0}
              className="w-auto"
            >
              <ChevronLeft className="w-4 h-4 mr-1" /> Anterior
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={goToNext} 
              disabled={currentIndex === documents.length - 1}
              className="w-auto"
            >
              Siguiente <ChevronRight className="w-4 h-4 ml-1" />
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}