import { create } from "zustand";
import type { ModelProvider } from "../types";

interface UiState {
  sidebarCollapsed: boolean;
  notesDrawerOpen: boolean;
  theme: "dark" | "light";
  modelProvider: ModelProvider;
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleNotesDrawer: (open?: boolean) => void;
  setTheme: (theme: "dark" | "light") => void;
  setModelProvider: (provider: ModelProvider) => void;
  initializeUi: () => void;
}

export const useUiStore = create<UiState>((set) => ({
  sidebarCollapsed: false,
  notesDrawerOpen: false,
  theme: "dark",
  modelProvider: "groq",

  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),

  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

  toggleNotesDrawer: (open) => set((state) => ({
    notesDrawerOpen: open !== undefined ? open : !state.notesDrawerOpen
  })),

  setTheme: (theme) => {
    set({ theme });
    localStorage.setItem("user_theme_preference", theme);
  },

  setModelProvider: (provider) => {
    set({ modelProvider: provider });
    localStorage.setItem("user_model_provider_preference", provider);
  },

  initializeUi: () => {
    const savedTheme = localStorage.getItem("user_theme_preference") as "dark" | "light" | null;
    if (savedTheme) {
      set({ theme: savedTheme });
    }

    const savedProvider = localStorage.getItem("user_model_provider_preference") as ModelProvider | null;
    if (savedProvider === "groq" || savedProvider === "gemini") {
      set({ modelProvider: savedProvider });
    }
  }
}));
