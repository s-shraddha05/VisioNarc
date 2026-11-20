import { Loader2, RefreshCw, ServerCrash } from "lucide-react";
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/auth/useAuth";
import { BrandMark } from "@/components/BrandMark";
import { Button } from "@/components/ui/button";

export function ProtectedRoute() {
  const { status, retry, logout } = useAuth();
  const location = useLocation();

  if (status === "checking") {
    return (
      <div className="flex min-h-svh items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 size-5 animate-spin" /> Checking your session…
      </div>
    );
  }
  if (status === "unavailable") {
    return (
      <div className="flex min-h-svh flex-col items-center justify-center gap-5 px-4 text-center">
        <BrandMark />
        <ServerCrash className="size-8 text-destructive" />
        <div className="max-w-md space-y-2">
          <h1 className="text-xl font-semibold">Cannot reach the VisoNarc server</h1>
          <p className="text-sm text-muted-foreground">
            You are still signed in on this tab. Start the backend (scripts\run_backend.ps1) or check that MySQL is
            running, then retry.
          </p>
        </div>
        <div className="flex flex-wrap justify-center gap-2">
          <Button onClick={retry}>
            <RefreshCw /> Retry
          </Button>
          <Button variant="outline" onClick={() => void logout()}>
            Sign out
          </Button>
        </div>
      </div>
    );
  }
  if (status === "anonymous") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}
