import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api/xyz (navigateur) -> http://localhost:8000/xyz (FastAPI). Le préfixe /api est retiré.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true, rewrite: (p) => p.replace(/^\/api/, "") },
      // Écrans rendus par le back (équipe du cabinet, console éditeur…) : même origine => la session (cookie) est partagée.
      "/vue": { target: "http://localhost:8000", changeOrigin: true },
      "/static": { target: "http://localhost:8000", changeOrigin: true },
      "/console": { target: "http://localhost:8000", changeOrigin: true },
      "/login": { target: "http://localhost:8000", changeOrigin: true },
      "/logout": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
