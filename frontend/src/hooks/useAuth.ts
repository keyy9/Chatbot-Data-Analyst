import { useState } from "react";
import { useAuthStore } from "../store/authStore";

export const useAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    return localStorage.getItem("admin_authenticated") === "true";
  });

  const handleLogout = () => {
    setIsAuthenticated(false);
    localStorage.setItem("admin_authenticated", "false");
    useAuthStore.getState().logout();
  };

  return {
    isAuthenticated,
    setIsAuthenticated,
    handleLogout,
  };
};
