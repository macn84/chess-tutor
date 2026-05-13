/**
 * Vite configuration for Chess Tutor frontend.
 *
 * Dev server proxies /api to the Flask backend on :5000 so no CORS
 * configuration is needed during development.
 *
 * The test block configures Vitest to use the jsdom environment so React
 * components can be rendered without a real browser.
 */

/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:5000',
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
  },
})
