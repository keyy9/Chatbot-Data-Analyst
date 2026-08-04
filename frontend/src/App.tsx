import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useUiStore } from "./store/uiStore";
import { useAuthStore } from "./store/authStore";
import { ProtectedRoute } from "./components/UI/ProtectedRoute";
import { ErrorBoundary } from "./components/UI/ErrorBoundary";
import { Login } from "./pages/Login";
import { ChatPage } from "./pages/ChatPage";
import { Profile } from "./pages/Profile";
import AdminDashboardShell from "./pages/AdminDashboardShell";
import ResetPasswordPage from "./pages/ResetPasswordPage";

// Admin route guard: requires a stored session whose role is "admin".
//
// This is UI gating only, NOT a security boundary - the session is read from
// localStorage/sessionStorage, so anyone can hand-write one in DevTools and
// render the admin shell. Real enforcement is server-side: every admin
// endpoint re-checks the caller's role against the database (`_require_admin`
// -> `verify_role(..., hard=True)`), so a forged session gets 403s and no data.
const AdminRoute = ({ children }: { children: React.ReactNode }) => {
  const { user, initialize } = useAuthStore();

  useEffect(() => {
    initialize();
  }, [initialize]);

  // Read local sessions directly to prevent state sync delays on first load
  const rawSession = localStorage.getItem("user_session") || sessionStorage.getItem("user_session");
  let sessionRole: string | undefined;
  if (rawSession) {
    try {
      sessionRole = JSON.parse(rawSession).role;
    } catch {
      sessionRole = undefined;
    }
  }

  const isAdmin = (user?.isAuthenticated && user.role === "admin") || sessionRole === "admin";

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
    const el = document.documentElement;
    el.classList.add("no-theme-transition");
    el.dataset.theme = theme;
    // Re-enable transitions only after the browser has painted the new theme,
    // so the colour change snaps instantly instead of sticking mid-transition.
    const raf = requestAnimationFrame(() =>
      requestAnimationFrame(() => el.classList.remove("no-theme-transition"))
    );
    return () => cancelAnimationFrame(raf);
  }, [theme]);

  return (
    <ErrorBoundary>
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
    </ErrorBoundary>
  );
}
