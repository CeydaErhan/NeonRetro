import axios from "axios";

function getDefaultApiBaseUrl() {
  const hostname = window.location.hostname;

  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return "http://localhost:10000";
  }

  return "/api";
}

// Shared axios instance used for all backend API requests.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || getDefaultApiBaseUrl(),
  headers: {
    "Content-Type": "application/json"
  }
});

export default api;
