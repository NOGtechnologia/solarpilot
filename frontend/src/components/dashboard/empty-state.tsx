"use client";

import { Play, Plus } from "lucide-react";
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
      <svg viewBox="0 0 120 70" className="relative mx-auto mb-5 h-20" aria-hidden>
        <path d="M10 62a50 50 0 0 1 100 0" fill="none" stroke="var(--border)" strokeWidth="3" strokeDasharray="4 6" />
        <circle cx="60" cy="24" r="14" fill="#F5A524" />
        <path d="M20 62h80" stroke="#8B5CF6" strokeWidth="3" strokeLinecap="round" />
      </svg>
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
