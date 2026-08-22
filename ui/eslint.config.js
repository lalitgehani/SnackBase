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
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: 'axios',
              message: 'Use @snackbase/sdk via useInstanceClient() instead of axios.',
            },
          ],
        },
      ],
    },
  },
  {
    files: ['src/**/*.{ts,tsx}'],
    ignores: [
      'src/pages/platform/**',
      'src/components/platform/**',
      'src/layouts/platform/**',
      'src/lib/control-plane/**',
      'src/lib/platform/**',
      'src/platform/**',
      'src/routes/platform.tsx',
      'src/routes/ProjectStudioRoot.tsx',
      'src/RootProviders.tsx',
    ],
    rules: {
      'no-restricted-imports': [
        'error',
        {
          paths: [
            {
              name: 'axios',
              message: 'Use @snackbase/sdk via useInstanceClient() instead of axios.',
            },
            {
              name: '@snackbase/react',
              message: 'Import @snackbase/react only from platform modules.',
            },
          ],
          patterns: [
            {
              group: ['@/pages/platform/*', '@/components/platform/*', '@/layouts/platform/*'],
              message: 'Do not import platform modules from self-host code.',
            },
          ],
        },
      ],
    },
  },
  {
    files: ['e2e/**/*.{ts,tsx}'],
    rules: {
      'react-hooks/rules-of-hooks': 'off',
    },
  },
  {
    files: ['src/lib/snackbase/InstanceClientProvider.tsx'],
    rules: {
      'react-refresh/only-export-components': 'off',
      'react-hooks/refs': 'off',
    },
  },
  {
    files: [
      'src/components/ui/**/*.{ts,tsx}',
      'src/components/records/FilterBuilderPanel.tsx',
      'src/pages/Endpoints/EndpointFormFields.tsx',
      'src/pages/Hooks/HookStatusBadge.tsx',
      'src/pages/Workflows/InstanceStatusBadge.tsx',
      'src/test/utils.tsx',
      'src/lib/platform/StudioBasePathContext.tsx',
      'src/components/platform/PlatformStudioChrome.tsx',
      'src/components/platform/EnvironmentColdStartGate.tsx',
      'src/components/platform/EnvironmentStatusBadge.tsx',
      'src/layouts/platform/PlatformStudioLayout.tsx',
    ],
    rules: {
      'react-refresh/only-export-components': 'off',
    },
  },
])
