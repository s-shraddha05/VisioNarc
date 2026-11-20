import { AlertOctagon, RefreshCw } from "lucide-react";
import { isRouteErrorResponse, useRouteError } from "react-router-dom";
import { BrandMark } from "@/components/BrandMark";
import { Button } from "@/components/ui/button";
import { APP_NAME } from "@/lib/brand";

/** Shown when a page throws while rendering. Never displays stack traces. */
export function RouteErrorPage() {
  const error = useRouteError();
  if (import.meta.env.DEV) console.error(error);
  const status = isRouteErrorResponse(error) ? error.status : null;

  return (
    <div className="flex min-h-svh flex-col items-center justify-center gap-6 px-4 text-center">
      <BrandMark />
      <div className="space-y-2">
        <AlertOctagon className="mx-auto size-8 text-destructive" />
        <h1 className="text-xl font-semibold">{status === 404 ? "Page not found" : "Something went wrong"}</h1>
        <p className="max-w-md text-sm text-muted-foreground">
          {status === 404
            ? `This ${APP_NAME} page does not exist.`
            : "This page hit an unexpected error. Your data is safe; reloading usually fixes it. If it keeps happening, check the browser console and backend log."}
        </p>
      </div>
      <div className="flex gap-2">
        <Button onClick={() => window.location.reload()}>
          <RefreshCw /> Reload
        </Button>
        <Button variant="outline" onClick={() => (window.location.href = "/")}>
          Dashboard
        </Button>
      </div>
    </div>
  );
}
