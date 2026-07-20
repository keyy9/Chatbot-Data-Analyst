import { create } from "zustand";

interface SpeechState {
  isSupported: boolean;
  /** id of the message currently being read aloud, if any - lets each ChatBubble
   *  independently know whether it's the one "speaking" without its own state. */
  speakingId: string | null;
  speak: (id: string, text: string) => void;
  stop: () => void;
}

const isSupported = typeof window !== "undefined" && "speechSynthesis" in window;

export const useSpeechStore = create<SpeechState>((set, get) => ({
  isSupported,

  speakingId: null,

  speak: (id, text) => {
    if (!isSupported) return;
    const synth = window.speechSynthesis;
    synth.cancel();

    if (get().speakingId === id) {
      set({ speakingId: null });
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.onend = () => set((state) => (state.speakingId === id ? { speakingId: null } : state));
    utterance.onerror = () => set((state) => (state.speakingId === id ? { speakingId: null } : state));

    set({ speakingId: id });
    synth.speak(utterance);
  },

  stop: () => {
    if (!isSupported) return;
    window.speechSynthesis.cancel();
    set({ speakingId: null });
  },
}));
