import React, { useEffect } from "react";
import { Navigate } from "react-router-dom";
import { useAuthStore } from "../../store/authStore";

interface ProtectedRouteProps {
  children: React.ReactElement;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { user, initialize } = useAuthStore();

  useEffect(() => {
    initialize();
  }, [initialize]);

  // Read local sessions directly to prevent state sync delays on first load
  const isAuth = user?.isAuthenticated || 
                 !!localStorage.getItem("user_session") || 
                 !!sessionStorage.getItem("user_session");

  if (!isAuth) {
    return <Navigate to="/login" replace />;
  }

  return children;
};
