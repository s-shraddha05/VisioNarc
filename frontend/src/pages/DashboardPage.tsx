import {
  Activity,
  AudioLines,
  BarChart3,
  CheckCircle2,
  ClipboardList,
  Database,
  FilePlus2,
  FolderOpen,
  Layers,
  RefreshCw,
  ScanFace,
  Server,
  XCircle,
} from "lucide-react";
import { Link } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAuth } from "@/auth/useAuth";
import { ResearchNotice } from "@/components/common/Notices";
import { StatCard } from "@/components/common/StatCard";
import { StatusBadge } from "@/components/common/StatusBadge";
import { EmptyState, ErrorState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/useApi";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api } from "@/lib/api";
import { APP_FULL_NAME } from "@/lib/brand";
import { describeAction, formatRelative } from "@/lib/format";
import { SESSION_STATUSES } from "@/lib/types";

const dayLabel = new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric" });

export function DashboardPage() {
  useDocumentTitle("Dashboard");
  const { admin } = useAuth();
  const summary = useApi(api.dashboard, []);
  const ready = useApi(api.readiness, []);
  const diag = useApi(api.diagnostics, []);

  const reloadAll = () => {
    summary.reload();
    ready.reload();
    diag.reload();
  };

  const s = summary.data;
  const chartData = (s?.sessions_per_day ?? []).map((d) => ({
    label: dayLabel.format(new Date(`${d.date}T00:00:00`)),
    count: d.count,
  }));
  const chartHasData = chartData.some((d) => d.count > 0);

  return (
    <div className="space-y-8">
      <section className="relative overflow-hidden rounded-2xl border bg-card p-6 sm:p-8">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -right-24 -top-24 size-72 rounded-full opacity-60 blur-3xl"
          style={{ background: "radial-gradient(circle, oklch(0.75 0.1 186 / 0.45), transparent 70%)" }}
        />
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-2">
            <p className="text-sm text-muted-foreground">
              Welcome back, <span className="font-medium text-foreground">{admin?.full_name || admin?.username}</span>
            </p>
            <h1 className="max-w-2xl text-2xl font-semibold tracking-tight text-balance sm:text-3xl">{APP_FULL_NAME}</h1>
            <p className="max-w-2xl text-sm text-muted-foreground">
              Experimental multimodal research workspace. All figures below are counted live from the database.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button asChild>
              <Link to="/analysis/new">
                <FilePlus2 /> New analysis
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link to="/history">
                <FolderOpen /> History
              </Link>
            </Button>
            <Button variant="ghost" size="icon" aria-label="Refresh dashboard" onClick={reloadAll}>
              <RefreshCw className={summary.loading ? "animate-spin" : undefined} />
            </Button>
          </div>
        </div>
      </section>

      <ResearchNotice />

      {summary.error ? (
        <ErrorState message={summary.error} onRetry={summary.reload} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {!s ? (
            Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-[118px] rounded-xl" />)
          ) : (
            <>
              <StatCard
                label="Analysis sessions"
                value={s.totals.sessions}
                icon={FolderOpen}
                hint={`${s.totals.active_sessions} active · ${s.totals.completed_sessions} completed`}
              />
              <StatCard label="Face measurements" value={s.totals.face_measurements} icon={ScanFace} />
              <StatCard label="Motion measurements" value={s.totals.motion_measurements} icon={Activity} />
              <StatCard
                label="Voice measurements"
                value={s.totals.voice_measurements}
                icon={AudioLines}
                hint={`${s.totals.combined_results} combined result${s.totals.combined_results === 1 ? "" : "s"}`}
              />
            </>
          )}
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Sessions created</CardTitle>
            <CardDescription>Last 14 days (UTC)</CardDescription>
          </CardHeader>
          <CardContent>
            {!s ? (
              <Skeleton className="h-64 w-full" />
            ) : chartHasData ? (
              <div className="h-64" role="img" aria-label="Bar chart of analysis sessions created per day">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 0, left: -20 }}>
                    <CartesianGrid vertical={false} stroke="var(--border)" />
                    <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={12} stroke="var(--muted-foreground)" interval="preserveStartEnd" />
                    <YAxis allowDecimals={false} tickLine={false} axisLine={false} fontSize={12} stroke="var(--muted-foreground)" />
                    <Tooltip
                      cursor={{ fill: "var(--muted)" }}
                      contentStyle={{ background: "var(--card)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
                      formatter={(v) => [v, "Sessions"]}
                    />
                    <Bar dataKey="count" fill="var(--primary)" radius={[4, 4, 0, 0]} maxBarSize={36} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyState
                icon={BarChart3}
                title="No sessions in the last 14 days"
                description="The trend appears once analysis sessions are created."
                action={
                  <Button asChild size="sm">
                    <Link to="/analysis/new">Create the first session</Link>
                  </Button>
                }
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Sessions by status</CardTitle>
          </CardHeader>
          <CardContent>
            {!s ? (
              <Skeleton className="h-48 w-full" />
            ) : s.totals.sessions === 0 ? (
              <EmptyState icon={Layers} title="No sessions yet" className="py-8" />
            ) : (
              <ul className="space-y-3">
                {SESSION_STATUSES.filter((st) => s.sessions_by_status[st]).map((st) => {
                  const n = s.sessions_by_status[st] ?? 0;
                  return (
                    <li key={st} className="space-y-1.5">
                      <div className="flex items-center justify-between text-sm">
                        <StatusBadge status={st} />
                        <span className="tabular-nums text-muted-foreground">{n}</span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                        <div className="h-full rounded-full bg-primary/70" style={{ width: `${(n / s.totals.sessions) * 100}%` }} />
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <div className="space-y-1.5">
              <CardTitle>Recent activity</CardTitle>
              <CardDescription>From the audit log</CardDescription>
            </div>
            <Button asChild variant="ghost" size="sm">
              <Link to="/audit">
                <ClipboardList /> View all
              </Link>
            </Button>
          </CardHeader>
          <CardContent>
            {!s ? (
              <Skeleton className="h-40 w-full" />
            ) : s.recent_activity.length === 0 ? (
              <EmptyState title="No activity recorded" className="py-8" />
            ) : (
              <ol className="relative space-y-4 border-l pl-5">
                {s.recent_activity.map((e) => (
                  <li key={e.id} className="relative">
                    <span className="absolute -left-[25px] top-1.5 size-2.5 rounded-full border-2 border-card bg-primary" />
                    <p className="text-sm font-medium">{describeAction(e.action)}</p>
                    <p className="text-xs text-muted-foreground">
                      {e.admin_username ?? "unknown user"} · {formatRelative(e.created_at)}
                      {typeof e.details?.reference_code === "string" && ` · ${e.details.reference_code}`}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center justify-between space-y-0">
            <CardTitle>System health</CardTitle>
            <Button asChild variant="ghost" size="sm">
              <Link to="/diagnostics">Details</Link>
            </Button>
          </CardHeader>
          <CardContent className="space-y-3">
            <HealthRow icon={Server} label="API server" ok={!ready.error && !!ready.data} pending={ready.loading} />
            <HealthRow icon={Database} label="Database" ok={ready.data?.database === "ok"} pending={ready.loading} />
            <HealthRow icon={Layers} label="Migrations current" ok={!!diag.data?.migrations_up_to_date} pending={diag.loading} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function HealthRow({ icon: Icon, label, ok, pending }: { icon: typeof Server; label: string; ok: boolean; pending: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-lg border px-3 py-2.5 text-sm">
      <span className="flex items-center gap-2">
        <Icon className="size-4 text-muted-foreground" /> {label}
      </span>
      {pending ? (
        <Skeleton className="h-4 w-16" />
      ) : ok ? (
        <span className="flex items-center gap-1 font-medium text-success">
          <CheckCircle2 className="size-4" /> OK
        </span>
      ) : (
        <span className="flex items-center gap-1 font-medium text-destructive">
          <XCircle className="size-4" /> Problem
        </span>
      )}
    </div>
  );
}
