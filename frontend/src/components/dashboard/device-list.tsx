"use client";

import { Cpu } from "lucide-react";

import { Card, CardHeader } from "@/components/ui/card";
import { fmtPower, fmtRelative } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { DeviceStatus } from "@/lib/types";
import { cn } from "@/lib/utils";

export function DeviceList({ devices }: { devices: DeviceStatus[] }) {
  const { t, lang } = useI18n();
  if (!devices.length) return null;
  return (
    <Card>
      <CardHeader title={t("dash.devices")} icon={<Cpu size={14} />} />
      <ul className="space-y-1.5">
        {devices.map((d) => {
          const p = fmtPower(d.snapshot?.pv_power_w ?? d.snapshot?.grid_power_w ?? null, lang);
          return (
            <li key={d.id} className="flex items-center justify-between gap-3 rounded-xl bg-card-2 px-3 py-2 text-sm">
              <span className="flex min-w-0 items-center gap-2">
                <span
                  className={cn("h-2 w-2 shrink-0 rounded-full", d.online ? "bg-success" : "bg-danger")}
                  aria-label={d.online ? t("common.online") : t("common.offline")}
                />
                <span className="truncate">{d.name}</span>
                <span className="hidden text-[11px] text-muted sm:inline">{t(`role.${d.role}`)}</span>
              </span>
              <span className="num shrink-0 text-[13px] text-muted">
                {d.online
                  ? `${p.value} ${p.unit}`
                  : d.last_seen
                    ? t("common.offline_since", { time: fmtRelative(d.last_seen, lang) })
                    : d.error ?? t("common.offline")}
              </span>
            </li>
          );
        })}
      </ul>
    </Card>
  );
}
