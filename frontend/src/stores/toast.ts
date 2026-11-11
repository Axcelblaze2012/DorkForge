import { create } from "zustand";

interface ToastState {
  message: string | null;
  show: (message: string) => void;
  hide: () => void;
}

let timer: number | undefined;

export const useToast = create<ToastState>((set) => ({
  message: null,
  show: (message) => {
    if (timer) window.clearTimeout(timer);
    set({ message });
    timer = window.setTimeout(() => set({ message: null }), 2200);
  },
  hide: () => {
    if (timer) window.clearTimeout(timer);
    set({ message: null });
  },
}));
