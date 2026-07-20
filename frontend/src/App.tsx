import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useUiStore } from "./store/uiStore";
import { useAuthStore } from "./store/authStore";
import { ProtectedRoute } from "./components/UI/ProtectedRoute";
import { Login } from "./pages/Login";
import { ChatPage } from "./pages/ChatPage";
import { Profile } from "./pages/Profile";
import AdminDashboardShell from "./pages/AdminDashboardShell";
import ResetPasswordPage from "./pages/ResetPasswordPage";

// Admin protected route check
const AdminRoute = ({ children }: { children: React.ReactNode }) => {
  const isAdmin = localStorage.getItem("admin_authenticated") === "true";
  if (!isAdmin) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

export default function App() {
  const { theme, initializeUi } = useUiStore();
  const { initialize: initializeAuth } = useAuthStore();

  // Hydrate the logged-in user from storage here (not just in Login.tsx) so
  // a direct navigation/refresh on a protected route (/admin, /chat,
  // /profile) still has a real authUser - otherwise every fetch gated on
  // authUser?.userId silently no-ops and the page looks stuck/blank.
  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  useEffect(() => {
    initializeUi();
  }, [initializeUi]);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        
        {/* Protected User Chat Routes */}
        <Route
          path="/chat"
          element={
            <ProtectedRoute>
              <ChatPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <Profile />
            </ProtectedRoute>
          }
        />

        {/* Protected Admin routes */}
        <Route
          path="/admin"
          element={
            <AdminRoute>
              <AdminDashboardShell />
            </AdminRoute>
          }
        />

        {/* Fallback redirects */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
