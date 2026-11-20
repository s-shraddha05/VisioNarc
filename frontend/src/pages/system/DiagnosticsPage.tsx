import { AlertTriangle, CheckCircle2, Database, Globe, MonitorSmartphone, RefreshCw, Server, XCircle } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { PageHeader } from "@/components/common/PageHeader";
import { ErrorState } from "@/components/common/States";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/useApi";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { mediaSupported, recorderSupported } from "@/lib/media";

type PermissionState = "granted" | "denied" | "prompt" | "unknown";

async function queryPermission(name: "camera" | "microphone"): Promise<PermissionState> {
  try {
    const result = await navigator.permissions.query({ name: name as PermissionName });
    return result.state;
  } catch {
    return "unknown"; // e.g. Firefox does not expose camera/microphone permission queries
  }
}

export function DiagnosticsPage() {
  useDocumentTitle("Diagnostics");
  const health = useApi(api.health, []);
  const ready = useApi(api.readiness, []);
  const diag = useApi(api.diagnostics, []);
  const [perms, setPerms] = useState<{ camera: PermissionState; microphone: PermissionState } | null>(null);
  const [checkedAt, setCheckedAt] = useState(() => new Date().toISOString());

  useEffect(() => {
    void Promise.all([queryPermission("camera"), queryPermission("microphone")]).then(([camera, microphone]) =>
      setPerms({ camera, microphone }),
    );
  }, [checkedAt]);

  function refresh() {
    health.reload();
    ready.reload();
    diag.reload();
    setCheckedAt(new Date().toISOString());
  }

  const d = diag.data;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="System"
        title="Health & diagnostics"
        description={`Live checks of the API, database and this browser. Last checked ${formatDateTime(checkedAt)}.`}
        actions={
          <Button variant="outline" onClick={refresh}>
            <RefreshCw className={diag.loading ? "animate-spin" : undefined} /> Re-run checks
          </Button>
        }
      />

      {d && d.errors.length > 0 && (
        <Alert variant="destructive">
          <AlertTriangle />
          <ul className="space-y-1">
            {d.errors.map((e) => (
              <li key={e}>{e}</li>
            ))}
          </ul>
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="size-5 text-primary" /> API server
            </CardTitle>
          </CardHeader>
          <CardContent>
            {health.error ? (
              <ErrorState message={health.error} onRetry={health.reload} />
            ) : !health.data || !d ? (
              <Skeleton className="h-40" />
            ) : (
              <dl className="divide-y text-sm">
                <Row k="Status" v={<Status ok />} />
                <Row k="Application" v={health.data.full_name} />
                <Row k="Version" v={health.data.version} />
                <Row k="Environment" v={health.data.environment} />
                <Row k="Python" v={d.python_version} />
                <Row k="Server time" v={formatDateTime(health.data.server_time)} />
              </dl>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="size-5 text-primary" /> Database
            </CardTitle>
          </CardHeader>
          <CardContent>
            {diag.error ? (
              <ErrorState message={diag.error} onRetry={diag.reload} />
            ) : !d || !ready.data ? (
              <Skeleton className="h-40" />
            ) : (
              <dl className="divide-y text-sm">
                <Row k="Readiness" v={<Status ok={ready.data.database === "ok"} />} />
                <Row k="Engine" v={`${d.database_dialect} ${d.database_server_version ?? ""}`} />
                <Row k="Schema revision" v={`${d.migration_current ?? "none"} (latest ${d.migration_head ?? "?"})`} />
                <Row k="Migrations" v={<Status ok={d.migrations_up_to_date} okText="Up to date" badText="Upgrade needed" />} />
                <Row k="Administrators" v={d.admin_count ?? "—"} />
              </dl>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MonitorSmartphone className="size-5 text-primary" /> This browser
            </CardTitle>
            <CardDescription>Needed for webcam and microphone capture.</CardDescription>
          </CardHeader>
          <CardContent>
            <dl className="divide-y text-sm">
              <Row k="Secure context" v={<Status ok={window.isSecureContext} okText="Yes" badText="No (use localhost or https)" />} />
              <Row k="Camera / microphone API" v={<Status ok={mediaSupported()} okText="Supported" badText="Not supported" />} />
              <Row k="MediaRecorder" v={<Status ok={recorderSupported()} okText="Supported" badText="Not supported" />} />
              <Row k="Camera permission" v={perms ? <Perm state={perms.camera} /> : "…"} />
              <Row k="Microphone permission" v={perms ? <Perm state={perms.microphone} /> : "…"} />
            </dl>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="size-5 text-primary" /> Privacy configuration
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!d ? (
              <Skeleton className="h-24" />
            ) : (
              <dl className="divide-y text-sm">
                <Row k="Raw media storage" v={d.store_raw_media ? "Enabled" : "Disabled (features only)"} />
                <Row k="Default retention" v={`${d.data_retention_days} days`} />
              </dl>
            )}
            <p className="mt-3 text-xs text-muted-foreground">
              Secrets such as database credentials and signing keys are never sent to the browser.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-2">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className="text-right font-medium">{v}</dd>
    </div>
  );
}

function Status({ ok = false, okText = "Healthy", badText = "Unavailable" }: { ok?: boolean; okText?: string; badText?: string }) {
  return ok ? (
    <span className="inline-flex items-center gap-1 text-success">
      <CheckCircle2 className="size-4" /> {okText}
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-destructive">
      <XCircle className="size-4" /> {badText}
    </span>
  );
}

function Perm({ state }: { state: PermissionState }) {
  const text = { granted: "Granted", denied: "Blocked", prompt: "Will ask", unknown: "Unknown" }[state];
  const cls = state === "granted" ? "text-success" : state === "denied" ? "text-destructive" : "text-muted-foreground";
  return <span className={cls}>{text}</span>;
}
