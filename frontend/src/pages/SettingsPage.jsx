import { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';
import { Globe, Bell, User, Shield, Database, Download, Upload, AlertTriangle, Sparkles, RotateCcw } from 'lucide-react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL + '/api';

export default function SettingsPage() {
  const { t, i18n } = useTranslation();
  const { user, isDemo } = useAuth();
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
  const [restoreMode, setRestoreMode] = useState('replace');
  const fileInputRef = useRef(null);
  
  // Delete all data states
  const [showDeleteAllConfirm, setShowDeleteAllConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');

  // Demo states
  const [isResettingDemo, setIsResettingDemo] = useState(false);

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
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const date = new Date().toISOString().split('T')[0];
      link.setAttribute('download', `carplus_backup_${date}.json`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast.success('Backup downloaded successfully');
    } catch (error) {
      console.error('Backup error:', error);
      toast.error(error.response?.data?.detail || 'Error downloading backup');
    } finally {
      setIsDownloading(false);
    }
  };

  // Handle file selection
  const handleFileSelect = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.name.endsWith('.json')) {
        toast.error('Please select a .json file');
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
      formData.append('merge_mode', restoreMode);
      
      const response = await axios.post(`${API}/admin/restore`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      
      toast.success(`Backup restored: ${response.data.message}`);
      setShowRestoreConfirm(false);
      setSelectedFile(null);
      setRestoreMode('replace');
      
      setTimeout(() => {
        window.location.reload();
      }, 2000);
    } catch (error) {
      console.error('Restore error:', error);
      toast.error(error.response?.data?.detail || 'Error restoring backup');
    } finally {
      setIsRestoring(false);
    }
  };

  // Delete all data
  const handleDeleteAllData = async () => {
    if (deleteConfirmText !== 'ELIMINAR TODO') {
      toast.error('You must type "ELIMINAR TODO" to confirm');
      return;
    }
    
    setIsDeleting(true);
    try {
      const response = await axios.delete(`${API}/admin/delete-all-data`);
      toast.success(response.data.message);
      setShowDeleteAllConfirm(false);
      setDeleteConfirmText('');
      
      setTimeout(() => {
        window.location.reload();
      }, 2000);
    } catch (error) {
      console.error('Delete error:', error);
      toast.error(error.response?.data?.detail || 'Error deleting data');
    } finally {
      setIsDeleting(false);
    }
  };

  // Reset demo data
  const handleResetDemo = async () => {
    if (!confirm('Reset demo data? This will restore all fictional demo data.')) return;
    
    setIsResettingDemo(true);
    try {
      const response = await axios.post(`${API}/demo/reset`, { confirm: true });
      toast.success('Demo data reset successfully');
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    } catch (error) {
      console.error('Demo reset error:', error);
      toast.error(error.response?.data?.detail || 'Failed to reset demo data');
    } finally {
      setIsResettingDemo(false);
    }
  };

  return (
    <div className="space-y-6 max-w-2xl" data-testid="settings-page">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">{t('nav.settings')}</h1>
        <p className="text-muted-foreground mt-1">{t('settings.managePreferences') || 'Manage your preferences'}</p>
      </div>

      {/* Demo Section - Only for demo users */}
      {isDemo && (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-500" />
              {t('settings.demoSection') || 'Demo Environment'}
            </CardTitle>
            <CardDescription>{t('settings.demoDescription') || 'Fictional data - No real actions - Isolated environment'}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-4 bg-amber-500/10 rounded-lg border border-amber-500/20">
              <div>
                <Label className="font-medium flex items-center gap-2 text-amber-700">
                  <RotateCcw className="w-4 h-4" />
                  {t('settings.resetDemoData') || 'Reset Demo Data'}
                </Label>
                <p className="text-sm text-amber-600 mt-1">
                  {t('settings.resetDemoDescription') || 'Restore all fictional demo data to initial state. No real data is affected.'}
                </p>
              </div>
              <Button 
                onClick={handleResetDemo}
                disabled={isResettingDemo}
                className="bg-amber-500 hover:bg-amber-600"
              >
                {isResettingDemo ? (
                  <>
                    <span className="animate-spin mr-2">⏳</span>
                    {t('common.resetting') || 'Resetting...'}
                  </>
                ) : (
                  <>
                    <RotateCcw className="w-4 h-4 mr-2" />
                    {t('settings.resetDemo') || 'Reset Demo'}
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Language Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Globe className="w-5 h-5 text-primary" />
            Language / Idioma
          </CardTitle>
          <CardDescription>{t('settings.chooseLanguage') || 'Choose your preferred language'}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <Button
              variant={i18n.language === 'en' ? 'default' : 'outline'}
              onClick={() => changeLanguage('en')}
              className={i18n.language === 'en' ? 'bg-primary text-primary-foreground' : ''}
              data-testid="settings-lang-en"
            >
              🇺🇸 English
            </Button>
            <Button
              variant={i18n.language === 'es' ? 'default' : 'outline'}
              onClick={() => changeLanguage('es')}
              className={i18n.language === 'es' ? 'bg-primary text-primary-foreground' : ''}
              data-testid="settings-lang-es"
            >
              🇲🇽 Español
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Notification Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="w-5 h-5 text-primary" />
            Notifications
          </CardTitle>
          <CardDescription>{t('settings.configureNotifications') || 'Configure how you receive updates'}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <Label className="font-medium">{t('settings.smsReminders') || 'SMS Reminders'}</Label>
              <p className="text-sm text-muted-foreground">{t('settings.smsRemindersDesc') || 'Receive SMS before appointments'}</p>
            </div>
            <Switch
              checked={notifications.smsReminders}
              onCheckedChange={(checked) => setNotifications({ ...notifications, smsReminders: checked })}
              data-testid="toggle-sms"
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <Label className="font-medium">{t('settings.emailAlerts') || 'Email Alerts'}</Label>
              <p className="text-sm text-muted-foreground">{t('settings.emailAlertsDesc') || 'Get email notifications for updates'}</p>
            </div>
            <Switch
              checked={notifications.emailAlerts}
              onCheckedChange={(checked) => setNotifications({ ...notifications, emailAlerts: checked })}
              data-testid="toggle-email"
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <Label className="font-medium">{t('settings.appointmentUpdates') || 'Appointment Updates'}</Label>
              <p className="text-sm text-muted-foreground">{t('settings.appointmentUpdatesDesc') || 'Notify when clients change appointments'}</p>
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
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="w-5 h-5 text-primary" />
            Profile
          </CardTitle>
          <CardDescription>{t('settings.yourAccountInfo') || 'Your account information'}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div>
              <Label className="form-label">{t('settings.name') || 'Name'}</Label>
              <p className="font-medium text-foreground">{user?.name}</p>
            </div>
            <div>
              <Label className="form-label">{t('settings.email') || 'Email'}</Label>
              <p className="font-medium text-foreground">{user?.email}</p>
            </div>
            <div>
              <Label className="form-label">{t('settings.role') || 'Role'}</Label>
              <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                user?.role === 'admin' ? 'bg-purple-500/20 text-purple-400' : 
                user?.role === 'demo' ? 'bg-amber-500/20 text-amber-400' :
                'bg-primary/20 text-primary'
              }`}>
                {user?.role}
              </span>
            </div>
            {user?.phone && (
              <div>
                <Label className="form-label">{t('settings.phone') || 'Phone'}</Label>
                <p className="font-medium text-foreground">{user.phone}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Backup & Restore - Admin Only */}
      {user?.role === 'admin' && (
        <Card className="border-amber-500/30 bg-amber-500/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="w-5 h-5 text-amber-500" />
              Backup & Restore
            </CardTitle>
            <CardDescription>{t('settings.adminOnly') || 'Database backups (Admin only)'}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Download Backup */}
            <div className="flex items-center justify-between p-4 bg-card rounded-lg border">
              <div>
                <Label className="font-medium flex items-center gap-2">
                  <Download className="w-4 h-4" />
                  Download Backup
                </Label>
                <p className="text-sm text-muted-foreground">Download all CRM data as JSON</p>
              </div>
              <Button 
                onClick={handleDownloadBackup}
                disabled={isDownloading}
                className="bg-amber-500 hover:bg-amber-600"
                data-testid="download-backup-btn"
              >
                {isDownloading ? (
                  <>
                    <span className="animate-spin mr-2">⏳</span>
                    Downloading...
                  </>
                ) : (
                  <>
                    <Download className="w-4 h-4 mr-2" />
                    Download
                  </>
                )}
              </Button>
            </div>

            {/* Restore Backup */}
            <div className="flex items-center justify-between p-4 bg-card rounded-lg border border-rose-500/30">
              <div>
                <Label className="font-medium flex items-center gap-2 text-rose-500">
                  <Upload className="w-4 h-4" />
                  Restore Backup
                </Label>
                <p className="text-sm text-rose-500">⚠️ This will replace ALL current data</p>
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
                  className="border-rose-500/30 text-rose-500 hover:bg-rose-500/10"
                  data-testid="restore-backup-btn"
                >
                  <Upload className="w-4 h-4 mr-2" />
                  Select File
                </Button>
              </div>
            </div>

            {/* Restore Confirmation Modal */}
            {showRestoreConfirm && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                <div className="bg-card rounded-lg p-6 max-w-md mx-4 shadow-xl border">
                  <div className="flex items-center gap-3 text-amber-500 mb-4">
                    <AlertTriangle className="w-8 h-8" />
                    <h3 className="text-lg font-bold text-foreground">Restore Backup</h3>
                  </div>
                  <p className="text-muted-foreground mb-2">Selected file:</p>
                  <p className="font-mono text-sm bg-muted p-2 rounded mb-4">{selectedFile?.name}</p>
                  
                  {/* Restore Mode Selection */}
                  <div className="mb-4">
                    <p className="text-sm font-medium text-foreground mb-2">Restore Mode:</p>
                    <div className="space-y-2">
                      <label className="flex items-start gap-3 p-3 border border-border rounded-lg cursor-pointer hover:bg-muted/50 transition-colors">
                        <input
                          type="radio"
                          name="restoreMode"
                          value="merge"
                          checked={restoreMode === 'merge'}
                          onChange={(e) => setRestoreMode(e.target.value)}
                          className="mt-1"
                        />
                        <div>
                          <span className="font-medium text-emerald-500">🔄 Merge (Recommended)</span>
                          <p className="text-xs text-muted-foreground mt-1">
                            Update existing records and add new ones without deleting current data.
                          </p>
                        </div>
                      </label>
                      <label className="flex items-start gap-3 p-3 border border-rose-500/30 rounded-lg cursor-pointer hover:bg-rose-500/5 transition-colors">
                        <input
                          type="radio"
                          name="restoreMode"
                          value="replace"
                          checked={restoreMode === 'replace'}
                          onChange={(e) => setRestoreMode(e.target.value)}
                          className="mt-1"
                        />
                        <div>
                          <span className="font-medium text-rose-500">🗑️ Replace All</span>
                          <p className="text-xs text-muted-foreground mt-1">
                            DELETE all current data and replace with backup.
                          </p>
                        </div>
                      </label>
                    </div>
                  </div>
                  
                  {restoreMode === 'replace' && (
                    <p className="text-rose-500 font-medium text-sm mb-4 p-2 bg-rose-500/10 rounded">
                      ⚠️ "Replace All" will DELETE all current data. This CANNOT be undone.
                    </p>
                  )}
                  
                  <div className="flex gap-3">
                    <Button 
                      variant="outline" 
                      onClick={() => {
                        setShowRestoreConfirm(false);
                        setSelectedFile(null);
                        setRestoreMode('replace');
                      }}
                      className="flex-1"
                    >
                      Cancel
                    </Button>
                    <Button 
                      onClick={handleRestoreBackup}
                      disabled={isRestoring}
                      className={`flex-1 ${restoreMode === 'merge' ? 'bg-emerald-500 hover:bg-emerald-600' : 'bg-rose-500 hover:bg-rose-600'}`}
                      data-testid="confirm-restore-btn"
                    >
                      {isRestoring ? (
                        <>
                          <span className="animate-spin mr-2">⏳</span>
                          Restoring...
                        </>
                      ) : (
                        restoreMode === 'merge' ? 'Merge Data' : 'Replace All'
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Delete All Data */}
            <div className="flex items-center justify-between p-4 bg-rose-500/10 rounded-lg border-2 border-rose-500/30 mt-4">
              <div>
                <Label className="font-medium flex items-center gap-2 text-rose-500">
                  <AlertTriangle className="w-4 h-4" />
                  Delete All Data
                </Label>
                <p className="text-sm text-rose-500">⚠️ DANGER: Permanently deletes ALL CRM information</p>
              </div>
              <Button 
                onClick={() => setShowDeleteAllConfirm(true)}
                variant="destructive"
                className="bg-rose-500 hover:bg-rose-600"
                data-testid="delete-all-btn"
              >
                <AlertTriangle className="w-4 h-4 mr-2" />
                Delete All
              </Button>
            </div>

            {/* Delete All Confirmation Modal */}
            {showDeleteAllConfirm && (
              <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
                <div className="bg-card rounded-lg p-6 max-w-md mx-4 shadow-xl border-2 border-rose-500">
                  <div className="flex items-center gap-3 text-rose-500 mb-4">
                    <AlertTriangle className="w-10 h-10" />
                    <h3 className="text-xl font-bold text-foreground">DANGER!</h3>
                  </div>
                  <p className="text-muted-foreground mb-4">
                    You are about to <strong className="text-rose-500">PERMANENTLY DELETE</strong> all CRM data:
                  </p>
                  <ul className="text-sm text-muted-foreground mb-4 list-disc list-inside bg-rose-500/10 p-3 rounded">
                    <li>All clients</li>
                    <li>All records</li>
                    <li>All appointments</li>
                    <li>All pre-qualifications</li>
                    <li>All comments</li>
                  </ul>
                  <p className="text-rose-500 font-bold mb-4">
                    ⚠️ This CANNOT be undone. Ensure you have a backup first.
                  </p>
                  <div className="mb-4">
                    <Label className="text-sm text-muted-foreground">
                      Type <strong className="text-rose-500">ELIMINAR TODO</strong> to confirm:
                    </Label>
                    <input
                      type="text"
                      value={deleteConfirmText}
                      onChange={(e) => setDeleteConfirmText(e.target.value)}
                      className="w-full mt-2 p-2 border-2 border-rose-500/30 rounded bg-background text-foreground focus:border-rose-500 focus:outline-none"
                      placeholder="ELIMINAR TODO"
                    />
                  </div>
                  <div className="flex gap-3">
                    <Button 
                      variant="outline" 
                      onClick={() => {
                        setShowDeleteAllConfirm(false);
                        setDeleteConfirmText('');
                      }}
                      className="flex-1"
                    >
                      Cancel
                    </Button>
                    <Button 
                      onClick={handleDeleteAllData}
                      disabled={isDeleting || deleteConfirmText !== 'ELIMINAR TODO'}
                      className="flex-1 bg-rose-500 hover:bg-rose-600 disabled:bg-rose-500/30"
                      data-testid="confirm-delete-all-btn"
                    >
                      {isDeleting ? (
                        <>
                          <span className="animate-spin mr-2">⏳</span>
                          Deleting...
                        </>
                      ) : (
                        '🗑️ Delete All'
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
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary" />
            About
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm text-muted-foreground">
            <p><strong>Dealer AI OS V2</strong> — Professional Dealership Operating System</p>
            <p>Car dealership CRM for managing clients, appointments, and sales.</p>
            <p className="text-xs text-muted-foreground/50 mt-4">
              Demo mode uses isolated fictional data. No real external communication.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}