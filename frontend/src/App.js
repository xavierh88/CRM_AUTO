import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { Toaster } from "./components/ui/sonner";
import "./i18n";
import "./App.css";

// Pages
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import ClientsPage from "./pages/ClientsPage";
import AgendaPage from "./pages/AgendaPage";
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
import TermsPage from "./pages/TermsPage";
import PrivacyPage from "./pages/PrivacyPage";

const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
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
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
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
      <div className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
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

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public routes for clients (no auth required) */}
          <Route path="/c/docs/:token" element={<PublicDocumentsPage />} />
          <Route path="/c/appointment/:token" element={<PublicAppointmentPage />} />
          <Route path="/terms" element={<TermsPage />} />
          <Route path="/privacy" element={<PrivacyPage />} />
          
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
            path="/clients"
            element={
              <ProtectedRoute>
                <Layout>
                  <ClientsPage />
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
          <Route
            path="/agenda"
            element={
              <ProtectedRoute>
                <Layout>
                  <AgendaPage />
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
        </Routes>
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}

export default App;
