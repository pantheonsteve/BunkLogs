import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  base: './',
  define: {
    'process.env.VITE_GOOGLE_CLIENT_ID': JSON.stringify(process.env.VITE_GOOGLE_CLIENT_ID),
    'process.env.VITE_API_BASE_URL': JSON.stringify(process.env.VITE_API_BASE_URL),
  },
  server: {
    port: 5173,
    host: true, // Allow access from other devices on network
    proxy: {
      // Proxy all requests starting with /_allauth to your Django backend
      '/_allauth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Proxy API requests to local Django backend during development
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  },
  plugins: [react()],
  build: {
    commonjsOptions: {
      transformMixedEsModules: true,
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
  }
})
