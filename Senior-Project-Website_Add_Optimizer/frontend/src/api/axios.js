import axios from "axios";

// Shared axios instance used for all backend API requests.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || "/api",
  headers: {
    "Content-Type": "application/json"
  }
});

export default api;
