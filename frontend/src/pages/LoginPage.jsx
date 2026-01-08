import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { toast } from 'sonner';
import { Car, Mail, Lock, User, Phone, CheckCircle2 } from 'lucide-react';
import axios from 'axios';

export default function LoginPage() {
  const { t, i18n } = useTranslation();
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [registerForm, setRegisterForm] = useState({ 
    email: '', 
    password: '', 
    name: '', 
    phone: ''
  });
  const [registrationSuccess, setRegistrationSuccess] = useState(false);

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await login(loginForm.email, loginForm.password);
      toast.success(t('common.success'));
      navigate('/dashboard');
    } catch (error) {
      toast.error(error.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post(`${process.env.REACT_APP_BACKEND_URL}/api/auth/register`, registerForm);
      toast.success(response.data.message || 'Registration successful!');
      setRegistrationSuccess(true);
    } catch (error) {
      toast.error(error.response?.data?.detail || t('common.error'));
    } finally {
      setLoading(false);
    }
  };

  const changeLanguage = (lang) => {
    i18n.changeLanguage(lang);
    localStorage.setItem('language', lang);
  };

  return (
    <div className="min-h-screen login-bg flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex flex-col items-center gap-3 mb-4">
            <img src="/logo.png" alt="CARPLUS AUTOSALE" className="w-32 h-32 object-contain" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-1">CARPLUS <span className="text-red-500">AUTOSALE</span></h1>
          <p className="text-red-400 font-semibold text-lg mb-2">Friendly Brokerage</p>
          <p className="text-slate-300 text-sm">{t('auth.subtitle')}</p>
        </div>

        {/* Language Toggle */}
        <div className="flex justify-center gap-2 mb-6">
          <Button
            variant={i18n.language === 'en' ? 'default' : 'outline'}
            size="sm"
            onClick={() => changeLanguage('en')}
            className={i18n.language === 'en' ? 'bg-blue-600' : 'bg-white/10 text-white border-white/20 hover:bg-white/20'}
            data-testid="lang-en"
          >
            English
          </Button>
          <Button
            variant={i18n.language === 'es' ? 'default' : 'outline'}
            size="sm"
            onClick={() => changeLanguage('es')}
            className={i18n.language === 'es' ? 'bg-blue-600' : 'bg-white/10 text-white border-white/20 hover:bg-white/20'}
            data-testid="lang-es"
          >
            Español
          </Button>
        </div>

        {/* Auth Card */}
        <Card className="glass border-0 shadow-2xl">
          <CardHeader className="pb-4">
            <CardTitle className="text-xl text-slate-800">{t('auth.welcome')}</CardTitle>
            <CardDescription>{t('auth.subtitle')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="login" className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-6">
                <TabsTrigger value="login" data-testid="login-tab">{t('auth.login')}</TabsTrigger>
                <TabsTrigger value="register" data-testid="register-tab">{t('auth.register')}</TabsTrigger>
              </TabsList>

              <TabsContent value="login">
                <form onSubmit={handleLogin} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="login-email" className="form-label">{t('auth.email')}</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                      <Input
                        id="login-email"
                        type="text"
                        placeholder="john@dealer.com or username"
                        className="pl-10"
                        value={loginForm.email}
                        onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
                        required
                        data-testid="login-email"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="login-password" className="form-label">{t('auth.password')}</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                      <Input
                        id="login-password"
                        type="password"
                        placeholder="••••••••"
                        className="pl-10"
                        value={loginForm.password}
                        onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                        required
                        data-testid="login-password"
                      />
                    </div>
                  </div>
                  <Button 
                    type="submit" 
                    className="w-full bg-slate-900 hover:bg-slate-800" 
                    disabled={loading}
                    data-testid="login-submit"
                  >
                    {loading ? t('common.loading') : t('auth.login')}
                  </Button>
                </form>
              </TabsContent>

              <TabsContent value="register">
                {registrationSuccess ? (
                  <div className="text-center py-6 space-y-4">
                    <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center mx-auto">
                      <CheckCircle2 className="w-8 h-8 text-emerald-600" />
                    </div>
                    <h3 className="text-lg font-semibold text-slate-800">Registration Successful!</h3>
                    <p className="text-slate-500 text-sm">
                      Your account has been created. Please wait for an administrator to activate your account before you can log in.
                    </p>
                    <Button 
                      variant="outline" 
                      onClick={() => setRegistrationSuccess(false)}
                      className="mt-4"
                    >
                      Register Another Account
                    </Button>
                  </div>
                ) : (
                  <form onSubmit={handleRegister} className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="register-name" className="form-label">{t('auth.name')}</Label>
                      <div className="relative">
                        <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <Input
                          id="register-name"
                          type="text"
                          placeholder="John Smith"
                          className="pl-10"
                          value={registerForm.name}
                          onChange={(e) => setRegisterForm({ ...registerForm, name: e.target.value })}
                          required
                          data-testid="register-name"
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="register-email" className="form-label">{t('auth.email')}</Label>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <Input
                          id="register-email"
                          type="email"
                          placeholder="john@dealer.com"
                          className="pl-10"
                          value={registerForm.email}
                          onChange={(e) => setRegisterForm({ ...registerForm, email: e.target.value })}
                          required
                          data-testid="register-email"
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="register-phone" className="form-label">{t('auth.phone')}</Label>
                      <div className="relative">
                        <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <Input
                          id="register-phone"
                          type="tel"
                          placeholder="+1 555 123 4567"
                          className="pl-10"
                          value={registerForm.phone}
                          onChange={(e) => setRegisterForm({ ...registerForm, phone: e.target.value })}
                          data-testid="register-phone"
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="register-password" className="form-label">{t('auth.password')}</Label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <Input
                          id="register-password"
                          type="password"
                          placeholder="••••••••"
                          className="pl-10"
                          value={registerForm.password}
                          onChange={(e) => setRegisterForm({ ...registerForm, password: e.target.value })}
                          required
                          data-testid="register-password"
                        />
                      </div>
                    </div>
                    <p className="text-xs text-slate-400 text-center">
                      All new accounts require admin approval before activation
                    </p>
                    <Button 
                      type="submit" 
                      className="w-full bg-slate-900 hover:bg-slate-800" 
                      disabled={loading}
                      data-testid="register-submit"
                    >
                      {loading ? t('common.loading') : t('auth.register')}
                    </Button>
                  </form>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
