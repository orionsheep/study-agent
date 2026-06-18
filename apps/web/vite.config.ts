import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

// Proxy /api → LearnForge backend so relative fetches (e.g. the English workspace's
// `fetch('/api/english/...')`) resolve correctly during local dev without each caller
// having to hardcode the backend host. The target mirrors VITE_API_BASE_URL (default
// http://127.0.0.1:8011) so the proxy and the absolute-path client.ts stay in sync.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiBase = env.VITE_API_BASE_URL || "http://127.0.0.1:8011";
  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 3000,
      strictPort: false,
      proxy: {
        "/api": {
          target: apiBase,
          changeOrigin: true,
          // Preserve the /api prefix so the backend sees the same path the browser sent.
          ws: true,
        },
      },
    },
    test: {
      environment: "jsdom",
      globals: true,
      exclude: ["**/node_modules/**", "**/dist/**", "e2e/**"]
    }
  };
});
