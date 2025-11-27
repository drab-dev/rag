import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    allowedHosts: ['dcdb4a06f83b.ngrok-free.app']
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
  // For production, API calls go through Nginx proxy at /api
  define: {
    // Default to /api for production builds (Nginx proxy)
    // Override with VITE_API_BASE_URL env var if needed
  },
});
