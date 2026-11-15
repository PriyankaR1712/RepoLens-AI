import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = env.REPOLENS_API_TARGET || 'http://127.0.0.1:8000';

  return {
    server: {
      host: '127.0.0.1',
      proxy: {
        '/repositories': { target: apiTarget, changeOrigin: true },
        '/health': { target: apiTarget, changeOrigin: true },
      },
    },
  };
});
