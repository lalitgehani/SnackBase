import { create } from 'zustand';
import type { ConnectionState } from '../services/realtime.service';
import type { RealtimeEvent } from '../types';

interface RealtimeStore {
  connectionState: ConnectionState;
  events: RealtimeEvent[];
  isSubscribed: boolean;
  error: string | null;
  setConnecting: () => void;
  setConnected: () => void;
  setDisconnected: () => void;
  setError: (message: string) => void;
  addEvent: (event: RealtimeEvent) => void;
  clearEvents: () => void;
  setSubscribed: (status: boolean) => void;
}

export const useRealtimeStore = create<RealtimeStore>((set) => ({
  connectionState: 'disconnected',
  events: [],
  isSubscribed: false,
  error: null,

  setConnecting: () => set({ connectionState: 'connecting', error: null }),
  setConnected: () => set({ connectionState: 'connected', error: null }),
  setDisconnected: () => set({ connectionState: 'disconnected', isSubscribed: false }),
  setError: (message) => set({ connectionState: 'error', error: message }),
  
  addEvent: (event) => set((state) => {
    // If heartbeat, don't add to stream unless we want to track it
    if (event.type === 'heartbeat') return state;

    return {
      events: [event, ...state.events].slice(0, 100)
    };
  }),
  
  clearEvents: () => set({ events: [] }),
  setSubscribed: (status) => set({ isSubscribed: status }),
}));
