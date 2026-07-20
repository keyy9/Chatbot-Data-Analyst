import { useAuthStore } from "../store/authStore";

export const authService = {
  login: (email: string, password: string, remember: boolean) => {
    return useAuthStore.getState().login(email, password, remember);
  },
  logout: () => {
    useAuthStore.getState().logout();
  },
  checkSession: () => {
    useAuthStore.getState().initialize();
  }
};
