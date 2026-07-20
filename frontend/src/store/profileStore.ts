import { create } from "zustand";
import type { UserProfile } from "../types";

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
    set((state) => {
      const updated = { ...state.profile, name: newName || "Retail Analyst" };
      localStorage.setItem("user_profile_data", JSON.stringify(updated));
      return { profile: updated };
    });
  },

  addActivity: (activity) => {
    set((state) => {
      const updatedActivities = [
        activity,
        ...state.profile.recentActivities.slice(0, 9) // Limit to 10 activities
      ];
      const updated = { ...state.profile, recentActivities: updatedActivities };
      localStorage.setItem("user_profile_data", JSON.stringify(updated));
      return { profile: updated };
    });
  },

  initializeProfile: () => {
    const saved = localStorage.getItem("user_profile_data");
    if (saved) {
      set({ profile: JSON.parse(saved) });
    } else {
      set({ profile: defaultProfile });
      localStorage.setItem("user_profile_data", JSON.stringify(defaultProfile));
    }
  }
}));
