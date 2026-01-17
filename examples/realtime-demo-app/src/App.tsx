import { useEffect, useRef, useState } from 'react';
import { ActionPanel } from './components/realtime/ActionsPanel';
import { EventStream } from './components/realtime/EventStream';
import { ConnectionStatus } from './components/realtime/ConnectionStatus';
import { RealtimeService } from './services/realtime.service';
import { useRealtimeStore } from './stores/realtime.store';

function App() {
  const realtimeServiceRef = useRef<RealtimeService | null>(null);
  const [, setTick] = useState(0); // Used to trigger re-renders for relative timestamps
  const {
    setConnecting,
    setConnected,
    setDisconnected,
    setError,
    addEvent,
    setSubscribed
  } = useRealtimeStore();

  useEffect(() => {
    // Initialize service
    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';
    const token = localStorage.getItem('token') || 'demo-token';

    const service = new RealtimeService(baseUrl, token);
    realtimeServiceRef.current = service;

    // Set up listeners
    const unsubscribeState = service.onStateChange((state) => {
      console.log('Store update state:', state);
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

    // Start connection
    service.connect();

    // Tick for relative timestamps
    const tickInterval = setInterval(() => setTick(t => t + 1), 5000);

    // Cleanup
    return () => {
      unsubscribeState();
      unsubscribeMessage();
      service.disconnect();
      clearInterval(tickInterval);
    };
  }, [setConnecting, setConnected, setDisconnected, setError, addEvent, setSubscribed]);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-50">
      <header className="border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold">SnackBase Realtime Demo</h1>
            <p className="text-xs text-slate-500">Open in two tabs to see real-time sync</p>
          </div>
          <div id="connection-status-placeholder">
            <ConnectionStatus />
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Left Panel: Actions */}
          <div className="lg:col-span-4 space-y-6">
            <section className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 p-6">
              <h2 className="text-lg font-semibold mb-4">Actions</h2>
              <ActionPanel />
            </section>

            <section className="bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-100 dark:border-blue-800/50 p-6">
              <h2 className="text-sm font-bold text-blue-800 dark:text-blue-300 uppercase tracking-wider mb-3">How to use</h2>
              <ul className="text-sm text-blue-700 dark:text-blue-400 space-y-2 list-disc pl-4">
                <li>Open this page in two browser tabs</li>
                <li>In one tab, click an action button</li>
                <li>Watch the event appear in both tabs instantly</li>
              </ul>
            </section>
          </div>

          {/* Right Panel: Event Stream */}
          <div className="lg:col-span-8">
            <section className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 flex flex-col h-[calc(100vh-14rem)]">
              <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                <h2 className="text-lg font-semibold">Realtime Event Stream</h2>
                <button
                  onClick={() => useRealtimeStore.getState().clearEvents()}
                  className="text-xs font-medium text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                >
                  Clear Stream
                </button>
              </div>
              <EventStream />
            </section>
          </div>
        </div>
      </main>

      <footer className="py-8 text-center text-slate-500 text-sm">
        <p>Powered by <a href="https://github.com/snackbase/snackbase" className="text-blue-600 hover:underline">SnackBase</a></p>
      </footer>
    </div>
  );
}

export default App;
