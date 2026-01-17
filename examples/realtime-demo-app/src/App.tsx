import { useEffect, useRef, useState } from 'react';
import { RealtimeDemo } from './components/realtime/RealtimeDemo';
import { LoginView } from './components/realtime/LoginView';
import { RealtimeService } from './services/realtime.service';
import { useRealtimeStore } from './stores/realtime.store';

function App() {
  const realtimeServiceRef = useRef<RealtimeService | null>(null);
  const [, setTick] = useState(0);
  const {
    token,
    setConnecting,
    setConnected,
    setDisconnected,
    setError,
    addEvent,
    setSubscribed
  } = useRealtimeStore();

  useEffect(() => {
    if (!token) {
      if (realtimeServiceRef.current) {
        realtimeServiceRef.current.disconnect();
        realtimeServiceRef.current = null;
      }
      return;
    }

    // Initialize service
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

    const service = new RealtimeService(baseUrl, token);
    realtimeServiceRef.current = service;

    const connect = () => {
      service.connect();
    };

    // Set up listeners
    const unsubscribeState = service.onStateChange((state) => {
      console.log('Connection state changed:', state);
      switch (state) {
        case 'connecting': setConnecting(); break;
        case 'connected':
          setConnected();
          service.subscribe('activities', ['create', 'update', 'delete']);
          setSubscribed(true);
          break;
        case 'disconnected': setDisconnected(); break;
        case 'error': setError('WebSocket encountered an error'); break;
      }
    });

    const unsubscribeMessage = service.onMessage((event) => {
      addEvent(event);
    });

    // Listen for manual reconnect requests
    const handleManualReconnect = () => {
      console.log('Manual reconnect triggered');
      connect();
    };
    window.addEventListener('realtime-reconnect', handleManualReconnect);

    // Start connection
    connect();

    // Tick for relative timestamps
    const tickInterval = setInterval(() => setTick(t => t + 1), 5000);

    // Cleanup
    return () => {
      unsubscribeState();
      unsubscribeMessage();
      window.removeEventListener('realtime-reconnect', handleManualReconnect);
      service.disconnect();
      clearInterval(tickInterval);
      realtimeServiceRef.current = null;
    };
  }, [token, setConnecting, setConnected, setDisconnected, setError, addEvent, setSubscribed]);

  if (!token) {
    return <LoginView />;
  }

  return <RealtimeDemo />;
}

export default App;
