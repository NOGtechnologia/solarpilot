"use client";

import { Play, Plus, SolarRoof } from "@phosphor-icons/react";
import Link from "next/link";
import { useState } from "react";

import { useApp } from "@/components/providers";
import { Button, buttonVariants } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export function EmptyState() {
  const { t } = useI18n();
  const { refreshSites, isAdmin } = useApp();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function startDemo() {
    setBusy(true);
    setError(null);
    try {
      await api.post("/api/demo");
      await refreshSites();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="relative mx-auto mt-6 max-w-xl overflow-hidden rounded-[24px] border border-border bg-card p-8 text-center">
      <div aria-hidden className="pointer-events-none absolute inset-x-0 -top-24 mx-auto h-48 w-48 rounded-full bg-solar/30 blur-3xl" />
      <div className="relative mx-auto mb-5 flex h-24 w-24 items-center justify-center rounded-[28px] border border-solar/30 bg-solar/10">
        <SolarRoof size={60} className="text-solar" aria-hidden />
      </div>
      <h1 className="relative text-2xl font-semibold tracking-tight">{t("empty.title")}</h1>
      <p className="relative mx-auto mt-2 max-w-md text-sm leading-relaxed text-muted">{t("empty.text")}</p>
      {isAdmin && (
        <div className="relative mt-6 flex flex-col justify-center gap-2 sm:flex-row">
          <Button variant="primary" size="lg" onClick={startDemo} disabled={busy}>
            <Play size={18} />
            {busy ? t("empty.demo_loading") : t("empty.demo")}
          </Button>
          <Link href="/setup/" className={cn(buttonVariants({ variant: "secondary", size: "lg" }))}>
            <Plus size={18} />
            {t("empty.setup")}
          </Link>
        </div>
      )}
      {error && <p className="mt-3 text-sm text-danger">{error}</p>}
    </section>
  );
}
