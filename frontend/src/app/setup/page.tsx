"use client";

import { Check, Cloud, Cpu, MapPin, Search, Wifi } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";

import { useApp } from "@/components/providers";
import { ArraysEditor } from "@/components/setup/arrays-editor";
import { DeviceForm, initialDraft, type DeviceDraft } from "@/components/setup/device-form";
import { LocationMap } from "@/components/setup/location-map";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge, Field, Input, Segmented, Skeleton } from "@/components/ui/form";
import { api } from "@/lib/api";
import { useI18n } from "@/lib/i18n";
import type { AdapterInfo, PvArray, Site } from "@/lib/types";
import { useFetch } from "@/lib/use-fetch";
import { REPO_URL, cn } from "@/lib/utils";

const STEPS = ["setup.step_location", "setup.step_adapter", "setup.step_connection", "setup.step_system"] as const;

interface GeoResult {
  name: string;
  admin1?: string;
  country?: string;
  lat: number;
  lon: number;
  timezone?: string;
}

export default function SetupPage() {
  const { t, lang } = useI18n();
  const { sites, refreshSites, isAdmin } = useApp();
  const router = useRouter();
  const adapters = useFetch<AdapterInfo[]>("/api/adapters");
  const [step, setStep] = useState(0);
  const [mode, setMode] = useState<"new" | "existing">("new");
  const [existingId, setExistingId] = useState<string>("");
  const [name, setName] = useState("");
  const [lat, setLat] = useState(51.16);
  const [lon, setLon] = useState(10.45);
  const [timezone, setTimezone] = useState(() => Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Berlin");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<GeoResult[]>([]);
  const [adapter, setAdapter] = useState<AdapterInfo | null>(null);
  const [draft, setDraft] = useState<DeviceDraft | null>(null);
  const [filter, setFilter] = useState("");
  const [arrays, setArrays] = useState<PvArray[]>([{ kwp: 10, tilt: 35, azimuth: 180, losses_pct: 14 }]);
  const [battery, setBattery] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const existing: Site | undefined = sites?.find((s) => String(s.id) === existingId);
  const siteCtx = existing ? { lat: existing.lat, lon: existing.lon, timezone: existing.timezone } : { lat, lon, timezone };

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return (adapters.data ?? []).filter((a) => !q || `${a.vendor} ${a.name}`.toLowerCase().includes(q));
  }, [adapters.data, filter]);

  async function search(e: FormEvent) {
    e.preventDefault();
    if (query.trim().length < 2) return;
    try {
      const r = await api.get<{ results: GeoResult[] }>(`/api/geocode?q=${encodeURIComponent(query)}&lang=${lang}`);
      setResults(r.results);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  function pick(r: GeoResult) {
    setLat(+r.lat.toFixed(5));
    setLon(+r.lon.toFixed(5));
    if (r.timezone) setTimezone(r.timezone);
    if (!name) setName(r.name);
    setResults([]);
  }

  function chooseAdapter(a: AdapterInfo) {
    setAdapter(a);
    setDraft(initialDraft(a));
    setStep(2);
  }

  const canNext =
    step === 0 ? (mode === "existing" ? !!existing : name.trim().length > 0) : step === 1 ? !!adapter : step === 2 ? !!draft?.name : true;

  async function finish() {
    if (!adapter || !draft) return;
    setSaving(true);
    setError(null);
    try {
      let siteId = existing?.id;
      const battery_kwh = battery ? Number(battery) : null;
      if (!siteId) {
        const s = await api.post<Site>("/api/sites", { name, lat, lon, timezone, arrays, battery_kwh });
        siteId = s.id;
      } else if (existing) {
        await api.put(`/api/sites/${existing.id}`, { ...existing, arrays, battery_kwh: battery_kwh ?? existing.battery_kwh });
      }
      await api.post("/api/devices", { site_id: siteId, name: draft.name, type: adapter.type, role: draft.role, config: draft.config, secrets: draft.secrets });
      await refreshSites();
      router.push("/");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (!isAdmin) return <p className="text-sm text-muted">403</p>;

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-2xl font-semibold tracking-tight">{t("setup.title")}</h1>
      <ol className="grid grid-cols-4 gap-2" aria-label={t("setup.title")}>
        {STEPS.map((s, i) => (
          <li key={s}>
            <button
              type="button"
              disabled={i > step}
              onClick={() => setStep(i)}
              aria-current={i === step ? "step" : undefined}
              className={cn(
                "flex w-full cursor-pointer flex-col items-start gap-1 rounded-xl border px-3 py-2 text-left text-[12px] disabled:cursor-default",
                i === step ? "border-solar bg-solar/10" : i < step ? "border-border bg-card" : "border-border bg-card opacity-60",
              )}
            >
              <span className={cn("flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-semibold", i < step ? "bg-success text-white" : "bg-card-2")}>
                {i < step ? <Check size={12} /> : i + 1}
              </span>
              <span className="font-medium">{t(s)}</span>
            </button>
          </li>
        ))}
      </ol>

      <Card>
        {step === 0 && (
          <div className="space-y-4">
            {!!sites?.length && (
              <Segmented
                label={t("setup.step_location")}
                value={mode}
                onChange={setMode}
                options={[
                  { value: "new", label: t("setup.new_site") },
                  { value: "existing", label: t("setup.existing_site") },
                ]}
              />
            )}
            {mode === "existing" ? (
              <div className="grid gap-2 sm:grid-cols-2">
                {sites?.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    onClick={() => {
                      setExistingId(String(s.id));
                      setArrays(s.arrays.length ? s.arrays : arrays);
                      setBattery(s.battery_kwh ? String(s.battery_kwh) : "");
                    }}
                    className={cn("cursor-pointer rounded-xl border p-3 text-left", existingId === String(s.id) ? "border-solar bg-solar/10" : "border-border")}
                  >
                    <div className="font-medium">{s.name}</div>
                    <div className="text-xs text-muted">
                      {s.kwp} kWp · {s.devices.length} {t("dash.devices")}
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <>
                <Field label={t("setup.site_name")} htmlFor="site-name">
                  <Input id="site-name" placeholder={t("setup.site_name_ph")} value={name} onChange={(e) => setName(e.target.value)} />
                </Field>
                <form onSubmit={search} className="flex gap-2">
                  <Input aria-label={t("setup.search")} placeholder={t("setup.search_ph")} value={query} onChange={(e) => setQuery(e.target.value)} />
                  <Button type="submit" aria-label={t("setup.search")}>
                    <Search size={16} />
                  </Button>
                </form>
                {results.length > 0 && (
                  <ul className="divide-y divide-border rounded-xl border border-border">
                    {results.map((r, i) => (
                      <li key={i}>
                        <button type="button" onClick={() => pick(r)} className="flex w-full cursor-pointer items-center gap-2 px-3 py-2 text-left text-sm hover:bg-card-2">
                          <MapPin size={14} className="text-solar" />
                          {r.name}
                          <span className="text-muted">
                            {[r.admin1, r.country].filter(Boolean).join(", ")}
                          </span>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
                <LocationMap
                  lat={lat}
                  lon={lon}
                  onChange={(a, b) => {
                    setLat(a);
                    setLon(b);
                  }}
                />
                <p className="text-xs text-muted">{t("setup.map_hint")}</p>
                <div className="grid grid-cols-3 gap-3">
                  <Field label={t("setup.lat")} htmlFor="lat">
                    <Input id="lat" type="number" step="0.00001" value={lat} onChange={(e) => setLat(Number(e.target.value))} />
                  </Field>
                  <Field label={t("setup.lon")} htmlFor="lon">
                    <Input id="lon" type="number" step="0.00001" value={lon} onChange={(e) => setLon(Number(e.target.value))} />
                  </Field>
                  <Field label={t("setup.timezone")} htmlFor="tz">
                    <Input id="tz" value={timezone} onChange={(e) => setTimezone(e.target.value)} />
                  </Field>
                </div>
              </>
            )}
          </div>
        )}

        {step === 1 && (
          <div className="space-y-3">
            <Input aria-label={t("setup.filter")} placeholder={t("setup.filter")} value={filter} onChange={(e) => setFilter(e.target.value)} />
            {!adapters.data ? (
              <Skeleton className="h-64" />
            ) : (
              <div className="grid gap-2 sm:grid-cols-2">
                {filtered.map((a) => (
                  <button
                    key={a.type}
                    type="button"
                    onClick={() => chooseAdapter(a)}
                    className={cn(
                      "flex cursor-pointer items-start gap-3 rounded-xl border p-3 text-left transition-colors hover:border-solar/60",
                      adapter?.type === a.type ? "border-solar bg-solar/10" : "border-border",
                    )}
                  >
                    <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-card-2 text-muted">
                      {a.connection === "cloud" ? <Cloud size={16} /> : a.connection === "simulated" ? <Cpu size={16} /> : <Wifi size={16} />}
                    </span>
                    <span className="min-w-0">
                      <span className="block font-medium">{a.name}</span>
                      <span className="mt-1 flex flex-wrap gap-1">
                        <Badge>{t(`setup.${a.connection}`)}</Badge>
                        <Badge tone={a.status === "stable" ? "success" : "solar"}>{t(`setup.${a.status}`)}</Badge>
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {step === 2 && adapter && draft && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-medium">{adapter.name}</h2>
              {adapter.docs && (
                <a
                  className="text-sm text-solar-text underline-offset-2 hover:underline"
                  href={`${REPO_URL}/blob/main/docs/adapters/${adapter.docs}.md`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {t("setup.docs")}
                </a>
              )}
            </div>
            <DeviceForm adapter={adapter} draft={draft} onChange={setDraft} site={siteCtx} />
          </div>
        )}

        {step === 3 && (
          <div className="space-y-4">
            <h2 className="font-medium">{t("setup.arrays")}</h2>
            <ArraysEditor arrays={arrays} onChange={setArrays} />
            <Field label={t("setup.battery_kwh")} htmlFor="batt" hint={t("common.optional")} className="max-w-xs">
              <Input id="batt" type="number" min="0" step="0.1" value={battery} onChange={(e) => setBattery(e.target.value)} />
            </Field>
          </div>
        )}

        {error && (
          <p role="alert" className="mt-4 text-sm text-danger">
            {error}
          </p>
        )}
        <div className="mt-6 flex justify-between gap-2">
          <Button variant="ghost" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>
            {t("common.back")}
          </Button>
          {step < 3 ? (
            <Button variant="primary" onClick={() => setStep((s) => s + 1)} disabled={!canNext}>
              {t("common.next")}
            </Button>
          ) : (
            <Button variant="primary" onClick={finish} disabled={saving || !arrays.every((a) => a.kwp > 0)}>
              {t("setup.finish")}
            </Button>
          )}
        </div>
      </Card>
    </div>
  );
}
