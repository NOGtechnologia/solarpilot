"use client";

import { MapPin } from "lucide-react";

import { useApp } from "@/components/providers";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/utils";

export function SiteSwitcher() {
  const { sites, site, setSite } = useApp();
  const { t } = useI18n();
  if (!sites || sites.length < 2) {
    const only = sites?.[0];
    return only ? (
      <div className="flex items-center gap-1.5 text-sm text-muted">
        <MapPin size={14} /> {only.name}
      </div>
    ) : null;
  }
  const opts = [{ id: "all", name: t("common.all_sites") }, ...sites.map((s) => ({ id: String(s.id), name: s.name }))];
  return (
    <div role="tablist" aria-label={t("common.all_sites")} className="-mx-1 flex gap-1 overflow-x-auto px-1 pb-1">
      {opts.map((o) => (
        <button
          key={o.id}
          role="tab"
          type="button"
          aria-selected={site === o.id}
          onClick={() => setSite(o.id)}
          className={cn(
            "shrink-0 cursor-pointer rounded-full border px-3.5 py-1.5 text-[13px] font-medium transition-colors",
            site === o.id ? "border-solar/60 bg-solar/15 text-fg" : "border-border text-muted hover:text-fg",
          )}
        >
          {o.name}
        </button>
      ))}
    </div>
  );
}
