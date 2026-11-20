import { fileURLToPath, URL } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  // Safe headers for the app pages. Camera/microphone stay allowed for this origin only.
  // (No CSP here: MediaPipe WebAssembly and Vite's dev client would need careful allowances.)
  const headers = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(self), microphone=(self), geolocation=()",
  };
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    build: {
      rollupOptions: {
        output: {
          // Keep the large charting library out of the main bundle so it caches separately.
          manualChunks: {
            charts: ["recharts"],
            vendor: ["react", "react-dom", "react-router-dom", "axios"],
          },
        },
      },
    },
    preview: { headers },
    server: {
      headers,
      host: "127.0.0.1",
      port: 5173,
      strictPort: true,
      // The browser calls /api on the Vite origin; Vite forwards to FastAPI, so no CORS in dev.
      proxy: {
        "/api": { target: env.VITE_BACKEND_ORIGIN || "http://127.0.0.1:8000", changeOrigin: true },
      },
    },
  };
});
