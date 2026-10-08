import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.CLARITY_API_TARGET || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: Object.fromEntries(
      ["/api", "/health", "/ready"].map((path) => [
        path,
        { target: apiTarget, changeOrigin: true },
      ]),
    ),
  },
  preview: {
    port: 4173,
    proxy: Object.fromEntries(
      ["/api", "/health", "/ready"].map((path) => [
        path,
        { target: apiTarget, changeOrigin: true },
      ]),
    ),
  },
  build: { outDir: "dist", sourcemap: false },
});
