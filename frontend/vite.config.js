import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// /api/xyz (navigateur) -> http://localhost:8000/xyz (FastAPI). Le préfixe /api est retiré.
export default defineConfig({
  plugins: [react()],
  // Tests automatiques : `npm test` (vitest). Environnement Node : les composants sont rendus en HTML statique.
  test: { environment: "node", include: ["src/**/*.test.{js,jsx}"], css: false },
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
      // Modules d'audit rendus par le back : écrans /missions/{id}/vue/..., exports Excel /missions/{id}/excel/...,
      // portail client, tableau de bord du back et pages de gestion du mot de passe.
      // (Les routes React de la mission sont sous /espace/missions : aucun conflit.)
      "/missions": { target: "http://localhost:8000", changeOrigin: true },
      "/portail": { target: "http://localhost:8000", changeOrigin: true },
      "/dashboard": { target: "http://localhost:8000", changeOrigin: true },
      "/activer": { target: "http://localhost:8000", changeOrigin: true },
      "/mot-de-passe-oublie": { target: "http://localhost:8000", changeOrigin: true },
      "/reinitialiser": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
