"use client";

import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Field, Input, Select, Switch } from "@/components/ui/form";
import { api } from "@/lib/api";
import { fmtPower } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import type { AdapterInfo, Snapshot } from "@/lib/types";

export const ROLES = ["inverter", "hybrid", "battery", "grid_meter", "meter", "ev_charger"] as const;
export const MASK = "__unchanged__";

export interface DeviceDraft {
  name: string;
  role: string;
  config: Record<string, unknown>;
  secrets: Record<string, string>;
}

export function initialDraft(a: AdapterInfo): DeviceDraft {
  const config: Record<string, unknown> = {};
  for (const f of a.config_schema) if (!f.secret && f.default !== null && f.default !== undefined) config[f.name] = f.default;
  return { name: a.name, role: a.default_role, config, secrets: {} };
}

export function DeviceForm({
  adapter,
  draft,
  onChange,
  site,
  deviceId,
}: {
  adapter: AdapterInfo;
  draft: DeviceDraft;
  onChange: (d: DeviceDraft) => void;
  site: { lat: number; lon: number; timezone: string };
  deviceId?: number;
}) {
  const { t, lang } = useI18n();
  const [test, setTest] = useState<{ state: "idle" | "busy" | "ok" | "fail"; error?: string; snap?: Snapshot }>({ state: "idle" });

  const setConfig = (k: string, v: unknown) => onChange({ ...draft, config: { ...draft.config, [k]: v } });
  const setSecret = (k: string, v: string) => onChange({ ...draft, secrets: { ...draft.secrets, [k]: v } });

  async function runTest() {
    setTest({ state: "busy" });
    try {
      const r = await api.post<{ ok: boolean; error?: string; snapshot?: Snapshot }>(`/api/adapters/${adapter.type}/test`, {
        config: draft.config,
        secrets: draft.secrets,
        device_id: deviceId,
        ...site,
      });
      setTest(r.ok ? { state: "ok", snap: r.snapshot } : { state: "fail", error: r.error });
    } catch (e) {
      setTest({ state: "fail", error: (e as Error).message });
    }
  }

  const p = (w: number | null | undefined) => {
    const f = fmtPower(w ?? null, lang);
    return `${f.value} ${f.unit}`;
  };

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label={t("setup.device_name")} htmlFor="dev-name">
          <Input id="dev-name" value={draft.name} onChange={(e) => onChange({ ...draft, name: e.target.value })} required />
        </Field>
        <Field label={t("setup.role")} htmlFor="dev-role">
          <Select id="dev-role" value={draft.role} onChange={(e) => onChange({ ...draft, role: e.target.value })}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {t(`role.${r}`)}
              </option>
            ))}
          </Select>
        </Field>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {adapter.config_schema.map((f) => {
          const label = `${lang === "de" ? f.label_de : f.label_en}${f.required ? " *" : ""}`;
          const hint = lang === "de" ? f.help_de : f.help_en;
          const id = `f-${f.name}`;
          if (f.type === "bool") {
            return (
              <div key={f.name} className="sm:col-span-2">
                <Switch id={id} label={label} checked={!!draft.config[f.name]} onChange={(v) => setConfig(f.name, v)} />
                {hint && <p className="text-xs text-muted">{hint}</p>}
              </div>
            );
          }
          if (f.secret) {
            const stored = draft.secrets[f.name] === MASK;
            return (
              <Field key={f.name} label={label} htmlFor={id} hint={stored ? t("settings.secret_set") : hint}>
                <Input
                  id={id}
                  type="password"
                  autoComplete="off"
                  placeholder={stored ? "••••••••" : ""}
                  value={stored ? "" : (draft.secrets[f.name] ?? "")}
                  onChange={(e) => setSecret(f.name, e.target.value || (stored ? MASK : ""))}
                />
              </Field>
            );
          }
          if (f.type === "select" && f.options) {
            return (
              <Field key={f.name} label={label} htmlFor={id} hint={hint}>
                <Select id={id} value={String(draft.config[f.name] ?? f.default ?? "")} onChange={(e) => setConfig(f.name, e.target.value)}>
                  {f.options.map((o) => (
                    <option key={o} value={o}>
                      {o}
                    </option>
                  ))}
                </Select>
              </Field>
            );
          }
          return (
            <Field key={f.name} label={label} htmlFor={id} hint={hint}>
              <Input
                id={id}
                type={f.type === "number" ? "number" : "text"}
                step="any"
                inputMode={f.type === "number" ? "decimal" : undefined}
                value={draft.config[f.name] === undefined || draft.config[f.name] === null ? "" : String(draft.config[f.name])}
                onChange={(e) =>
                  setConfig(f.name, f.type === "number" ? (e.target.value === "" ? null : Number(e.target.value)) : e.target.value)
                }
                required={f.required}
              />
            </Field>
          );
        })}
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={runTest} disabled={test.state === "busy"}>
          {test.state === "busy" ? <Loader2 size={16} className="animate-spin" /> : null}
          {test.state === "busy" ? t("setup.testing") : t("setup.test")}
        </Button>
        {test.state === "ok" && (
          <span role="status" className="flex items-center gap-1.5 text-sm text-success">
            <CheckCircle2 size={16} /> {t("setup.test_ok")} · PV {p(test.snap?.pv_power_w)}
            {test.snap?.grid_power_w != null && ` · ${t("flow.grid")} ${p(test.snap.grid_power_w)}`}
            {test.snap?.battery_soc_pct != null && ` · ${Math.round(test.snap.battery_soc_pct)} %`}
          </span>
        )}
        {test.state === "fail" && (
          <span role="alert" className="flex items-center gap-1.5 text-sm text-danger">
            <XCircle size={16} /> {t("setup.test_fail")}: {test.error}
          </span>
        )}
      </div>
    </div>
  );
}
