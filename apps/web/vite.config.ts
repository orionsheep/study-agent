import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 3847,
    strictPort: false
  },
  test: {
    environment: "jsdom",
    globals: true,
    exclude: ["**/node_modules/**", "**/dist/**", "e2e/**"]
  }
});
