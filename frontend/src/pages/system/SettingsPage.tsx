import { CheckCircle2, KeyRound, Loader2, Lock, Save, ShieldCheck, UserRound, XCircle } from "lucide-react";
import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { useAuth } from "@/auth/useAuth";
import { PageHeader } from "@/components/common/PageHeader";
import { ActiveSessionsCard } from "@/components/system/ActiveSessionsCard";
import { RetentionPanel } from "@/components/system/RetentionPanel";
import { ErrorState, LoadingState } from "@/components/common/States";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { FieldError } from "@/components/ui/form-controls";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useApi } from "@/hooks/useApi";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

const RULES = [
  { label: "At least 12 characters", ok: (pw: string) => pw.length >= 12 },
  { label: "At least one letter and one digit", ok: (pw: string) => /[A-Za-z]/.test(pw) && /\d/.test(pw) },
  { label: "At most 72 bytes", ok: (pw: string) => new TextEncoder().encode(pw).length <= 72 },
  { label: "No leading or trailing spaces", ok: (pw: string) => pw === pw.trim() },
];

export function SettingsPage() {
  useDocumentTitle("Settings");
  const settings = useApi(api.settings, []);
  const cfg = settings.data;

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="System" title="Settings" description="Your administrator account and the server's effective configuration." />
      <div className="grid gap-6 *:min-w-0 xl:grid-cols-2">
        <ProfileCard />
        <PasswordCard />
      </div>
      {settings.error ? (
        <ErrorState message={settings.error} onRetry={settings.reload} />
      ) : !cfg ? (
        <LoadingState />
      ) : (
        <div className="grid gap-6 *:min-w-0 xl:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <ShieldCheck className="size-5 text-primary" /> Privacy & retention
              </CardTitle>
              <CardDescription>Read-only. To change these, edit backend/.env and restart the backend.</CardDescription>
            </CardHeader>
            <CardContent>
              <dl className="divide-y text-sm">
                <Row k="Raw media storage" hint="STORE_RAW_MEDIA" v={<Flag on={cfg.store_raw_media} onText="Enabled (with consent)" offText="Disabled (features only)" />} />
                <Row k="Default retention" hint="DATA_RETENTION_DAYS" v={`${cfg.data_retention_days} days`} />
                <Row
                  k="Automatic deletion"
                  hint="RETENTION_AUTO_PURGE. When off, use Retention purge below or python -m scripts.purge_expired."
                  v={<Flag on={cfg.retention_enforcement} onText="On (runs at startup and periodically)" offText="Off (manual purge only)" />}
                />
                <Row k="Consent text version" v={cfg.consent_text_version} />
              </dl>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Lock className="size-5 text-primary" /> Security policy
              </CardTitle>
              <CardDescription>Read-only. Configured in backend/.env.</CardDescription>
            </CardHeader>
            <CardContent>
              <dl className="divide-y text-sm">
                <Row k="Session lifetime" hint="ACCESS_TOKEN_EXPIRE_MINUTES" v={`${cfg.access_token_expire_minutes} minutes`} />
                <Row k="Lock after" hint="LOGIN_MAX_FAILED_ATTEMPTS" v={`${cfg.login_max_failed_attempts} failed sign-ins`} />
                <Row k="Lock duration" hint="LOGIN_LOCKOUT_MINUTES" v={`${cfg.login_lockout_minutes} minutes`} />
                <Row k="Environment" v={cfg.environment} />
              </dl>
            </CardContent>
          </Card>
          <RetentionPanel />
          <ActiveSessionsCard />
          <Card className="xl:col-span-2">
            <CardHeader>
              <CardTitle>Analysis capabilities</CardTitle>
              <CardDescription>Reported by the server. Features shown as unavailable cannot be started anywhere in the UI.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
              {(
                [
                  ["Face analysis", cfg.capabilities.face_analysis],
                  ["Motion analysis", cfg.capabilities.motion_analysis],
                  ["Voice analysis", cfg.capabilities.voice_analysis],
                  ["Multimodal summary (no score)", cfg.capabilities.multimodal_analysis],
                  ["PDF reports", cfg.capabilities.pdf_reports],
                ] as const
              ).map(([label, on]) => (
                <div key={label} className="space-y-1 rounded-lg border p-3 text-sm">
                  <p className="font-medium">{label}</p>
                  <Flag on={on} onText="Available" offText="Not yet available" />
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}

function ProfileCard() {
  const { admin, setAdmin } = useAuth();
  const [name, setName] = useState(admin?.full_name ?? "");
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  useEffect(() => setName(admin?.full_name ?? ""), [admin?.full_name]);

  async function save(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMsg(null);
    try {
      setAdmin(await api.updateProfile(name.trim() || null));
      setMsg({ ok: true, text: "Profile saved." });
    } catch (err) {
      setMsg({ ok: false, text: errorMessage(err) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserRound className="size-5 text-primary" /> Profile
        </CardTitle>
        <CardDescription>
          Signed in as <strong>{admin?.username}</strong>. Last sign-in {formatDateTime(admin?.last_login_at)}.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={save} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="full-name">Display name</Label>
            <Input id="full-name" maxLength={100} value={name} onChange={(e) => setName(e.target.value)} placeholder="Optional" />
          </div>
          {msg && <Alert variant={msg.ok ? "default" : "destructive"}>{msg.text}</Alert>}
          <Button type="submit" disabled={saving || name.trim() === (admin?.full_name ?? "")}>
            {saving ? <Loader2 className="animate-spin" /> : <Save />} Save profile
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function PasswordCard() {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [touched, setTouched] = useState(false);
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const strong = RULES.every((r) => r.ok(next));
  const mismatch = (touched || confirm.length > 0) && confirm !== next;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setTouched(true);
    if (!current || !strong || next !== confirm) return;
    setSaving(true);
    setMsg(null);
    try {
      const res = await api.changePassword(current, next);
      setMsg({ ok: true, text: res.message });
      setCurrent("");
      setNext("");
      setConfirm("");
      setTouched(false);
    } catch (err) {
      setMsg({ ok: false, text: errorMessage(err) });
    } finally {
      setSaving(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <KeyRound className="size-5 text-primary" /> Change password
        </CardTitle>
        <CardDescription>After a change, your other signed-in sessions are signed out.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={submit} className="space-y-4" noValidate>
          <div className="space-y-2">
            <Label htmlFor="pw-current">Current password</Label>
            <Input id="pw-current" type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} maxLength={128} aria-invalid={touched && !current} />
            <FieldError>{touched && !current ? "Enter your current password." : null}</FieldError>
          </div>
          <div className="space-y-2">
            <Label htmlFor="pw-new">New password</Label>
            <Input id="pw-new" type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} maxLength={128} aria-describedby="pw-rules" aria-invalid={touched && !strong} />
            <ul id="pw-rules" className="space-y-0.5 text-xs">
              {RULES.map((rule) => {
                const ok = next.length > 0 && rule.ok(next);
                return (
                  <li key={rule.label} className={`flex items-center gap-1 ${ok ? "text-success" : "text-muted-foreground"}`}>
                    {ok ? <CheckCircle2 className="size-3.5" /> : <XCircle className="size-3.5" />} {rule.label}
                  </li>
                );
              })}
            </ul>
          </div>
          <div className="space-y-2">
            <Label htmlFor="pw-confirm">Confirm new password</Label>
            <Input id="pw-confirm" type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} maxLength={128} aria-invalid={mismatch} />
            <FieldError>{mismatch ? "Passwords do not match." : null}</FieldError>
          </div>
          {msg && <Alert variant={msg.ok ? "default" : "destructive"}>{msg.text}</Alert>}
          <Button type="submit" disabled={saving}>
            {saving ? <Loader2 className="animate-spin" /> : <KeyRound />} Change password
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function Row({ k, v, hint }: { k: string; v: ReactNode; hint?: string }) {
  return (
    <div className="flex flex-col gap-1 py-2.5 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
      <dt>
        <span className="text-muted-foreground">{k}</span>
        {hint && <span className="block text-xs text-muted-foreground/70">{hint}</span>}
      </dt>
      <dd className="shrink-0 font-medium sm:text-right">{v}</dd>
    </div>
  );
}

function Flag({ on, onText, offText }: { on: boolean; onText: string; offText: string }) {
  return on ? (
    <span className="inline-flex items-center gap-1 text-success">
      <CheckCircle2 className="size-4" /> {onText}
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 text-muted-foreground">
      <XCircle className="size-4" /> {offText}
    </span>
  );
}
