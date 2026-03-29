import { setupServer } from 'msw/node'
import { handlers } from './handlers'

/**
 * MSW server instance for Node.js (Vitest) environment.
 * Configured in src/test/setup.ts to start/stop around test suites.
 */
export const server = setupServer(...handlers)
