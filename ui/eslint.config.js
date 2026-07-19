import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist', 'coverage']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      // Allow intentionally unused names (e.g. Playwright fixtures kept for side effects)
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
    },
  },
  // Playwright fixture `use` is not a React hook — disable rules-of-hooks for e2e
  {
    files: ['e2e/**/*.{ts,tsx}'],
    rules: {
      'react-hooks/rules-of-hooks': 'off',
    },
  },
  // Intentional mixed component + helper/constant exports (shadcn, forms, test utils)
  {
    files: [
      'src/components/ui/**/*.{ts,tsx}',
      'src/components/records/FilterBuilderPanel.tsx',
      'src/pages/Endpoints/EndpointFormFields.tsx',
      'src/pages/Hooks/HookFormFields.tsx',
      'src/pages/Workflows/InstanceStatusBadge.tsx',
      'src/test/utils.tsx',
    ],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
])
