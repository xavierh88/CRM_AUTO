import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';
import { toast } from 'sonner';
import { Globe, Bell, User, Shield } from 'lucide-react';

export default function SettingsPage() {
  const { t, i18n } = useTranslation();
  const { user } = useAuth();
  const [notifications, setNotifications] = useState({
    smsReminders: true,
    emailAlerts: false,
    appointmentUpdates: true
  });

  const changeLanguage = (lang) => {
    i18n.changeLanguage(lang);
    localStorage.setItem('language', lang);
    toast.success(`Language changed to ${lang === 'en' ? 'English' : 'Español'}`);
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
