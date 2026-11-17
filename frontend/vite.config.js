import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite configuration file
export default defineConfig({
  plugins: [react()],
  css: {
    postcss: {},
  },
  server: {
    port: 3000,
    proxy: {
      // Forward API requests to the backend server during local operation
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/detect': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});

