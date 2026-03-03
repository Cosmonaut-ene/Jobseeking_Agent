import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',  // IPv4 — avoids ::1 IPv6 ECONNREFUSED on Windows
        changeOrigin: true,
      },
    },
  },
})
