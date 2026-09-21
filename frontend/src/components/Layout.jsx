import { useState, useEffect } from 'react';
import { Link, useLocation, NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  Package,
  Users,
  DollarSign,
  MessageSquare,
  Calendar,
  FileText,
  BarChart3,
  Bot,
  Settings,
  Menu,
  X,
  Bell,
  Search,
  ChevronDown,
  LogOut,
  Shield,
  MoreHorizontal,
  Wrench,
  Sparkles,
} from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from './ui/dropdown-menu';
import { Separator } from './ui/separator';
import NotificationsPopover from './NotificationsPopover';
import './Layout.css';

export const Layout = ({ children }) => {
  const { t } = useTranslation();
  const { user, logout, isAdmin, isDemo } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [headerSearch, setHeaderSearch] = useState('');
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const isBDC = user?.role === 'bdc';
  const isBDCManager = user?.role === 'bdc_manager';
  const isAdminOrBDC = isAdmin || isBDC || isBDCManager;
  const isDesktop = typeof window !== 'undefined' && window.innerWidth >= 1024;

  const getRoleDisplayName = (role) => {
    switch (role) {
      case 'admin': return 'Administrador';
      case 'bdc_manager': return 'BDC Manager';
      case 'bdc': return 'BDC';
      case 'telemarketer': return 'Telemarketer';
      case 'salesperson': return 'Telemarketer';
      case 'demo': return 'Demo';
      default: return role;
    }
  };

  const navItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: t('nav.dashboard') || 'Home', roles: ['all'] },
    { path: '/inventory', icon: Package, label: t('nav.inventory') || 'Inventario', roles: ['all'] },
    { path: '/leads', icon: Users, label: t('nav.leads') || 'Leads', roles: ['all'] },
    { path: '/customers', icon: Users, label: t('nav.customers') || 'Clientes', roles: ['all'] },
    { path: '/deals', icon: DollarSign, label: t('nav.deals') || 'Negocios', roles: ['all'] },
    { path: '/conversations', icon: MessageSquare, label: t('nav.conversations') || 'Conversaciones', roles: ['all'] },
    { path: '/appointments', icon: Calendar, label: t('nav.appointments') || 'Citas', roles: ['all'] },
    { path: '/documents', icon: FileText, label: t('nav.documents') || 'Documentos', roles: ['all'] },
    { path: '/reports', icon: BarChart3, label: t('nav.reports') || 'Reportes', roles: ['admin', 'bdc_manager'] },
    { path: '/jarvis', icon: Bot, label: t('nav.jarvis') || 'Jarvis', roles: ['all'] },
    { path: '/settings', icon: Settings, label: t('nav.settings') || 'Configuración', roles: ['all'] },
    ...(isAdmin ? [{ path: '/developer', icon: Wrench, label: 'Desarrollador', roles: ['admin'] }] : []),
  ];

  const filteredNavItems = navItems.filter(item => 
    item.roles.includes('all') || item.roles.includes(user?.role)
  );

  const mobileNavItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: t('nav.dashboard') || 'Home' },
    { path: '/inventory', icon: Package, label: t('nav.inventory') || 'Inventario' },
    { path: '/leads', icon: Users, label: t('nav.leads') || 'Leads' },
    { path: '/jarvis', icon: Sparkles, label: t('nav.jarvis') || 'Jarvis' },
    { path: '/more', icon: MoreHorizontal, label: t('nav.more') || 'Más' },
  ];

  const moreMenuItems = filteredNavItems.filter(item => 
    !['/dashboard', '/inventory', '/leads', '/jarvis'].includes(item.path)
  );

  const isActive = (path) => location.pathname === path || (path !== '/dashboard' && location.pathname.startsWith(path + '/'));

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth >= 1024) setSidebarOpen(false);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return (
    <div className="dealer-os-layout">
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Desktop Sidebar */}
      <aside 
        className={`sidebar ${sidebarOpen ? 'open' : ''} ${isDesktop ? 'desktop' : ''}`}
        aria-label="Navegación principal"
      >
        <div className="sidebar-content">
          {/* Logo / Brand */}
          <div className="sidebar-brand">
            <Link to="/dashboard" className="brand-link" aria-label="Dealer AI OS Home">
              <div className="brand-icon">
                <img src="/logo.png" alt="" className="w-10 h-10 object-contain" />
              </div>
              <div className="brand-text">
                <span className="brand-name">DEALER AI</span>
                <span className="brand-tagline">OS V2</span>
              </div>
            </Link>
            <button 
              className="sidebar-close lg:hidden"
              onClick={() => setSidebarOpen(false)}
              aria-label="Cerrar menú"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="sidebar-nav" role="navigation" aria-label="Menú principal">
            <ul className="nav-list" role="list">
              {filteredNavItems.map((item) => (
                <li key={item.path} className="nav-item">
                  <NavLink
                    to={item.path}
                    className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
                    onClick={() => setSidebarOpen(false)}
                    aria-current={isActive(item.path) ? 'page' : undefined}
                  >
                    <item.icon className="nav-icon w-5 h-5" aria-hidden="true" />
                    <span className="nav-label">{item.label}</span>
                    {isActive(item.path) && <span className="nav-indicator" aria-hidden="true" />}
                  </NavLink>
                </li>
              ))}
            </ul>
          </nav>

          {/* Demo indicator in sidebar */}
          {isDemo && (
            <div className="sidebar-demo-badge" aria-label="Modo Demo">
              <span className="demo-dot" aria-hidden="true" />
              <span>MODO DEMO</span>
            </div>
          )}

          {/* User section */}
          <div className="sidebar-user">
            <div className="user-info">
              <Avatar className="w-10 h-10">
                <AvatarImage src={user?.avatar_url} alt={user?.name} />
                <AvatarFallback className="text-sm font-semibold bg-blue-500">
                  {user?.name?.charAt(0).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div className="user-details">
                <p className="user-name truncate">{user?.name}</p>
                <p className="user-role">{getRoleDisplayName(user?.role)}</p>
              </div>
            </div>
            <Button
              variant="ghost"
              className="w-full justify-start text-slate-400 hover:text-white hover:bg-slate-800/50"
              onClick={logout}
              aria-label="Cerrar sesión"
            >
              <LogOut className="w-4 h-4 mr-2" />
              {t('nav.logout') || 'Cerrar sesión'}
            </Button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="main-content">
        {/* Top Header */}
        <header className="top-header" role="banner">
          <div className="header-left">
            <button
              className="menu-toggle lg:hidden"
              onClick={() => setSidebarOpen(true)}
              aria-label="Abrir menú"
              aria-expanded={sidebarOpen}
              aria-controls="sidebar"
            >
              <Menu className="w-6 h-6" />
            </button>
            <div className="header-search hidden sm:block">
              <Search className="search-icon w-5 h-5" aria-hidden="true" />
              <Input
                type="search"
                placeholder={t('header.search') || 'Buscar clientes, vehículos, citas...'}
                value={headerSearch}
                onChange={(e) => setHeaderSearch(e.target.value)}
                className="search-input"
                aria-label="Búsqueda global"
              />
            </div>
          </div>

          <div className="header-right">
            <NotificationsPopover />
            
            {/* Demo Badge in Header */}
            {isDemo && (
              <span className="demo-badge-header" aria-label="Modo Demo activo">
                <span className="demo-pulse" aria-hidden="true" />
                DEMO
              </span>
            )}

            {/* User Menu Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-10 w-10 rounded-full p-0" aria-label="Menú de usuario">
                  <Avatar className="w-10 h-10">
                    <AvatarImage src={user?.avatar_url} alt={user?.name} />
                    <AvatarFallback className="text-sm font-semibold bg-blue-500">
                      {user?.name?.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent className="w-56" align="end" forceMount>
                <div className="px-2 py-1">
                  <p className="text-sm font-medium truncate">{user?.name}</p>
                  <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                  <p className="text-xs text-muted-foreground capitalize">{getRoleDisplayName(user?.role)}</p>
                </div>
                <Separator />
                <DropdownMenuItem asChild>
                  <Link to="/settings" onClick={() => setUserMenuOpen(false)}>
                    <Settings className="w-4 h-4 mr-2" />
                    {t('nav.settings') || 'Configuración'}
                  </Link>
                </DropdownMenuItem>
                {isAdmin && (
                  <DropdownMenuItem asChild>
                    <Link to="/developer" onClick={() => setUserMenuOpen(false)}>
                      <Wrench className="w-4 h-4 mr-2" />
                      Desarrollador
                    </Link>
                  </DropdownMenuItem>
                )}
                <Separator />
                <DropdownMenuItem onClick={logout} className="text-destructive focus:text-destructive">
                  <LogOut className="w-4 h-4 mr-2" />
                  {t('nav.logout') || 'Cerrar sesión'}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        {/* Page Content */}
        <main className="page-content" id="main-content" role="main" tabIndex={-1}>
          {children}
        </main>

        {/* Mobile Bottom Navigation */}
        <nav className="mobile-bottom-nav" role="navigation" aria-label="Navegación principal móvil" aria-hidden={isDesktop}>
          {mobileNavItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `mobile-nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setSidebarOpen(false)}
              aria-current={isActive(item.path) ? 'page' : undefined}
            >
              <item.icon className="w-6 h-6" aria-hidden="true" />
              <span className="mobile-nav-label">{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Mobile More Menu Sheet */}
        <MobileMoreMenu
          items={moreMenuItems}
          isOpen={userMenuOpen}
          onClose={() => setUserMenuOpen(false)}
          location={location}
          onNavigate={() => setUserMenuOpen(false)}
        />
      </div>
    </div>
  );
};

// Mobile More Menu Component
function MobileMoreMenu({ items, isOpen, onClose, location, onNavigate }) {
  const { t } = useTranslation();
  
  if (!isOpen) return null;

  return (
    <>
      <div 
        className="fixed inset-0 bg-black/50 z-40 lg:hidden"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="fixed bottom-0 left-0 right-0 z-50 lg:hidden animate-slide-up bg-slate-950 border-t border-slate-800 rounded-t-2xl safe-bottom">
        <div className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">{t('nav.more') || 'Más opciones'}</h3>
            <button onClick={onClose} className="p-2 rounded-lg hover:bg-slate-800" aria-label="Cerrar">
              <X className="w-5 h-5" />
            </button>
          </div>
          <ul className="space-y-1" role="list">
            {items.map((item) => (
              <li key={item.path}>
                <NavLink
                  to={item.path}
                  className={({ isActive }) => `flex items-center gap-3 px-4 py-3 rounded-lg text-slate-300 transition-colors ${isActive ? 'bg-blue-500/20 text-blue-400' : 'hover:bg-slate-800/50 hover:text-white'}`}
                  onClick={onNavigate}
                  aria-current={location.pathname === item.path ? 'page' : undefined}
                >
                  <item.icon className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
                  <span className="font-medium">{item.label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </>
  );
}

export default Layout;