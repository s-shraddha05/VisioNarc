import { createContext } from "react";
import type { AdminProfile } from "@/lib/types";

// The context object lives in its own non-component module so that hot-reloading
// AuthContext.tsx (the provider) never creates a second, mismatched context.

/** "unavailable": a saved token exists but the server could not be reached to check it. */
export type AuthStatus = "checking" | "authenticated" | "anonymous" | "unavailable";

export interface AuthContextValue {
  status: AuthStatus;
  admin: AdminProfile | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  /** Re-check the saved token after the server was unavailable. */
  retry: () => void;
  /** Replace the cached profile after a successful profile update. */
  setAdmin: (admin: AdminProfile) => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
