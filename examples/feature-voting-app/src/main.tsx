import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { SnackBaseClient } from '@snackbase/sdk'
import { SnackBaseProvider } from '@snackbase/sdk/react'
import App from './App'
import './index.css'

// Initialize SnackBase client
const snackbaseUrl = import.meta.env.VITE_SNACKBASE_URL || 'http://localhost:8000'

const client = new SnackBaseClient({
  baseUrl: snackbaseUrl,
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <SnackBaseProvider client={client}>
        <App />
      </SnackBaseProvider>
    </BrowserRouter>
  </StrictMode>,
)
