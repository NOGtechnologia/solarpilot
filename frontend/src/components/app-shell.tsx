"use client";

import { BarChart3, CloudSun, Languages, LayoutDashboard, LogOut, Moon, Settings, Sun } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useEffect, useState, type ReactNode } from "react";

import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

import { Logo } from "./logo";
import { useApp } from "./providers";

const NAV = [
  { href: "/", key: "nav.dashboard", icon: LayoutDashboard },
  { href: "/forecast/", key: "nav.forecast", icon: CloudSun },
  { href: "/reports/", key: "nav.reports", icon: BarChart3 },
  { href: "/settings/", key: "nav.settings", icon: Settings },
] as const;

function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const { t } = useI18n();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const dark = !mounted || resolvedTheme === "dark";
  return (
    <button
      type="button"
      onClick={() => setTheme(dark ? "light" : "dark")}
      className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-xl text-muted hover:bg-card-2 hover:text-fg"
      aria-label={t("theme.toggle")}
      title={t("theme.toggle")}
    >
      {dark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}

function LangToggle() {
  const { lang, setLang, t } = useI18n();
  return (
    <button
      type="button"
      onClick={() => setLang(lang === "de" ? "en" : "de")}
      className="flex h-9 cursor-pointer items-center gap-1 rounded-xl px-2 text-[13px] font-medium text-muted hover:bg-card-2 hover:text-fg"
      aria-label={t("lang.toggle")}
      title={t("lang.toggle")}
    >
      <Languages size={16} />
      {lang.toUpperCase()}
    </button>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname() ?? "/";
  const { t } = useI18n();
  const { auth, refreshAuth } = useApp();
  const router = useRouter();
  const bare = pathname.startsWith("/login");

  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  async function logout() {
    await api.post("/api/auth/logout");
    await refreshAuth();
    router.replace("/login/");
  }

  return (
    <div className="min-h-dvh">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-lg focus:bg-card focus:px-3 focus:py-2">
        Skip to content
      </a>
      <header className="sticky top-0 z-30 border-b border-border/70 bg-bg/80 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-3 px-4">
          <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
            <Logo />
            <span>SolarPilot</span>
          </Link>
          {!bare && (
            <nav aria-label="Hauptnavigation" className="ml-6 hidden items-center gap-1 md:flex">
              {NAV.map((n) => (
                <Link
                  key={n.href}
                  href={n.href}
                  aria-current={isActive(n.href) ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
                    isActive(n.href) ? "bg-card-2 text-fg" : "text-muted hover:text-fg",
                  )}
                >
                  <n.icon size={16} />
                  {t(n.key)}
                </Link>
              ))}
            </nav>
          )}
          <div className="ml-auto flex items-center gap-1">
            <LangToggle />
            <ThemeToggle />
            {auth?.authenticated && !bare && (
              <button
                type="button"
                onClick={logout}
                className="flex h-9 w-9 cursor-pointer items-center justify-center rounded-xl text-muted hover:bg-card-2 hover:text-fg"
                aria-label={t("nav.logout")}
                title={t("nav.logout")}
              >
                <LogOut size={17} />
              </button>
            )}
          </div>
        </div>
      </header>
      <main id="main" className={cn("mx-auto max-w-7xl px-4 pt-4", bare ? "pb-10" : "pb-28 md:pb-10")}>
        {children}
      </main>
      {!bare && (
        <nav
          aria-label="Navigation"
          className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-bg/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-md md:hidden"
        >
          <div className="mx-auto grid max-w-md grid-cols-4">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                aria-current={isActive(n.href) ? "page" : undefined}
                className={cn(
                  "flex flex-col items-center gap-0.5 py-2.5 text-[11px] font-medium",
                  isActive(n.href) ? "text-solar-text" : "text-muted",
                )}
              >
                <n.icon size={20} />
                {t(n.key)}
              </Link>
            ))}
          </div>
        </nav>
      )}
    </div>
  );
}
