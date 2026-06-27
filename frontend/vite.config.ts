import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// `build.target: 'esnext'` keeps the bundle modern and avoids an esbuild 0.28
// limitation where destructuring is not lowered for some legacy targets. The
// production build is served via CloudFront, so modern-browser-only output is
// acceptable.
export default defineConfig({
  plugins: [react()],
  build: {
    target: 'esnext',
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
});
