import { Loader2, LogOut, Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "@/auth/useAuth";
import { BrandMark } from "@/components/BrandMark";
import { NAV_GROUPS } from "@/components/layout/nav";
import { Button } from "@/components/ui/button";
import { APP_NAME } from "@/lib/brand";
import { cn } from "@/lib/utils";

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { admin, logout } = useAuth();
  const [signingOut, setSigningOut] = useState(false);

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center gap-3 px-5">
        <BrandMark className="size-9 bg-[oklch(0.62_0.11_186)] text-white" />
        <div className="leading-tight">
          <p className="text-[15px] font-semibold tracking-tight text-white">{APP_NAME}</p>
          <p className="text-[11px] text-white/55">Voice &amp; motion research</p>
        </div>
      </div>

      <nav aria-label="Main" className="flex-1 space-y-6 overflow-y-auto px-3 py-4">
        {NAV_GROUPS.map((group) => (
          <div key={group.label} className="space-y-1">
            <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-white/40">
              {group.label}
            </p>
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={onNavigate}
                className={({ isActive }) =>
                  cn(
                    "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[oklch(0.7_0.11_186)]",
                    isActive
                      ? "bg-white/10 text-white"
                      : "text-white/65 hover:bg-white/5 hover:text-white",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <span
                      aria-hidden="true"
                      className={cn(
                        "absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-[oklch(0.72_0.12_186)] transition-opacity",
                        isActive ? "opacity-100" : "opacity-0",
                      )}
                    />
                    <item.icon className="size-4 shrink-0" />
                    {item.label}
                  </>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="border-t border-white/10 p-3">
        <div className="mb-2 flex items-center gap-3 rounded-lg px-3 py-2">
          <span className="flex size-8 items-center justify-center rounded-full bg-white/10 text-xs font-semibold uppercase text-white">
            {(admin?.full_name || admin?.username || "?").slice(0, 2)}
          </span>
          <div className="min-w-0 leading-tight">
            <p className="truncate text-sm font-medium text-white">{admin?.full_name || admin?.username}</p>
            <p className="text-xs text-white/50">Administrator</p>
          </div>
        </div>
        <Button
          variant="ghost"
          className="w-full justify-start text-white/75 hover:bg-white/10 hover:text-white"
          disabled={signingOut}
          onClick={async () => {
            setSigningOut(true);
            await logout();
          }}
        >
          {signingOut ? <Loader2 className="animate-spin" /> : <LogOut />} Sign out
        </Button>
      </div>
    </div>
  );
}

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();

  useEffect(() => setMobileOpen(false), [location.pathname]);

  useEffect(() => {
    if (!mobileOpen) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setMobileOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mobileOpen]);

  return (
    <div className="min-h-svh lg:pl-64">
      <a
        href="#main"
        className="sr-only z-50 rounded-md bg-card px-3 py-2 text-sm shadow focus:not-sr-only focus:fixed focus:left-3 focus:top-3"
      >
        Skip to content
      </a>

      {/* Desktop sidebar */}
      <aside className="sidebar-surface fixed inset-y-0 left-0 z-30 hidden w-64 lg:block">
        <SidebarContent />
      </aside>

      {/* Mobile top bar + drawer */}
      <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b bg-card/85 px-4 backdrop-blur lg:hidden">
        <Button
          variant="ghost"
          size="icon"
          aria-label="Open navigation"
          aria-expanded={mobileOpen}
          onClick={() => setMobileOpen(true)}
        >
          <Menu />
        </Button>
        <BrandMark className="size-8" />
        <span className="font-semibold tracking-tight">{APP_NAME}</span>
      </header>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <aside className="sidebar-surface absolute inset-y-0 left-0 w-72 max-w-[85vw] shadow-2xl">
            <Button
              variant="ghost"
              size="icon"
              aria-label="Close navigation"
              className="absolute right-2 top-3 text-white/75 hover:bg-white/10 hover:text-white"
              onClick={() => setMobileOpen(false)}
            >
              <X />
            </Button>
            <SidebarContent onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      )}

      <main id="main" className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 sm:py-8 lg:px-10">
        <Outlet />
      </main>
    </div>
  );
}
