import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      "/health": "http://127.0.0.1:8000",
      "/sentinel": "http://127.0.0.1:8000",
      "/cameras": "http://127.0.0.1:8000",
      "/events": "http://127.0.0.1:8000",
      "/watchlist": "http://127.0.0.1:8000",
      "/alerts": "http://127.0.0.1:8000",
      "/hunt": "http://127.0.0.1:8000",
      "/media": "http://127.0.0.1:8000",
      "/live": "http://127.0.0.1:8000",
    },
  },
});
