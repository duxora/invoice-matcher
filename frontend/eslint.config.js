import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
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
      // Apps must not import from each other.
      // Rationale: each app under src/apps/ is an independently deployable slice.
      // Cross-app imports create hidden coupling that breaks the isolation boundary
      // and makes it impossible to extract apps later. All shared code must live
      // in src/shared/ and be imported from there instead.
      // TODO: tighten this with a regex-based no-restricted-imports rule once
      //       the src/apps/ directory structure is established (ticket #421+).
      'no-restricted-imports': [
        'warn',
        {
          patterns: [
            {
              // Placeholder pattern — will be refined once app directories exist.
              // Intent: src/apps/X/** should NOT import from src/apps/Y/**
              group: ['../apps/*', '../../apps/*'],
              message:
                'Do not import across app boundaries. Use src/shared/ for cross-app utilities.',
            },
          ],
        },
      ],
    },
  },
])
