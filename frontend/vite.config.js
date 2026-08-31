import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite proxies API routes to the FastAPI backend during `npm run dev`,
// so the frontend at :5173 can hit /turn etc. without CORS.
// Production: FastAPI serves the built React app from /static and routes
// SPA paths to index.html.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // The advisor session. Without this the dev frontend can never
      // authenticate: every route below is gated on a cookie that only
      // /login issues, so the registry 401s forever and the client list
      // renders empty against a backend that is fine.
      "/login":     "http://localhost:7860",
      // The chart runtime and vendored ECharts the client report loads,
      // plus anything else served from the backend static mount.
      "/static":    "http://localhost:7860",
      "/r":         "http://localhost:7860",

      // Exact-path API endpoints
      "/turn":      "http://localhost:7860",
      "/feedback":  "http://localhost:7860",
      "/health":    "http://localhost:7860",

      // Adviser notifications — /alerts and /alerts/{id}/ack
      "/alerts":    "http://localhost:7860",

      // The advisor screen's own data. These were missing, so the dev
      // frontend rendered "No clients yet" against a backend that had
      // thirteen — a config gap that looks exactly like a data bug.
      "/clients":   "http://localhost:7860",
      "/reports":   "http://localhost:7860",
      "/registry":  "http://localhost:7860",
      "/ape":       "http://localhost:7860",

      // Prefix endpoints — sub-paths are proxied to FastAPI
      "/sessions":  "http://localhost:7860",
      "/users":     "http://localhost:7860",
      "/config":    "http://localhost:7860",

      // /admin/* hits FastAPI, but /admin (exact) is a SPA route handled by React.
      // The "^/admin/" regex prefix matches /admin/anything but NOT /admin alone.
      "^/admin/":   "http://localhost:7860",

      // Same pattern for /analytics: /analytics/* are API endpoints, but
      // /analytics alone is the SPA page handled by React Router.
      "^/analytics/": "http://localhost:7860",
    },
  },
  build: {
    // The FastAPI app will mount this directory at /static and serve
    // index.html from the root.
    outDir: "dist",
    emptyOutDir: true,
  },
});
