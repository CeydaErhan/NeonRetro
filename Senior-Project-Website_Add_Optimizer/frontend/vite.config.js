import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Vite config for React frontend build and dev server.
export default defineConfig({
  plugins: [react()]
});
