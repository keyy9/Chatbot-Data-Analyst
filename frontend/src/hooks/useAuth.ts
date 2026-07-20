import { useState } from "react";

export const useAuth = () => {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    return localStorage.getItem("admin_authenticated") === "true";
  });

  const handleLogout = () => {
    setIsAuthenticated(false);
    localStorage.setItem("admin_authenticated", "false");
  };

  return {
    isAuthenticated,
    setIsAuthenticated,
    handleLogout,
  };
};
