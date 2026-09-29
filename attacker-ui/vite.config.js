import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Built assets are emitted into the attacker service's static tree so the
// stdlib HTTP server (port 8001) serves the operator console directly under
// /static/console/ — no Node runtime needed at demo time.
export default defineConfig({
  test: { environment: "jsdom", setupFiles: ["./src/test-setup.js"] },
  plugins: [react()],
  base: "/static/console/",
  build: {
    outDir: "../attacker_server/static/console",
    emptyOutDir: true,
    assetsDir: "assets",
    sourcemap: false,
  },
  server: {
    host: "0.0.0.0",
    port: 5175,
    allowedHosts: [".e2b.app", ".e2b.dev"],
    proxy: { "/api": "http://127.0.0.1:8001" },
  },
});
