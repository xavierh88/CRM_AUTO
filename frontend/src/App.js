import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { JarvisProvider } from "./context/JarvisContext";
import { Toaster } from "./components/ui/sonner";
import "./i18n";
import "./App.css";

// Pages
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import InventoryPage from "./pages/InventoryPage";
import LeadsPage from "./pages/LeadsPage";
import CustomersPage from "./pages/CustomersPage";
import DealsPage from "./pages/DealsPage";
import ConversationsPage from "./pages/ConversationsPage";
import AppointmentsPage from "./pages/AppointmentsPage";
import DocumentsPage from "./pages/DocumentsPage";
import ReportsPage from "./pages/ReportsPage";
import JarvisPage from "./pages/JarvisPage";
import AdminPage from "./pages/AdminPage";
import SettingsPage from "./pages/SettingsPage";
import ImportContactsPage from "./pages/ImportContactsPage";
import PreQualifyPage from "./pages/PreQualifyPage";
import SolicitudesPage from "./pages/SolicitudesPage";
import VendedoresPage from "./pages/VendedoresPage";
import SoldPage from "./pages/SoldPage";
import Layout from "./components/Layout";

// Public Pages (for clients)
import PublicDocumentsPage from "./pages/PublicDocumentsPage";
import PublicAppointmentPage from "./pages/PublicAppointmentPage";

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }
  
  if (!user) {
    return <Navigate to="/login" replace />;
  }
  
  return children;
};

const AdminRoute = ({ children }) => {
  const { user, isAdmin, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }
  
  if (!user || !isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }
  
  return children;
};

const AdminOrBDCRoute = ({ children }) => {
  const { user, isAdmin, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }
  
  const isBDC = user?.role === 'bdc';
  const isBDCManager = user?.role === 'bdc_manager';
  if (!user || (!isAdmin && !isBDC && !isBDCManager)) {
    return <Navigate to="/dashboard" replace />;
  }
  
  return children;
};

const ReportsRoute = ({ children }) => {
  const { user, isAdmin, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }
  
  const isBDCManager = user?.role === 'bdc_manager';
  if (!user || (!isAdmin && !isBDCManager)) {
    return <Navigate to="/dashboard" replace />;
  }
  
  return children;
};

function App() {
  return (
    <AuthProvider>
      <JarvisProvider>
        <BrowserRouter>
          <Routes>
            {/* Public routes for clients (no auth required) */}
            <Route path="/c/docs/:token" element={<PublicDocumentsPage />} />
            <Route path="/c/appointment/:token" element={<PublicAppointmentPage />} />
          
          <Route path="/login" element={<LoginPage />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Layout>
                  <DashboardPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/inventory"
            element={
              <ProtectedRoute>
                <Layout>
                  <InventoryPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/leads"
            element={
              <ProtectedRoute>
                <Layout>
                  <LeadsPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/customers"
            element={
              <ProtectedRoute>
                <Layout>
                  <CustomersPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/deals"
            element={
              <ProtectedRoute>
                <Layout>
                  <DealsPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/conversations"
            element={
              <ProtectedRoute>
                <Layout>
                  <ConversationsPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/appointments"
            element={
              <ProtectedRoute>
                <Layout>
                  <AppointmentsPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/documents"
            element={
              <ProtectedRoute>
                <Layout>
                  <DocumentsPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/reports"
            element={
              <ReportsRoute>
                <Layout>
                  <ReportsPage />
                </Layout>
              </ReportsRoute>
            }
          />
          <Route
            path="/jarvis"
            element={
              <ProtectedRoute>
                <Layout>
                  <JarvisPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/solicitudes"
            element={
              <AdminOrBDCRoute>
                <Layout>
                  <SolicitudesPage />
                </Layout>
              </AdminOrBDCRoute>
            }
          />
          <Route
            path="/import"
            element={
              <AdminRoute>
                <Layout>
                  <ImportContactsPage />
                </Layout>
              </AdminRoute>
            }
          />
          <Route
            path="/vendedores"
            element={
              <AdminOrBDCRoute>
                <Layout>
                  <VendedoresPage />
                </Layout>
              </AdminOrBDCRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <AdminRoute>
                <Layout>
                  <AdminPage />
                </Layout>
              </AdminRoute>
            }
          />
          <Route
            path="/prequalify"
            element={
              <AdminRoute>
                <Layout>
                  <PreQualifyPage />
                </Layout>
              </AdminRoute>
            }
          />
          <Route
            path="/settings"
            element={
              <ProtectedRoute>
                <Layout>
                  <SettingsPage />
                </Layout>
              </ProtectedRoute>
            }
          />
          <Route
            path="/sold"
            element={
              <ProtectedRoute>
                <Layout>
                  <SoldPage />
                </Layout>
              </ProtectedRoute>
            }
          />
</Routes>
        </BrowserRouter>
        <Toaster position="top-right" richColors />
      </JarvisProvider>
    </AuthProvider>
  );
}

export default App;