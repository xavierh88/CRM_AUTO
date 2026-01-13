import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { 
  LayoutDashboard, 
  Users, 
  Calendar, 
  Settings, 
  LogOut, 
  Menu, 
  X,
  Shield,
  FileSpreadsheet,
  FileText,
  MessageSquare,
  BarChart3
} from 'lucide-react';
import { Button } from './ui/button';
import NotificationsPopover from './NotificationsPopover';

export const Layout = ({ children }) => {
  const { t } = useTranslation();
  const { user, logout, isAdmin } = useAuth();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const isBDC = user?.role === 'bdc';
  const isAdminOrBDC = isAdmin || isBDC;

  const navItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: t('nav.dashboard') },
    { path: '/clients', icon: Users, label: t('nav.clients') },
    { path: '/agenda', icon: Calendar, label: t('nav.agenda') },
    { path: '/solicitudes', icon: MessageSquare, label: 'Solicitudes' },
    { path: '/import', icon: FileSpreadsheet, label: t('nav.import') || 'Importar' },
    ...(isAdminOrBDC ? [{ path: '/vendedores', icon: BarChart3, label: 'Vendedores' }] : []),
    ...(isAdmin ? [{ path: '/prequalify', icon: FileText, label: 'Pre-Qualify' }] : []),
    ...(isAdmin ? [{ path: '/admin', icon: Shield, label: t('nav.admin') }] : []),
    { path: '/settings', icon: Settings, label: t('nav.settings') },
  ];

  const isActive = (path) => location.pathname === path;

  // Check if we're on desktop (lg breakpoint = 1024px)
  const isDesktop = typeof window !== 'undefined' && window.innerWidth >= 1024;

  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f8fafc' }}>
      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(15, 23, 42, 0.5)',
            zIndex: 40
          }}
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside 
        className="sidebar noise-texture"
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          bottom: 0,
          width: '256px',
          zIndex: 50,
          transform: sidebarOpen ? 'translateX(0)' : (isDesktop ? 'translateX(0)' : 'translateX(-100%)'),
          transition: 'transform 0.2s ease-in-out'
        }}
      >
        <div className="flex flex-col h-full relative z-10">
          {/* Logo */}
          <div className="flex items-center gap-3 px-6 py-4 border-b border-slate-700/50">
            <img src="/logo.png" alt="CARPLUS AUTOSALE" className="w-12 h-12 object-contain" />
            <div>
              <h1 className="font-bold text-white text-lg tracking-tight">CARPLUS</h1>
              <p className="text-xs text-red-400 font-semibold">Friendly Brokerage</p>
            </div>
            <button 
              className="lg:hidden ml-auto text-slate-400 hover:text-white"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-6 space-y-1 overflow-y-auto">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`sidebar-item ${isActive(item.path) ? 'active' : ''}`}
                onClick={() => setSidebarOpen(false)}
                data-testid={`nav-${item.path.slice(1)}`}
              >
                <item.icon className="w-5 h-5" />
                <span className="font-medium">{item.label}</span>
              </Link>
            ))}
          </nav>

          {/* User info */}
          <div className="px-4 py-4 border-t border-slate-700/50">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white font-semibold">
                {user?.name?.charAt(0).toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-white truncate">{user?.name}</p>
                <p className="text-xs text-slate-400 truncate">{user?.email}</p>
              </div>
            </div>
            <Button
              variant="ghost"
              className="w-full justify-start text-slate-300 hover:text-white hover:bg-slate-800"
              onClick={logout}
              data-testid="logout-btn"
            >
              <LogOut className="w-4 h-4 mr-2" />
              {t('nav.logout')}
            </Button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div 
        style={{ 
          marginLeft: isDesktop ? '256px' : '0',
          minHeight: '100vh'
        }}
      >
        {/* Top bar */}
        <header 
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 30,
            backgroundColor: 'rgba(255, 255, 255, 0.8)',
            backdropFilter: 'blur(12px)',
            borderBottom: '1px solid rgba(226, 232, 240, 0.5)',
            padding: '12px 16px'
          }}
        >
          <div className="flex items-center gap-3">
            <button 
              className="lg:hidden p-2 rounded-lg hover:bg-slate-100"
              onClick={() => setSidebarOpen(true)}
              data-testid="mobile-menu-btn"
            >
              <Menu className="w-5 h-5 text-slate-600" />
            </button>
            <div className="flex-1" />
            <div className="flex items-center gap-2">
              <NotificationsPopover />
              <div className={`px-2 py-1 rounded text-xs font-medium ${
                isAdmin ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'
              }`}>
                {user?.role}
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main style={{ padding: '16px' }}>
          {children}
        </main>
      </div>
    </div>
  );
};

export default Layout;
