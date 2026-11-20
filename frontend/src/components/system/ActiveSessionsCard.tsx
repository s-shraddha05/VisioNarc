import { Laptop, Loader2, LogOut } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/auth/useAuth";
import { ErrorState, LoadingState } from "@/components/common/States";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useApi } from "@/hooks/useApi";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

/** Your active sign-ins. Revocation is enforced server-side on the next request of that sign-in. */
export function ActiveSessionsCard() {
  const { logout } = useAuth();
  const sessions = useApi(api.adminSessions, []);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function run(key: string, fn: () => Promise<{ message: string }>, signsOutHere = false) {
    setBusy(key);
    setMsg(null);
    try {
      const res = await fn();
      if (signsOutHere) {
        await logout();
        return;
      }
      setMsg({ ok: true, text: res.message });
      sessions.reload();
    } catch (err) {
      setMsg({ ok: false, text: errorMessage(err) });
    } finally {
      setBusy(null);
    }
  }

  const others = (sessions.data ?? []).filter((s) => !s.current).length;

  return (
    <Card className="xl:col-span-2">
      <CardHeader className="flex-row flex-wrap items-start justify-between gap-3 space-y-0">
        <div className="space-y-1.5">
          <CardTitle className="flex items-center gap-2">
            <Laptop className="size-5 text-primary" /> Active sign-ins
          </CardTitle>
          <CardDescription>Revoked sign-ins stop working on their next request.</CardDescription>
        </div>
        <Button variant="outline" disabled={!!busy || others === 0} onClick={() => run("others", api.revokeOtherAdminSessions)}>
          {busy === "others" ? <Loader2 className="animate-spin" /> : <LogOut />} Sign out other devices
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {msg && <Alert variant={msg.ok ? "default" : "destructive"}>{msg.text}</Alert>}
        {sessions.loading && !sessions.data ? (
          <LoadingState />
        ) : sessions.error ? (
          <ErrorState message={sessions.error} onRetry={sessions.reload} />
        ) : (
          <ul className="divide-y rounded-lg border">
            {(sessions.data ?? []).map((s) => (
              <li key={s.id} className="flex flex-col gap-2 p-3 text-sm sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <p className="flex flex-wrap items-center gap-2 font-medium">
                    Signed in {formatDateTime(s.issued_at)} {s.current && <Badge>This tab</Badge>}
                  </p>
                  <p className="truncate text-xs text-muted-foreground">
                    {s.ip_address ?? "unknown address"} · expires {formatDateTime(s.expires_at)} · {s.user_agent ?? "unknown browser"}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={!!busy}
                  onClick={() => run(`s${s.id}`, () => api.revokeAdminSession(s.id), s.current)}
                >
                  {busy === `s${s.id}` ? <Loader2 className="animate-spin" /> : <LogOut />} {s.current ? "Sign out" : "Revoke"}
                </Button>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
