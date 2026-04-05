import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/workflow/api': 'http://localhost:7070',
      '/scheduler/api': 'http://localhost:7070',
      '/kb/api': 'http://localhost:7070',
      '/telegram-bridge/api': 'http://localhost:7070',
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
