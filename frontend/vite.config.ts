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
        // API_ZIEL: zweites Backend für eine zweite lokale Instanz (z. B. Demo mit Abo)
        target: process.env.API_ZIEL ?? 'http://localhost:8000',
        rewrite: (pfad) => pfad.replace(/^\/api/, ''),
      },
    },
  },
})
