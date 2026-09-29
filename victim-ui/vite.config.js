import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  test: { environment: "jsdom", setupFiles: ["./src/test-setup.js"] },
  plugins: [react()],
  base: "/static/explorer/",
  build: { outDir: "../victim_server/static/explorer", emptyOutDir: true },
  server: {
    host: "0.0.0.0",
    port: 5174,
    allowedHosts: [".e2b.app"],
    proxy: { "/api": "http://127.0.0.1:5001" },
  },
});
