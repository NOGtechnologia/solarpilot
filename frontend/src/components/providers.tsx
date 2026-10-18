"use client";

import { ThemeProvider } from "next-themes";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api } from "@/lib/api";
import { I18nProvider } from "@/lib/i18n";
import type { AuthStatus, Site } from "@/lib/types";
import { storageGet, storageSet } from "@/lib/utils";

interface AppCtx {
  auth: AuthStatus | null;
  refreshAuth: () => Promise<void>;
  sites: Site[] | undefined;
  refreshSites: () => Promise<void>;
  site: string; // "all" oder ID
  setSite: (s: string) => void;
  isAdmin: boolean;
}

const Ctx = createContext<AppCtx | null>(null);

export function useApp() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useApp außerhalb des Providers");
  return c;
}

function AppProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [sites, setSites] = useState<Site[] | undefined>(undefined);
  const [site, setSiteState] = useState("all");
  const router = useRouter();
  const pathname = usePathname();

  const refreshAuth = useCallback(async () => {
    try {
      setAuth(await api.get<AuthStatus>("/api/auth/status"));
    } catch {
      setAuth({ has_users: true, authenticated: false, user: null, public_dashboard: false, language: "de" });
    }
  }, []);

  const refreshSites = useCallback(async () => {
    try {
      setSites(await api.get<Site[]>("/api/sites"));
    } catch {
      setSites([]);
    }
  }, []);

  useEffect(() => {
    refreshAuth();
    const s = storageGet("sp_site");
    if (s) setSiteState(s);
  }, [refreshAuth]);

  const canView = !!auth && (auth.authenticated || auth.public_dashboard);

  useEffect(() => {
    if (!auth) return;
    const onLogin = pathname?.startsWith("/login");
    if (!canView && !onLogin) router.replace("/login/");
    if (canView) refreshSites();
  }, [auth, canView, pathname, router, refreshSites]);

  useEffect(() => {
    if (sites && site !== "all" && !sites.some((s) => String(s.id) === site)) setSiteState("all");
  }, [sites, site]);

  const setSite = useCallback((s: string) => {
    setSiteState(s);
    storageSet("sp_site", s);
  }, []);

  const value = useMemo(
    () => ({
      auth,
      refreshAuth,
      sites,
      refreshSites,
      site,
      setSite,
      isAdmin: !!auth?.user?.is_admin,
    }),
    [auth, refreshAuth, sites, refreshSites, site, setSite],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function Providers({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem disableTransitionOnChange>
      <I18nProvider>
        <AppProvider>{children}</AppProvider>
      </I18nProvider>
    </ThemeProvider>
  );
}
