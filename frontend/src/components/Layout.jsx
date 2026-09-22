import { useState, useEffect, useContext } from 'react';
import { Link, useLocation, NavLink, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import { JarvisProvider, useJarvis } from '../context/JarvisContext';
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
  Command,
  Car,
  Zap,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Avatar, AvatarFallback, AvatarImage } from './ui/avatar';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from './ui/dropdown-menu';
import { Separator } from './ui/separator';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from './ui/sheet';
import { ScrollArea } from './ui/scroll-area';
import NotificationsPopover from './NotificationsPopover';
import JarvisPanel from './JarvisPanel';
import './Layout.css';

function LayoutContent({ children }) {
  const { t } = useTranslation();
  const { user, logout, isAdmin, isDemo } = useAuth();
  const { sidebarOpen: jarvisSidebarOpen, closeSidebar: closeJarvisSidebar, mobileSheetOpen: jarvisMobileSheetOpen, closeMobileSheet: closeJarvisMobileSheet, toggleSidebar: toggleJarvisSidebar, toggleMobileSheet: toggleJarvisMobileSheet } = useJarvis();
  const location = useLocation();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(() => {
    try {
      return localStorage.getItem('dealer-sidebar-collapsed') === 'true';
    } catch {
      return false;
    }
  });

  const toggleSidebarCollapsed = () => {
    setSidebarCollapsed((current) => {
      const next = !current;
      try {
        localStorage.setItem('dealer-sidebar-collapsed', String(next));
      } catch {}
      return next;
    });
  };
  const [headerSearch, setHeaderSearch] = useState('');
  const [moreSheetOpen, setMoreSheetOpen] = useState(false);
  const [isScrolled, setIsScrolled] = useState(false);

  const isBDC = user?.role === 'bdc';
  const isBDCManager = user?.role === 'bdc_manager';
  const isAdminOrBDC = isAdmin || isBDC || isBDCManager;
  const [isDesktop, setIsDesktop] = useState(() =>
    typeof window !== 'undefined'
      ? window.matchMedia('(min-width: 1024px)').matches
      : false
  );

  const getRoleDisplayName = (role) => {
    switch (role) {
      case 'admin': return t('nav.admin') || 'Administrator';
      case 'bdc_manager': return t('nav.bdcManager') || 'BDC Manager';
      case 'bdc': return t('nav.bdc') || 'BDC';
      case 'telemarketer': return t('nav.telemarketer') || 'Telemarketer';
      case 'salesperson': return t('nav.telemarketer') || 'Telemarketer';
      case 'demo': return t('nav.demo') || 'Demo';
      default: return role;
    }
  };

  const navItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: t('nav.dashboard') || 'Dashboard', roles: ['all'], section: 'core' },
    { path: '/inventory', icon: Package, label: t('nav.inventory') || 'Inventory', roles: ['all'], section: 'core' },
    { path: '/leads', icon: Users, label: t('nav.leads') || 'Leads', roles: ['all'], section: 'core' },
    { path: '/customers', icon: Users, label: t('nav.customers') || 'Customers', roles: ['all'], section: 'core' },
    { path: '/deals', icon: DollarSign, label: t('nav.deals') || 'Deals', roles: ['all'], section: 'core' },
    { path: '/conversations', icon: MessageSquare, label: t('nav.conversations') || 'Conversations', roles: ['all'], section: 'core' },
    { path: '/appointments', icon: Calendar, label: t('nav.appointments') || 'Appointments', roles: ['all'], section: 'core' },
    { path: '/documents', icon: FileText, label: t('nav.documents') || 'Documents', roles: ['all'], section: 'core' },
    { path: '/reports', icon: BarChart3, label: t('nav.reports') || 'Reports', roles: ['admin', 'bdc_manager'], section: 'analytics' },
    { path: '/jarvis', icon: Bot, label: t('nav.jarvis') || 'Jarvis', roles: ['all'], section: 'ai' },
    { path: '/settings', icon: Settings, label: t('nav.settings') || 'Settings', roles: ['all'], section: 'system' },
    ...(isAdmin ? [{ path: '/developer', icon: Wrench, label: t('nav.developer') || 'Developer', roles: ['admin'], section: 'system' }] : []),
  ];

  const filteredNavItems = navItems.filter(item => 
    item.roles.includes('all') || item.roles.includes(user?.role)
  );

  const groupedNavItems = filteredNavItems.reduce((acc, item) => {
    if (!acc[item.section]) acc[item.section] = [];
    acc[item.section].push(item);
    return acc;
  }, {});

  const sectionLabels = {
    core: t('nav.sectionCore') || 'Core',
    analytics: t('nav.sectionAnalytics') || 'Analytics',
    ai: t('nav.sectionAI') || 'AI',
    system: t('nav.sectionSystem') || 'System',
  };

  const mobileNavItems = [
    { path: '/dashboard', icon: LayoutDashboard, label: t('nav.dashboard') || 'Home' },
    { path: '/inventory', icon: Package, label: t('nav.inventory') || 'Inventory' },
    { path: '/leads', icon: Users, label: t('nav.leads') || 'Leads' },
    { path: '/jarvis', icon: Sparkles, label: t('nav.jarvis') || 'Jarvis' },
    { path: '#more', icon: MoreHorizontal, label: t('nav.more') || 'More', isMore: true },
  ];

  const moreMenuItems = filteredNavItems.filter(item => 
    !['/dashboard', '/inventory', '/leads', '/jarvis'].includes(item.path)
  );

  const isActive = (path) => location.pathname === path || (path !== '/dashboard' && location.pathname.startsWith(path + '/'));

  useEffect(() => {
    const media = window.matchMedia('(min-width: 1024px)');

    const handleBreakpointChange = (event) => {
      setIsDesktop(event.matches);

      if (event.matches) {
        setSidebarOpen(false);
        setMoreSheetOpen(false);
      }
    };

    setIsDesktop(media.matches);

    if (media.addEventListener) {
      media.addEventListener('change', handleBreakpointChange);
      return () => media.removeEventListener('change', handleBreakpointChange);
    }

    media.addListener(handleBreakpointChange);
    return () => media.removeListener(handleBreakpointChange);
  }, []);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 8);
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleGlobalSearch = (e) => {
    e.preventDefault();
    const query = headerSearch.trim();
    if (!query) return;
    navigate(`/search?q=${encodeURIComponent(query)}`);
    setHeaderSearch('');
  };

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
        className={`sidebar ${sidebarOpen ? 'open' : ''} ${isDesktop ? 'desktop' : ''} ${isDesktop && sidebarCollapsed ? 'collapsed' : ''}`}
        aria-label="Main navigation"
        id="sidebar"
      >
        <div className="sidebar-content">
          {/* Logo / Brand */}
          <div className="sidebar-brand">
            <Link to="/dashboard" className="brand-link" aria-label="Dealer AI OS Home">
              <div className="brand-icon">
                <Car className="w-6 h-6 text-primary-foreground" aria-hidden="true" />
              </div>
              <div className="brand-text">
                <span className="brand-name">DEALER <span className="text-primary">AI</span></span>
                <span className="brand-tagline">OS V2</span>
              </div>
            </Link>
            <button 
              className="sidebar-close"
              onClick={() => isDesktop ? toggleSidebarCollapsed() : setSidebarOpen(false)}
              aria-label={t('nav.closeMenu') || 'Close menu'}
            >
              {isDesktop ? (sidebarCollapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />) : <X className="w-5 h-5" />}
            </button>
          </div>

          {/* Navigation */}
          <nav className="sidebar-nav" role="navigation" aria-label="Main menu">
            <ScrollArea className="flex-1" type="auto">
              <div className="px-3">
                {Object.entries(groupedNavItems).map(([section, items]) => (
                  <div key={section} className="nav-section mb-6">
                    <h3 className="nav-section-title px-3 mb-2">{sectionLabels[section] || section}</h3>
                    <ul className="nav-list" role="list">
                      {items.map((item) => (
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
                  </div>
                ))}
              </div>
            </ScrollArea>
          </nav>

          {/* Demo indicator in sidebar */}
          {isDemo && (
            <div className="sidebar-demo-badge" aria-label={t('nav.demoMode') || 'Demo Mode'}>
              <span className="demo-dot" aria-hidden="true" />
              <span>{t('nav.demoMode') || 'DEMO MODE'}</span>
            </div>
          )}

          {/* User section */}
          <div className="sidebar-user">
            <div className="user-info">
              <Avatar className="w-10 h-10">
                <AvatarImage src={user?.avatar_url} alt={user?.name} />
                <AvatarFallback className="text-sm font-semibold bg-primary">
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
              className="w-full justify-start text-muted-foreground hover:text-foreground hover:bg-muted"
              onClick={logout}
              aria-label={t('nav.logout') || 'Logout'}
            >
              <LogOut className="w-4 h-4 sidebar-logout-icon" />
              <span className="sidebar-logout-label">{t('nav.logout') || 'Logout'}</span>
            </Button>
          </div>
        </div>

      </aside>

      {/* Main Content Area */}
      <div className={`main-content ${isDesktop && sidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        {/* Top Header */}
        <header className={`top-header ${isScrolled ? 'scrolled' : ''}`} role="banner">
          <div className="header-left">
            <button
              className="menu-toggle lg:hidden"
              onClick={() => setSidebarOpen(true)}
              aria-label={t('nav.openMenu') || 'Open menu'}
              aria-expanded={sidebarOpen}
              aria-controls="sidebar"
            >
              <Menu className="w-6 h-6" />
            </button>
            <div className="header-search hidden sm:block">
              <form onSubmit={handleGlobalSearch} className="w-full max-w-xl">
                <Search className="search-icon w-5 h-5" aria-hidden="true" />
                <Input
                  type="search"
                  placeholder={t('header.search') || 'Search clients, vehicles, appointments...'}
                  value={headerSearch}
                  onChange={(e) => setHeaderSearch(e.target.value)}
                  className="search-input"
                  aria-label="Global search"
                  onKeyDown={(e) => e.key === 'Escape' && (e.target.blur(), setHeaderSearch(''))}
                />
                <kbd className="search-shortcut" aria-hidden="true">
                  <Command className="w-3 h-3" />
                </kbd>
              </form>
            </div>
          </div>

          <div className="header-right">
            <NotificationsPopover />
            
            {/* Demo Badge in Header */}
            {isDemo && (
              <span className="demo-badge-header" aria-label={t('nav.demoActive') || 'Demo mode active'}>
                <span className="demo-pulse" aria-hidden="true" />
                {t('nav.demo') || 'DEMO'}
              </span>
            )}

            {/* Jarvis Toggle Button (Desktop) */}
            {isDesktop && (
              <Button
                variant="ghost"
                className="relative h-10 w-10 rounded-xl p-0"
                onClick={toggleJarvisSidebar}
                aria-label={jarvisSidebarOpen ? 'Close Jarvis' : 'Open Jarvis'}
                aria-expanded={jarvisSidebarOpen}
              >
                <Zap className="w-5 h-5" style={{ color: 'hsl(var(--primary))' }} />
              </Button>
            )}

            {/* User Menu Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" className="relative h-10 w-10 rounded-full p-0" aria-label="User menu">
                  <Avatar className="w-10 h-10">
                    <AvatarImage src={user?.avatar_url} alt={user?.name} />
                    <AvatarFallback className="text-sm font-semibold bg-primary">
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
                  <Link to="/settings" onClick={() => setMoreSheetOpen(false)}>
                    <Settings className="w-4 h-4 mr-2" />
                    {t('nav.settings') || 'Settings'}
                  </Link>
                </DropdownMenuItem>
                {isAdmin && (
                  <DropdownMenuItem asChild>
                    <Link to="/developer" onClick={() => setMoreSheetOpen(false)}>
                      <Wrench className="w-4 h-4 mr-2" />
                      {t('nav.developer') || 'Developer'}
                    </Link>
                  </DropdownMenuItem>
                )}
                <Separator />
                <DropdownMenuItem onClick={logout} className="text-destructive focus:text-destructive">
                  <LogOut className="w-4 h-4 mr-2" />
                  {t('nav.logout') || 'Logout'}
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
        <nav className="mobile-bottom-nav" role="navigation" aria-label="Mobile navigation" aria-hidden={isDesktop}>
          {mobileNavItems.map((item) => (
            <button
              key={item.path}
              className={`mobile-nav-item ${isActive(item.path) ? 'active' : ''}`}
              onClick={() => {
                if (item.isMore) {
                  setMoreSheetOpen(true);
                } else {
                  navigate(item.path);
                  setSidebarOpen(false);
                  closeJarvisMobileSheet();
                }
              }}
              aria-current={isActive(item.path) && !item.isMore ? 'page' : undefined}
              aria-label={item.label}
            >
              <item.icon className="w-6 h-6" aria-hidden="true" />
              <span className="mobile-nav-label">{item.label}</span>
            </button>
          ))}
        </nav>

        {/* Mobile More Sheet */}
        <Sheet open={moreSheetOpen} onOpenChange={setMoreSheetOpen}>
          <SheetContent className="sm:max-w-sm" side="bottom">
            <SheetHeader>
              <SheetTitle>{t('nav.more') || 'More'}</SheetTitle>
            </SheetHeader>
            <ScrollArea className="py-2" type="auto">
              <ul className="space-y-1" role="list">
                {moreMenuItems.map((item) => (
                  <li key={item.path}>
                    <NavLink
                      to={item.path}
                      className={({ isActive }) => `flex items-center gap-3 px-4 py-3 rounded-lg text-muted-foreground transition-colors ${isActive ? 'bg-primary/20 text-primary' : 'hover:bg-muted hover:text-foreground'}`}
                      onClick={() => setMoreSheetOpen(false)}
                      aria-current={location.pathname === item.path ? 'page' : undefined}
                    >
                      <item.icon className="w-5 h-5 flex-shrink-0" aria-hidden="true" />
                      <span className="font-medium">{item.label}</span>
                    </NavLink>
                  </li>
                ))}
              </ul>
            </ScrollArea>
          </SheetContent>
        </Sheet>

        {/* Jarvis Mobile FAB */}
        {!isDesktop && (
          <button
            className="jarvis-fab"
            onClick={toggleJarvisMobileSheet}
            aria-label={jarvisMobileSheetOpen ? 'Close Jarvis' : 'Open Jarvis'}
            aria-expanded={jarvisMobileSheetOpen}
          >
            <Zap className="w-6 h-6" />
          </button>
        )}

        {/* Jarvis Mobile Bottom Sheet */}
        {!isDesktop && (
          <div className={`jarvis-bottom-sheet ${jarvisMobileSheetOpen ? 'open' : ''}`} role="dialog" aria-label="Jarvis Assistant">
            <div className="jarvis-sheet-handle" />
            <div className="jarvis-sheet-content">
              <JarvisPanel onClose={closeJarvisMobileSheet} />
            </div>
          </div>
        )}

        {/* Jarvis Desktop Sidebar Panel */}
        {isDesktop && (
          <aside className={`jarvis-sidebar-panel ${jarvisSidebarOpen ? 'open' : ''}`} role="complementary" aria-label="Jarvis Assistant">
            <div className="flex items-center justify-between p-4 border-b border-slate-800">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Zap className="w-5 h-5" style={{ color: 'hsl(var(--primary))' }} />
                Jarvis
              </h2>
              <button
                className="p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
                onClick={closeJarvisSidebar}
                aria-label="Close Jarvis"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <JarvisPanel onClose={closeJarvisSidebar} />
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

export const Layout = ({ children }) => {
  return (
    <JarvisProvider>
      <LayoutContent children={children} />
    </JarvisProvider>
  );
};

export default Layout;
