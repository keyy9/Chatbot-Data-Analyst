import { create } from "zustand";
import type { UserSession } from "../types";
import { authApi, ApiError } from "../lib/apiClient";

interface AuthState {
  user: UserSession | null;
  rememberMe: boolean;
  pendingOtpUserId: string | null;
  login: (email: string, password: string, remember: boolean) => Promise<{ success: boolean; requiresOtp?: boolean; role?: "user" | "admin"; error?: string }>;
  verifyOtp: (otpCode: string) => Promise<{ success: boolean; role?: "user" | "admin"; error?: string }>;
  requestPasswordReset: (email: string) => Promise<{ success: boolean; message?: string; error?: string }>;
  logout: () => void;
  initialize: () => void;
}

function persistSession(sessionUser: UserSession, remember: boolean) {
  if (remember) {
    localStorage.setItem("user_session", JSON.stringify(sessionUser));
  } else {
    sessionStorage.setItem("user_session", JSON.stringify(sessionUser));
  }
  localStorage.setItem("remember_me_state", JSON.stringify(remember));
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  rememberMe: false,
  pendingOtpUserId: null,

  login: async (email, password, remember) => {
    try {
      const res = await authApi.login(email, password);

      if (res.requires_otp) {
        set({ pendingOtpUserId: res.user_id, rememberMe: remember });
        return { success: true, requiresOtp: true };
      }

      const sessionUser: UserSession = {
        userId: res.user_id,
        email: res.email!,
        username: res.username,
        role: res.role!,
        isAuthenticated: true
      };
      set({ user: sessionUser, rememberMe: remember, pendingOtpUserId: null });
      persistSession(sessionUser, remember);
      return { success: true, role: res.role };
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "Login failed. Please try again.";
      return { success: false, error: message };
    }
  },

  verifyOtp: async (otpCode) => {
    const { pendingOtpUserId, rememberMe } = get();
    if (!pendingOtpUserId) {
      return { success: false, error: "No login in progress. Please log in again." };
    }
    try {
      const res = await authApi.verifyOtp(pendingOtpUserId, otpCode);
      const sessionUser: UserSession = {
        userId: res.user_id,
        email: res.email!,
        username: res.username,
        role: res.role!,
        isAuthenticated: true
      };
      set({ user: sessionUser, pendingOtpUserId: null });
      persistSession(sessionUser, rememberMe);
      return { success: true, role: res.role };
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "Verification failed. Please try again.";
      return { success: false, error: message };
    }
  },

  requestPasswordReset: async (email) => {
    try {
      const res = await authApi.forgotPassword(email);
      return { success: true, message: res.message };
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "Could not send reset email. Please try again.";
      return { success: false, error: message };
    }
  },

  logout: () => {
    set({ user: null, pendingOtpUserId: null });
    localStorage.removeItem("user_session");
    sessionStorage.removeItem("user_session");
    localStorage.removeItem("admin_authenticated");
  },

  initialize: () => {
    const localSess = localStorage.getItem("user_session");
    const sessionSess = sessionStorage.getItem("user_session");
    const rememberState = localStorage.getItem("remember_me_state") === "true";

    if (localSess) {
      set({ user: JSON.parse(localSess), rememberMe: rememberState });
    } else if (sessionSess) {
      set({ user: JSON.parse(sessionSess), rememberMe: rememberState });
    }
  }
}));
