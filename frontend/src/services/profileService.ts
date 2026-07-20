import { useProfileStore } from "../store/profileStore";

export const profileService = {
  updateDisplayName: (newName: string) => {
    useProfileStore.getState().updateDisplayName(newName);
  },
  logActivity: (activity: string) => {
    useProfileStore.getState().addActivity(activity);
  },
  getProfile: () => {
    return useProfileStore.getState().profile;
  }
};
