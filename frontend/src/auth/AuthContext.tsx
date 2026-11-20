import { useCallback, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { AuthContext, type AuthStatus } from "@/auth/context";
import { classifySessionCheckError } from "@/auth/sessionCheck";
import { api, setUnauthorizedHandler, tokenStore } from "@/lib/api";
import type { AdminProfile } from "@/lib/types";

// Only components are exported here (React Fast Refresh requirement); the context object is in
// auth/context.ts and the hook in auth/useAuth.ts.
export function AuthProvider({ children }: { children: ReactNode }) {
  const [admin, setAdmin] = useState<AdminProfile | null>(null);
  const [status, setStatus] = useState<AuthStatus>(tokenStore.get() ? "checking" : "anonymous");

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setAdmin(null);
      setStatus("anonymous");
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  // Validate a token left from earlier in this tab against the server.
  useEffect(() => {
    if (status !== "checking") return;
    api
      .me()
      .then((profile) => {
        setAdmin(profile);
        setStatus("authenticated");
      })
      .catch((err) => {
        if (classifySessionCheckError(err) === "unauthorized") {
          tokenStore.clear(); // genuine 401: the token is invalid, expired or revoked
          setStatus("anonymous");
        } else {
          setStatus("unavailable"); // server unreachable: keep the token so the user can retry
        }
      });
  }, [status]);

  const login = useCallback(async (username: string, password: string) => {
    const result = await api.login(username, password);
    tokenStore.set(result.access_token);
    setAdmin(result.admin);
    setStatus("authenticated");
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      tokenStore.clear();
      setAdmin(null);
      setStatus("anonymous");
    }
  }, []);

  const retry = useCallback(() => setStatus(tokenStore.get() ? "checking" : "anonymous"), []);

  const value = useMemo(
    () => ({ status, admin, login, logout, retry, setAdmin }),
    [status, admin, login, logout, retry],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
