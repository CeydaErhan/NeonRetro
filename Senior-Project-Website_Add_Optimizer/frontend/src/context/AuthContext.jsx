import { createContext, useContext, useEffect, useMemo, useState } from "react";
import api from "../api/axios";

const AuthContext = createContext(null);
const TOKEN_KEY = "optimizer_jwt_token";

function buildAuthorizationHeader(token) {
  if (!token) {
    return null;
  }

  return token.startsWith("Bearer ") ? token : `Bearer ${token}`;
}

// Provides authentication state and actions to the full application tree.
export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [isLoading, setIsLoading] = useState(false);

  // Keeps local storage and axios auth header in sync with token state.
  useEffect(() => {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
      api.defaults.headers.common.Authorization = buildAuthorizationHeader(token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
      delete api.defaults.headers.common.Authorization;
    }
  }, [token]);

  // Performs login request, then stores received JWT token.
  const login = async (email, password) => {
    setIsLoading(true);
    try {
      const response = await api.post("/auth/login", { email, password });
      const accessToken = response?.data?.access_token;
      if (!accessToken) {
        throw new Error("Token not returned by server.");
      }
      api.defaults.headers.common.Authorization = `Bearer ${accessToken}`;
      setToken(accessToken);
      return response.data;
    } finally {
      setIsLoading(false);
    }
  };

  // Clears JWT from state and local storage.
  const logout = async () => {
    try {
      if (token) {
        await api.post("/auth/logout");
      }
    } catch {
      // Ignores logout API errors because client-side token removal is authoritative.
    } finally {
      setToken(null);
    }
  };

  const value = useMemo(
    () => ({
      token,
      isAuthenticated: Boolean(token),
      isLoading,
      login,
      logout
    }),
    [token, isLoading]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Returns auth context for easy access in pages and components.
export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }
  return ctx;
}
