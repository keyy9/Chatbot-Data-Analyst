import { useAuthStore } from "../store/authStore";

export const useAuth = () => {
  const user = useAuthStore((s) => s.user);
  const isAuthenticated = !!user?.isAuthenticated && user.role === "admin";

  const handleLogout = () => {
    useAuthStore.getState().logout();
  };

  return {
    isAuthenticated,
    handleLogout,
  };
};
