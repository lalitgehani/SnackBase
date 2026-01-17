import { create } from 'zustand';
import type { ConnectionState } from '../services/realtime.service';
import type { RealtimeEvent, AuthResponse } from '../types';

interface RealtimeStore {
  connectionState: ConnectionState;
  events: RealtimeEvent[];
  isSubscribed: boolean;
  error: string | null;
  token: string | null;
  user: AuthResponse['user'] | null;
  setConnecting: () => void;
  setConnected: () => void;
  setDisconnected: () => void;
  setError: (message: string) => void;
  addEvent: (event: RealtimeEvent) => void;
  clearEvents: () => void;
  setSubscribed: (status: boolean) => void;
  setAuth: (response: AuthResponse) => void;
  logout: () => void;
}

export const useRealtimeStore = create<RealtimeStore>((set) => ({
  connectionState: 'disconnected',
  events: [],
  isSubscribed: false,
  error: null,
  token: localStorage.getItem('token'),
  user: JSON.parse(localStorage.getItem('user') || 'null'),

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
  setAuth: (response) => {
    localStorage.setItem('token', response.token);
    localStorage.setItem('user', JSON.stringify(response.user));
    set({ token: response.token, user: response.user });
  },
  logout: () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    set({ token: null, user: null, connectionState: 'disconnected', isSubscribed: false });
  },
}));
