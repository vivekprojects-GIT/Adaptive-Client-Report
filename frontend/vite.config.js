import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite proxies API routes to the FastAPI backend during `npm run dev`,
// so the frontend at :5173 can hit /turn etc. without CORS.
// Production: FastAPI serves the built React app from /static and routes
// SPA paths to index.html.
// APE_API overrides the backend target when 7860 is taken locally.
const API = process.env.APE_API || "http://localhost:7860";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // The advisor session. Without this the dev frontend can never
      // authenticate: every route below is gated on a cookie that only
      // /login issues, so the registry 401s forever and the client list
      // renders empty against a backend that is fine.
      "/login":     API,
      // The chart runtime and vendored ECharts the client report loads,
      // plus anything else served from the backend static mount.
      "/static":    API,
      "/r":         API,

      // Exact-path API endpoints
      "/turn":      API,
      "/feedback":  API,
      "/health":    API,

      // Adviser notifications — /alerts and /alerts/{id}/ack
      "/alerts":    API,

      // The advisor screen's own data. These were missing, so the dev
      // frontend rendered "No clients yet" against a backend that had
      // thirteen — a config gap that looks exactly like a data bug.
      "/clients":   API,
      "/reports":   API,
      "/registry":  API,
      "/ape":       API,

      // Prefix endpoints — sub-paths are proxied to FastAPI
      "/sessions":  API,
      "/users":     API,
      "/config":    API,

      // /admin/* hits FastAPI, but /admin (exact) is a SPA route handled by React.
      // The "^/admin/" regex prefix matches /admin/anything but NOT /admin alone.
      "^/admin/":   API,

      // Same pattern for /analytics: /analytics/* are API endpoints, but
      // /analytics alone is the SPA page handled by React Router.
      "^/analytics/": API,
    },
  },
  build: {
    // The FastAPI app will mount this directory at /static and serve
    // index.html from the root.
    outDir: "dist",
    emptyOutDir: true,
  },
});
