import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Built assets are emitted into the Flask static tree so the dashboard
// backend (port 5000) serves them directly under /static/soc/.
export default defineConfig({
  plugins: [react()],
  base: "/static/soc/",
  build: {
    outDir: "../dashboard/static/soc",
    emptyOutDir: true,
    assetsDir: "assets",
    sourcemap: false,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:5000",
      "/socket.io": { target: "http://127.0.0.1:5000", ws: true },
    },
  },
});
