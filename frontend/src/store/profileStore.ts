import { create } from "zustand";
import type { UserProfile } from "../types";
import { useAuthStore } from "./authStore";

interface ProfileState {
  profile: UserProfile;
  updateDisplayName: (newName: string) => void;
  addActivity: (activity: string) => void;
  initializeProfile: () => void;
}

const defaultProfile: UserProfile = {
  email: "user@lapisai.com",
  name: "Retail Analyst",
  role: "User",
  createdAt: "2026-06-25",
  recentActivities: [
    "Logged in successfully",
    "Analysed May revenue trends",
    "Created note 'Monthly Summary'",
    "Checked top products category 'Kue Basah'"
  ]
};

export const useProfileStore = create<ProfileState>((set) => ({
  profile: defaultProfile,

  updateDisplayName: (newName) => {
    const userId = useAuthStore.getState().user?.userId;
    const storageKey = userId ? `user_profile_data_${userId}` : "user_profile_data";
    set((state) => {
      const updated = { ...state.profile, name: newName || "Retail Analyst" };
      localStorage.setItem(storageKey, JSON.stringify(updated));
      return { profile: updated };
    });
  },

  addActivity: (activity) => {
    const userId = useAuthStore.getState().user?.userId;
    const storageKey = userId ? `user_profile_data_${userId}` : "user_profile_data";
    set((state) => {
      const updatedActivities = [
        activity,
        ...state.profile.recentActivities.slice(0, 9) // Limit to 10 activities
      ];
      const updated = { ...state.profile, recentActivities: updatedActivities };
      localStorage.setItem(storageKey, JSON.stringify(updated));
      return { profile: updated };
    });
  },

  initializeProfile: () => {
    const userId = useAuthStore.getState().user?.userId;
    const storageKey = userId ? `user_profile_data_${userId}` : "user_profile_data";
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      set({ profile: JSON.parse(saved) });
    } else {
      const user = useAuthStore.getState().user;
      const initialProfile: UserProfile = {
        email: user?.email || "user@lapisai.com",
        name: user?.username || "Retail Analyst",
        role: "User",
        createdAt: new Date().toISOString().split("T")[0],
        recentActivities: [
          "Logged in successfully"
        ]
      };
      set({ profile: initialProfile });
      localStorage.setItem(storageKey, JSON.stringify(initialProfile));
    }
  }
}));
