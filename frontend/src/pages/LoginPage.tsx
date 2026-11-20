import { AlertCircle, Eye, EyeOff, Loader2, LogIn, ShieldCheck } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "@/auth/useAuth";
import { BrandMark } from "@/components/BrandMark";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { errorMessage } from "@/lib/api";
import { APP_DISCLAIMER, APP_FULL_NAME, APP_NAME } from "@/lib/brand";

export function LoginPage() {
  const { status, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    document.title = `Sign in · ${APP_FULL_NAME}`;
  }, []);

  if (status === "authenticated") return <Navigate to={from} replace />;

  const usernameError = touched && !username.trim() ? "Enter your username." : null;
  const passwordError = touched && !password ? "Enter your password." : null;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setTouched(true);
    if (!username.trim() || !password) return;
    setSubmitting(true);
    setError(null);
    try {
      await login(username.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(errorMessage(err));
      setPassword("");
      setTouched(false); // the cleared password is not a validation error

    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="grid min-h-svh lg:grid-cols-[1.1fr_1fr]">
      <section className="relative hidden flex-col justify-between overflow-hidden bg-[oklch(0.24_0.05_220)] p-12 text-white lg:flex">
        <div
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            background:
              "radial-gradient(60% 50% at 20% 20%, oklch(0.55 0.12 186 / 0.6), transparent), radial-gradient(50% 40% at 80% 80%, oklch(0.5 0.12 250 / 0.5), transparent)",
          }}
        />
        <div className="relative flex items-center gap-3">
          <BrandMark className="bg-white/15 text-white" />
          <span className="text-lg font-semibold tracking-tight">{APP_NAME}</span>
        </div>
        <div className="relative max-w-lg space-y-5">
          <h1 className="text-4xl font-semibold leading-tight tracking-tight">{APP_FULL_NAME}</h1>
          <p className="text-base text-white/75">
            Multimodal behavioural analysis that combines facial appearance, body motion and voice
            features into a transparent, quality-aware experimental indicator.
          </p>
        </div>
        <p className="relative max-w-lg text-sm text-white/60">{APP_DISCLAIMER}</p>
      </section>

      <section className="flex items-center justify-center px-4 py-10 sm:px-8">
        <div className="w-full max-w-md space-y-6">
          <div className="space-y-3 text-center lg:hidden">
            <BrandMark className="mx-auto" />
            <h1 className="text-2xl font-semibold tracking-tight">{APP_FULL_NAME}</h1>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-xl">
                <ShieldCheck className="size-5 text-primary" /> Administrator sign in
              </CardTitle>
              <CardDescription>Only authorised administrators can access {APP_NAME}.</CardDescription>
            </CardHeader>
            <CardContent>
              <form className="space-y-4" onSubmit={onSubmit} noValidate>
                {error && (
                  <Alert variant="destructive">
                    <AlertCircle />
                    <span>{error}</span>
                  </Alert>
                )}
                <div className="space-y-2">
                  <Label htmlFor="username">Username</Label>
                  <Input
                    id="username"
                    autoComplete="username"
                    autoFocus
                    value={username}
                    maxLength={50}
                    onChange={(e) => setUsername(e.target.value)}
                    aria-invalid={!!usernameError}
                    aria-describedby={usernameError ? "username-error" : undefined}
                    disabled={submitting}
                  />
                  {usernameError && (
                    <p id="username-error" className="text-xs text-destructive">
                      {usernameError}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="password">Password</Label>
                  <div className="relative">
                    <Input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      autoComplete="current-password"
                      value={password}
                      maxLength={128}
                      onChange={(e) => setPassword(e.target.value)}
                      aria-invalid={!!passwordError}
                      aria-describedby={passwordError ? "password-error" : undefined}
                      disabled={submitting}
                      className="pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      className="absolute inset-y-0 right-0 flex w-10 items-center justify-center text-muted-foreground hover:text-foreground"
                      aria-label={showPassword ? "Hide password" : "Show password"}
                    >
                      {showPassword ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                    </button>
                  </div>
                  {passwordError && (
                    <p id="password-error" className="text-xs text-destructive">
                      {passwordError}
                    </p>
                  )}
                </div>
                <Button type="submit" className="w-full" size="lg" disabled={submitting}>
                  {submitting ? <Loader2 className="animate-spin" /> : <LogIn />}
                  {submitting ? "Signing in…" : "Sign in"}
                </Button>
              </form>
            </CardContent>
          </Card>

          <p className="text-center text-xs text-muted-foreground">
            Forgot your password? An operator with server access can reset it with
            <code className="mx-1 rounded bg-muted px-1 py-0.5">python -m scripts.reset_admin_password</code>
            (see README).
          </p>
        </div>
      </section>
    </div>
  );
}
