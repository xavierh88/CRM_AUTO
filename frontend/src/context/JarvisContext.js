import { createContext, useContext, useState, useCallback } from 'react';

const JarvisContext = createContext(null);

export const JarvisProvider = ({ children }) => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [mobileSheetOpen, setMobileSheetOpen] = useState(false);

  const openSidebar = useCallback(() => setSidebarOpen(true), []);
  const closeSidebar = useCallback(() => setSidebarOpen(false), []);
  const toggleSidebar = useCallback(() => setSidebarOpen(prev => !prev), []);

  const openMobileSheet = useCallback(() => setMobileSheetOpen(true), []);
  const closeMobileSheet = useCallback(() => setMobileSheetOpen(false), []);
  const toggleMobileSheet = useCallback(() => setMobileSheetOpen(prev => !prev), []);

  return (
    <JarvisContext.Provider value={{
      sidebarOpen,
      setSidebarOpen,
      openSidebar,
      closeSidebar,
      toggleSidebar,
      mobileSheetOpen,
      setMobileSheetOpen,
      openMobileSheet,
      closeMobileSheet,
      toggleMobileSheet,
    }}>
      {children}
    </JarvisContext.Provider>
  );
};

export const useJarvis = () => {
  const context = useContext(JarvisContext);
  if (!context) {
    throw new Error('useJarvis must be used within a JarvisProvider');
  }
  return context;
};