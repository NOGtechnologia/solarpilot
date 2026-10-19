import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function KpiTile({
  label,
  value,
  unit,
  sub,
  accent,
  icon,
}: {
  label: string;
  value: ReactNode;
  unit?: string;
  sub?: ReactNode;
  accent: string;
  icon?: ReactNode;
}) {
  return (
    <div className="relative overflow-hidden rounded-[var(--radius-card)] border border-border bg-card p-4">
      <div className="absolute inset-x-0 top-0 h-[3px]" style={{ background: accent }} aria-hidden />
      <div className="flex items-center gap-2 text-[13px] text-muted">
        {icon && (
          <span
            className="flex h-7 w-7 items-center justify-center rounded-lg [&>svg]:h-[17px] [&>svg]:w-[17px]"
            style={{ background: `${accent}22`, color: accent }}
            aria-hidden
          >
            {icon}
          </span>
        )}
        {label}
      </div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className="num text-[28px] font-semibold leading-none sm:text-[32px]">{value}</span>
        {unit && <span className="text-sm text-muted">{unit}</span>}
      </div>
      {sub && <div className={cn("mt-1.5 text-xs text-muted")}>{sub}</div>}
    </div>
  );
}
