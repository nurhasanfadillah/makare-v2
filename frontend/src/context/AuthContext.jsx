import { createContext, useContext, useEffect, useState } from "react";
import { api, TOKEN_KEY } from "@/lib/api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!localStorage.getItem(TOKEN_KEY)) {
      setReady(true);
      return;
    }
    api.get("/auth/me").then((r) => setUser(r.data)).catch(() => localStorage.removeItem(TOKEN_KEY)).finally(() => setReady(true));
  }, []);

  const login = async (username, password) => {
    const r = await api.post("/auth/login", { username, password });
    localStorage.setItem(TOKEN_KEY, r.data.token);
    setUser(r.data.user);
    return r.data.user;
  };

  const logout = async ({ revoke = true } = {}) => {
    let revoked = !revoke;
    try {
      if (revoke) { await api.post("/auth/logout"); revoked = true; }
    } catch { /* Local sign-out must still work if the network is unavailable. */ }
    finally {
      localStorage.removeItem(TOKEN_KEY);
      setUser(null);
    }
    return revoked;
  };

  return <AuthCtx.Provider value={{ user, ready, login, logout, isAdmin: user?.role === "admin" }}>{children}</AuthCtx.Provider>;
}

export const useAuth = () => useContext(AuthCtx);
