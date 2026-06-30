import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  base: '/',
  define: {
    'process.env.VITE_GOOGLE_CLIENT_ID': JSON.stringify(process.env.VITE_GOOGLE_CLIENT_ID),
    'process.env.VITE_API_BASE_URL': JSON.stringify(process.env.VITE_API_BASE_URL),
  },
  server: {
    port: 5173,
    host: true, // Allow access from other devices on network
    fs: {
      // Help center imports markdown from docs/features at build time.
      allow: ['..'],
    },
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
    },
    rollupOptions: {
      output: {
        // Split heavy third-party libs into their own long-term-cacheable
        // chunks so they aren't re-downloaded when app code changes, and so
        // route chunks that don't use them stay lean. Page-level splitting is
        // handled by React.lazy in src/routes/routeConfig.jsx.
        manualChunks(id) {
          if (!id.includes('node_modules')) return undefined;
          if (id.includes('quill')) return 'vendor-quill';
          if (id.includes('chart.js') || id.includes('chartjs')) return 'vendor-charts';
          if (id.includes('@datadog')) return 'vendor-datadog';
          if (
            id.includes('react-markdown') ||
            id.includes('remark') ||
            id.includes('micromark') ||
            id.includes('mdast') ||
            id.includes('hast') ||
            id.includes('unist') ||
            id.includes('decode-named-character-reference') ||
            id.includes('property-information')
          ) {
            return 'vendor-markdown';
          }
          if (id.includes('moment')) return 'vendor-moment';
          return undefined;
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
    exclude: [
      '**/node_modules/**',
      '**/dist/**',
      'e2e/**',
    ],
  }
})
