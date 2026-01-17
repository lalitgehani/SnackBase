import type { RealtimeEvent } from '../types';

export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'error';

export class RealtimeService {
  private ws: WebSocket | null = null;
  private baseUrl: string;
  private token: string;
  private stateChangeCallbacks: ((state: ConnectionState) => void)[] = [];
  private messageCallbacks: ((event: RealtimeEvent) => void)[] = [];
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
  private isExplicitlyDisconnected = false;

  constructor(baseUrl: string, token: string) {
    this.baseUrl = baseUrl;
    this.token = token;
    console.log(`Initialized RealtimeService with ${this.baseUrl}`);
  }

  private get wsUrl(): string {
    // Convert http/https to ws/wss
    const url = new URL(this.baseUrl);
    url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    url.pathname = `${url.pathname}/realtime/ws`;
    url.searchParams.set('token', this.token);
    return url.toString();
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.isExplicitlyDisconnected = false;
    this.updateState('connecting');

    try {
      this.ws = new WebSocket(this.wsUrl);

      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.updateState('connected');
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as RealtimeEvent;
          this.messageCallbacks.forEach((cb) => cb(data));
        } catch (e) {
          console.error('Error parsing WebSocket message', e);
        }
      };

      this.ws.onclose = (event) => {
        console.log(`WebSocket closed: ${event.code} ${event.reason}`);
        this.updateState('disconnected');
        
        if (!this.isExplicitlyDisconnected && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('WebSocket error', error);
        this.updateState('error');
      };
    } catch (error) {
      console.error('Failed to create WebSocket', error);
      this.updateState('error');
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    
    this.reconnectAttempts++;
    const delay = Math.min(Math.pow(2, this.reconnectAttempts) * 1000, 30000);
    
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
    
    this.reconnectTimeout = setTimeout(() => {
      this.connect();
    }, delay);
  }

  subscribe(collection: string, operations: string[]) {
    if (this.ws?.readyState !== WebSocket.OPEN) {
      console.warn('Cannot subscribe: WebSocket not connected');
      return;
    }

    const message = {
      action: 'subscribe',
      collection,
      operations,
    };

    this.ws.send(JSON.stringify(message));
    console.log(`Sent subscription for ${collection}`);
  }

  unsubscribe(collection: string) {
    if (this.ws?.readyState !== WebSocket.OPEN) return;

    const message = {
      action: 'unsubscribe',
      collection,
    };

    this.ws.send(JSON.stringify(message));
    console.log(`Sent unsubscribe for ${collection}`);
  }

  onStateChange(callback: (state: ConnectionState) => void) {
    this.stateChangeCallbacks.push(callback);
    return () => {
      this.stateChangeCallbacks = this.stateChangeCallbacks.filter((cb) => cb !== callback);
    };
  }

  onMessage(callback: (event: RealtimeEvent) => void) {
    this.messageCallbacks.push(callback);
    return () => {
      this.messageCallbacks = this.messageCallbacks.filter((cb) => cb !== callback);
    };
  }

  private updateState(state: ConnectionState) {
    this.stateChangeCallbacks.forEach((cb) => cb(state));
  }

  disconnect() {
    this.isExplicitlyDisconnected = true;
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.updateState('disconnected');
  }
}
