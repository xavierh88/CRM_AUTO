import { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';
import { Globe, Bell, User, Shield, Database, Download, Upload, AlertTriangle } from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

export default function SettingsPage() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const [notifications, setNotifications] = useState({
    smsReminders: true,
    emailAlerts: false,
    appointmentUpdates: true
  });
  
  // Backup/Restore states
  const [isDownloading, setIsDownloading] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);
  const [showRestoreConfirm, setShowRestoreConfirm] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const fileInputRef = useRef(null);

  const changeLanguage = (lang) => {
    i18n.changeLanguage(lang);
    localStorage.setItem('language', lang);
    toast.success(`Language changed to ${lang === 'en' ? 'English' : 'Español'}`);
  };

  // Download backup
  const handleDownloadBackup = async () => {
    setIsDownloading(true);
    try {
      const response = await axios.get(`${API}/admin/backup`, {
        responseType: 'blob'
      });
      
      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const date = new Date().toISOString().split('T')[0];
      link.setAttribute('download', `carplus_backup_${date}.json`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Backup descargado exitosamente');
    } catch (error) {
      console.error('Backup error:', error);
      toast.error(error.response?.data?.detail || 'Error al descargar backup');
    } finally {
      setIsDownloading(false);
    }
  };

  // Handle file selection
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.name.endsWith('.json')) {
        toast.error('Por favor selecciona un archivo .json');
        return;
      }
      setSelectedFile(file);
      setShowRestoreConfirm(true);
    }
  };

  // Restore backup
  const handleRestoreBackup = async () => {
    if (!selectedFile) return;
    
    setIsRestoring(true);
    try {
      const formData = new FormData();
      formData.append('file', selectedFile);
      
      const response = await axios.post(`${API}/admin/restore`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      toast.success(`Backup restaurado: ${response.data.message}`);
      setShowRestoreConfirm(false);
      setSelectedFile(null);
      
      // Reload page to reflect changes
      setTimeout(() => {
        window.location.reload();
      }, 2000);
    } catch (error) {
      console.error('Restore error:', error);
      toast.error(error.response?.data?.detail || 'Error al restaurar backup');
    } finally {
      setIsRestoring(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl" data-testid="settings-page">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">{t('nav.settings')}</h1>
        <p className="text-slate-500 mt-1">Manage your preferences</p>
      </div>

      {/* Language Settings */}
      <Card className="dashboard-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="w-5 h-5 text-blue-600" />
            Language / Idioma
          </CardTitle>
          <CardDescription>Choose your preferred language</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <Button
              variant={i18n.language === 'en' ? 'default' : 'outline'}
              onClick={() => changeLanguage('en')}
              className={i18n.language === 'en' ? 'bg-slate-900' : ''}
              data-testid="settings-lang-en"
            >
              🇺🇸 English
            </Button>
            <Button
              variant={i18n.language === 'es' ? 'default' : 'outline'}
              onClick={() => changeLanguage('es')}
              className={i18n.language === 'es' ? 'bg-slate-900' : ''}
              data-testid="settings-lang-es"
            >
              🇲🇽 Español
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Notification Settings */}
      <Card className="dashboard-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-blue-600" />
            Notifications
          </CardTitle>
          <CardDescription>Configure how you receive updates</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label className="font-medium">SMS Reminders</Label>
              <p className="text-sm text-slate-500">Receive SMS before appointments</p>
            </div>
            <Switch
              checked={notifications.smsReminders}
              onCheckedChange={(checked) => setNotifications({ ...notifications, smsReminders: checked })}
              data-testid="toggle-sms"
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <Label className="font-medium">Email Alerts</Label>
              <p className="text-sm text-slate-500">Get email notifications for updates</p>
            </div>
            <Switch
              checked={notifications.emailAlerts}
              onCheckedChange={(checked) => setNotifications({ ...notifications, emailAlerts: checked })}
              data-testid="toggle-email"
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <Label className="font-medium">Appointment Updates</Label>
              <p className="text-sm text-slate-500">Notify when clients change appointments</p>
            </div>
            <Switch
              checked={notifications.appointmentUpdates}
              onCheckedChange={(checked) => setNotifications({ ...notifications, appointmentUpdates: checked })}
              data-testid="toggle-appt-updates"
            />
          </div>
        </CardContent>
      </Card>

      {/* Profile Info */}
      <Card className="dashboard-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="w-5 h-5 text-blue-600" />
            Profile
          </CardTitle>
          <CardDescription>Your account information</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div>
              <Label className="form-label">Name</Label>
              <p className="font-medium">{user?.name}</p>
            </div>
            <div>
              <Label className="form-label">Email</Label>
              <p className="font-medium">{user?.email}</p>
            </div>
            <div>
              <Label className="form-label">Role</Label>
              <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                user?.role === 'admin' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
              }`}>
                {user?.role}
              </span>
            </div>
            {user?.phone && (
              <div>
                <Label className="form-label">Phone</Label>
                <p className="font-medium">{user.phone}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Backup & Restore - Admin Only */}
      {user?.role === 'admin' && (
        <Card className="dashboard-card border-amber-200 bg-amber-50/30">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="w-5 h-5 text-amber-600" />
              Backup & Restore
            </CardTitle>
            <CardDescription>Administra los respaldos de la base de datos (Solo Admin)</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Download Backup */}
            <div className="flex items-center justify-between p-4 bg-white rounded-lg border">
              <div>
                <Label className="font-medium flex items-center gap-2">
                  <Download className="w-4 h-4" />
                  Descargar Respaldo
                </Label>
                <p className="text-sm text-slate-500">Descarga toda la información del CRM en formato JSON</p>
              </div>
              <Button 
                onClick={handleDownloadBackup}
                disabled={isDownloading}
                className="bg-amber-600 hover:bg-amber-700"
                data-testid="download-backup-btn"
              >
                {isDownloading ? (
                  <>
                    <span className="animate-spin mr-2">⏳</span>
                    Descargando...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4 mr-2" />
                    Descargar
                  </>
                )}
              </Button>
            </div>

            {/* Restore Backup */}
            <div className="flex items-center justify-between p-4 bg-white rounded-lg border border-red-200">
              <div>
                <Label className="font-medium flex items-center gap-2 text-red-700">
                  <Upload className="w-4 h-4" />
                  Restaurar Respaldo
                </Label>
                <p className="text-sm text-red-500">⚠️ Esto reemplazará TODOS los datos actuales</p>
              </div>
              <div>
                <input
                  type="file"
                  accept=".json"
                  onChange={handleFileSelect}
                  ref={fileInputRef}
                  className="hidden"
                />
                <Button 
                  onClick={() => fileInputRef.current?.click()}
                  variant="outline"
                  className="border-red-300 text-red-600 hover:bg-red-50"
                  data-testid="restore-backup-btn"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Seleccionar Archivo
                </Button>
              </div>
            </div>

            {/* Restore Confirmation Modal */}
            {showRestoreConfirm && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg p-6 max-w-md mx-4 shadow-xl">
                  <div className="flex items-center gap-3 text-red-600 mb-4">
                    <AlertTriangle className="w-8 h-8" />
                    <h3 className="text-lg font-bold">¡Advertencia!</h3>
                  </div>
                  <p className="text-slate-600 mb-2">
                    Estás a punto de restaurar el backup:
                  </p>
                  <p className="font-mono text-sm bg-slate-100 p-2 rounded mb-4">
                    {selectedFile?.name}
                  </p>
                  <p className="text-red-600 font-medium mb-4">
                    ⚠️ Esta acción ELIMINARÁ todos los datos actuales y los reemplazará con los del backup. Esta acción NO se puede deshacer.
                  </p>
                  <div className="flex gap-3">
                    <Button 
                      variant="outline" 
                      onClick={() => {
                        setShowRestoreConfirm(false);
                        setSelectedFile(null);
                      }}
                      className="flex-1"
                    >
                      Cancelar
                    </Button>
                    <Button 
                      onClick={handleRestoreBackup}
                      disabled={isRestoring}
                      className="flex-1 bg-red-600 hover:bg-red-700"
                      data-testid="confirm-restore-btn"
                    >
                      {isRestoring ? (
                        <>
                          <span className="animate-spin mr-2">⏳</span>
                          Restaurando...
                        </>
                      ) : (
                        'Sí, Restaurar'
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* About */}
      <Card className="dashboard-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-blue-600" />
            About
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm text-slate-500">
            <p><strong>CARPLUS AUTOSALE</strong> v1.0.0</p>
            <p>Car dealership CRM for managing clients, appointments, and sales.</p>
            <p className="text-xs text-slate-400 mt-4">
              SMS integration is currently <strong>mocked</strong>. Configure Twilio credentials to enable real SMS.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
