import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// /api wird an das Backend weitergereicht: Frontend und API laufen so auf demselben
// Ursprung – Voraussetzung für das HttpOnly-/SameSite=Strict-Sitzungscookie.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        rewrite: (pfad) => pfad.replace(/^\/api/, ''),
      },
    },
  },
})
