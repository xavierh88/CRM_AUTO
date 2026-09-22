import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { toast } from 'sonner';
import { Mail, Lock, User, Phone, CheckCircle2, Sparkles, Shield, Car } from 'lucide-react';
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

  const handleDemoLogin = async () => {
    setLoading(true);
    try {
      await login('demo@dealerai.com', 'demo123456');
      toast.success(t('auth.demoActivated') || 'Demo mode activated');
      navigate('/dashboard');
    } catch (error) {
      try {
        await register({ 
          email: 'demo@dealerai.com', 
          password: 'demo123456', 
          name: 'Demo User', 
          phone: '+1555000000' 
        });
        toast.success('Demo account created');
        navigate('/dashboard');
      } catch (regError) {
        try {
          await login('demo@dealerai.com', 'demo123456');
          toast.success(t('auth.demoActivated') || 'Demo mode activated');
          navigate('/dashboard');
        } catch (loginError) {
          toast.error('Demo access not configured. Contact admin.');
        }
      }
    } finally {
      setLoading(false);
    }
  };

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
    <div className="min-h-screen min-h-[100dvh] flex items-center justify-center p-4 relative overflow-hidden bg-background">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--primary)_0%,_transparent_70%)] opacity-20" aria-hidden="true" />
      <div className="absolute inset-0 opacity-[0.03]" aria-hidden="true" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noise\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noise)\'/%3E%3C/svg%3E")' }} />
      
      <div className="relative w-full max-w-md z-10">
        {/* Brand Header */}
        <div className="text-center mb-10">
          <div className="inline-flex flex-col items-center gap-3 mb-6">
            <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center shadow-[0_8px_32px_-8px_hsl(var(--primary)/0.4)]">
              <Car className="w-10 h-10 text-primary-foreground" aria-hidden="true" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-foreground tracking-tight mb-1">
            DEALER <span className="text-primary">AI</span> OS
          </h1>
          <p className="text-primary font-semibold text-lg mb-2">V2</p>
          <p className="text-muted-foreground text-sm">{t('auth.subtitle')}</p>
        </div>

        {/* Language Toggle */}
        <div className="flex justify-center gap-2 mb-8">
          <Button
            variant={i18n.language === 'en' ? 'default' : 'outline'}
            size="sm"
            onClick={() => changeLanguage('en')}
            className={i18n.language === 'en' 
              ? 'bg-primary hover:bg-primary/90 text-primary-foreground' 
              : 'bg-card border-border text-foreground hover:bg-muted'}
            data-testid="lang-en"
          >
            English
          </Button>
          <Button
            variant={i18n.language === 'es' ? 'default' : 'outline'}
            size="sm"
            onClick={() => changeLanguage('es')}
            className={i18n.language === 'es' 
              ? 'bg-primary hover:bg-primary/90 text-primary-foreground' 
              : 'bg-card border-border text-foreground hover:bg-muted'}
            data-testid="lang-es"
          >
            Español
          </Button>
        </div>

        {/* Auth Card */}
        <Card className="bg-card/50 backdrop-blur-xl border-border/50 shadow-2xl">
          <CardHeader className="pb-6 text-center">
            <CardTitle className="text-2xl font-bold text-foreground">{t('auth.welcome')}</CardTitle>
            <CardDescription className="text-muted-foreground">{t('auth.subtitle')}</CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs defaultValue="login" className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-6 bg-muted rounded-lg p-1" role="tablist">
                <TabsTrigger value="login" data-testid="login-tab" className="data-[state=active]:bg-background data-[state=active]:shadow-sm">{t('auth.login')}</TabsTrigger>
                <TabsTrigger value="register" data-testid="register-tab" className="data-[state=active]:bg-background data-[state=active]:shadow-sm">{t('auth.register')}</TabsTrigger>
              </TabsList>

              <TabsContent value="login" className="focus-visible:ring-0">
                <form onSubmit={handleLogin} className="space-y-5">
                  <div className="space-y-2">
                    <Label htmlFor="login-email" className="form-label">{t('auth.email')}</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" aria-hidden="true" />
                      <Input
                        id="login-email"
                        type="text"
                        placeholder="john@dealer.com or username"
                        className="pl-10 bg-background border-border"
                        value={loginForm.email}
                        onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
                        required
                        data-testid="login-email"
                        autoComplete="username"
                      />
                    </div>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="login-password" className="form-label">{t('auth.password')}</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" aria-hidden="true" />
                      <Input
                        id="login-password"
                        type="password"
                        placeholder="••••••••"
                        className="pl-10 bg-background border-border"
                        value={loginForm.password}
                        onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
                        required
                        data-testid="login-password"
                        autoComplete="current-password"
                      />
                    </div>
                  </div>
                  <Button 
                    type="submit" 
                    className="w-full bg-primary hover:bg-primary/90 text-primary-foreground py-3" 
                    disabled={loading}
                    data-testid="login-submit"
                  >
                    {loading ? t('common.loading') : t('auth.login')}
                  </Button>
                </form>
                
                {/* Demo Login */}
                <div className="relative my-6">
                  <div className="absolute inset-0 flex items-center">
                    <span className="w-full border-t border-border" />
                  </div>
                  <div className="relative flex justify-center text-sm">
                    <span className="px-2 bg-card text-muted-foreground">{t('auth.or') || 'Or'}</span>
                  </div>
                </div>
                
                <Button 
                  type="button"
                  variant="outline"
                  className="w-full gap-2 bg-card border-border hover:bg-muted"
                  onClick={handleDemoLogin}
                  disabled={loading}
                  data-testid="demo-login"
                >
                  <Sparkles className="w-4 h-4 text-primary" />
                  <Shield className="w-4 h-4 text-emerald-500" />
                  <span className="font-medium">{t('auth.demoMode') || 'Demo Mode'}</span>
                </Button>
                <p className="text-xs text-center text-muted-foreground mt-3">
                  {t('auth.demoNotice') || 'Fictional data • No real actions • Isolated environment'}
                </p>
              </TabsContent>

              <TabsContent value="register" className="focus-visible:ring-0">
                {registrationSuccess ? (
                  <div className="text-center py-10 space-y-4">
                    <div className="w-16 h-16 bg-emerald-500/10 rounded-full flex items-center justify-center mx-auto">
                      <CheckCircle2 className="w-8 h-8 text-emerald-500" />
                    </div>
                    <h3 className="text-lg font-semibold text-foreground">Registration Successful!</h3>
                    <p className="text-muted-foreground text-sm">
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
                  <form onSubmit={handleRegister} className="space-y-5">
                    <div className="space-y-2">
                      <Label htmlFor="register-name" className="form-label">{t('auth.name')}</Label>
                      <div className="relative">
                        <User className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" aria-hidden="true" />
                        <Input
                          id="register-name"
                          type="text"
                          placeholder="John Smith"
                          className="pl-10 bg-background border-border"
                          value={registerForm.name}
                          onChange={(e) => setRegisterForm({ ...registerForm, name: e.target.value })}
                          required
                          data-testid="register-name"
                          autoComplete="name"
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="register-email" className="form-label">{t('auth.email')}</Label>
                      <div className="relative">
                        <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" aria-hidden="true" />
                        <Input
                          id="register-email"
                          type="email"
                          placeholder="john@dealer.com"
                          className="pl-10 bg-background border-border"
                          value={registerForm.email}
                          onChange={(e) => setRegisterForm({ ...registerForm, email: e.target.value })}
                          required
                          data-testid="register-email"
                          autoComplete="email"
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="register-phone" className="form-label">{t('auth.phone')}</Label>
                      <div className="relative">
                        <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" aria-hidden="true" />
                        <Input
                          id="register-phone"
                          type="tel"
                          placeholder="+1 555 123 4567"
                          className="pl-10 bg-background border-border"
                          value={registerForm.phone}
                          onChange={(e) => setRegisterForm({ ...registerForm, phone: e.target.value })}
                          data-testid="register-phone"
                          autoComplete="tel"
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="register-password" className="form-label">{t('auth.password')}</Label>
                      <div className="relative">
                        <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" aria-hidden="true" />
                        <Input
                          id="register-password"
                          type="password"
                          placeholder="••••••••"
                          className="pl-10 bg-background border-border"
                          value={registerForm.password}
                          onChange={(e) => setRegisterForm({ ...registerForm, password: e.target.value })}
                          required
                          data-testid="register-password"
                          autoComplete="new-password"
                        />
                      </div>
                    </div>
                    <p className="text-xs text-center text-muted-foreground">
                      All new accounts require admin approval before activation
                    </p>
                    <Button 
                      type="submit" 
                      className="w-full bg-primary hover:bg-primary/90 text-primary-foreground py-3" 
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

        {/* Footer */}
        <p className="text-center text-xs text-muted-foreground mt-6">
          Dealer AI OS V2 — Professional Dealership Operating System
        </p>
      </div>
    </div>
  );
}