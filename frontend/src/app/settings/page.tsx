"use client";

import { Download, Pencil, Plus, Send, Trash2, Upload } from "lucide-react";
import Link from "next/link";
import { useTheme } from "next-themes";
import { useEffect, useState, type ReactNode } from "react";

import { useApp } from "@/components/providers";
import { ArraysEditor } from "@/components/setup/arrays-editor";
import { DeviceForm, MASK, type DeviceDraft } from "@/components/setup/device-form";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardHeader } from "@/components/ui/card";
import { Badge, Field, Input, Select, Skeleton, Switch, Textarea } from "@/components/ui/form";
import { api } from "@/lib/api";
import { fmtRelative } from "@/lib/format";
import { useI18n, type Lang } from "@/lib/i18n";
import type { AdapterInfo, Device, Site } from "@/lib/types";
import { useFetch } from "@/lib/use-fetch";
import { cn } from "@/lib/utils";

type Section = "sites" | "tariff" | "general" | "notifications" | "smarthome" | "data" | "users" | "ai";
const SECTIONS: Section[] = ["sites", "tariff", "general", "notifications", "smarthome", "data", "users", "ai"];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Json = Record<string, any>;

function useSection(name: string) {
  const { data, reload } = useFetch<Json>(`/api/settings/${name}`);
  const [draft, setDraft] = useState<Json | null>(null);
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    if (data) setDraft(structuredClone(data));
  }, [data]);
  const set = (path: string[], value: unknown) =>
    setDraft((d) => {
      const next = structuredClone(d ?? {});
      let cur = next;
      for (const p of path.slice(0, -1)) cur = cur[p] ??= {};
      cur[path[path.length - 1]] = value;
      return next;
    });
  const save = async () => {
    setState("saving");
    try {
      await api.put(`/api/settings/${name}`, draft);
      await reload();
      setState("saved");
      setError(null);
      window.setTimeout(() => setState("idle"), 2000);
    } catch (e) {
      setState("error");
      setError((e as Error).message);
    }
  };
  return { draft, set, save, state, error };
}

function SaveBar({ state, error, onSave }: { state: string; error: string | null; onSave: () => void }) {
  const { t } = useI18n();
  return (
    <div className="mt-5 flex items-center gap-3">
      <Button variant="primary" onClick={onSave} disabled={state === "saving"}>
        {t("common.save")}
      </Button>
      {state === "saved" && <span role="status" className="text-sm text-success">{t("common.saved")}</span>}
      {error && <span role="alert" className="text-sm text-danger">{error}</span>}
    </div>
  );
}

function SecretInput({ id, value, onChange }: { id: string; value: string; onChange: (v: string) => void }) {
  const { t } = useI18n();
  const stored = value === MASK;
  return (
    <>
      <Input
        id={id}
        type="password"
        autoComplete="off"
        placeholder={stored ? "••••••••" : ""}
        value={stored ? "" : value}
        onChange={(e) => onChange(e.target.value || (stored ? MASK : ""))}
      />
      {stored && <span className="text-xs text-muted">{t("settings.secret_set")}</span>}
    </>
  );
}

function Num({ id, value, onChange, step = "any" }: { id: string; value: number; onChange: (v: number) => void; step?: string }) {
  return <Input id={id} type="number" step={step} inputMode="decimal" value={value ?? ""} onChange={(e) => onChange(Number(e.target.value))} />;
}

function Grid({ children }: { children: ReactNode }) {
  return <div className="grid gap-4 sm:grid-cols-2">{children}</div>;
}

/* --- Anlagen ---------------------------------------------------------------- */

function SiteEditor({ site, onDone }: { site: Site; onDone: () => void }) {
  const { t } = useI18n();
  const [s, setS] = useState(site);
  const [error, setError] = useState<string | null>(null);
  async function save() {
    try {
      await api.put(`/api/sites/${site.id}`, s);
      onDone();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <div className="mt-3 space-y-4 rounded-xl border border-border p-3">
      <Grid>
        <Field label={t("setup.site_name")} htmlFor={`sn-${site.id}`}>
          <Input id={`sn-${site.id}`} value={s.name} onChange={(e) => setS({ ...s, name: e.target.value })} />
        </Field>
        <Field label={t("setup.timezone")} htmlFor={`tz-${site.id}`}>
          <Input id={`tz-${site.id}`} value={s.timezone} onChange={(e) => setS({ ...s, timezone: e.target.value })} />
        </Field>
        <Field label={t("setup.lat")} htmlFor={`la-${site.id}`}>
          <Num id={`la-${site.id}`} value={s.lat} onChange={(v) => setS({ ...s, lat: v })} />
        </Field>
        <Field label={t("setup.lon")} htmlFor={`lo-${site.id}`}>
          <Num id={`lo-${site.id}`} value={s.lon} onChange={(v) => setS({ ...s, lon: v })} />
        </Field>
        <Field label={t("setup.battery_kwh")} htmlFor={`bk-${site.id}`}>
          <Num id={`bk-${site.id}`} value={s.battery_kwh ?? 0} onChange={(v) => setS({ ...s, battery_kwh: v || null })} />
        </Field>
        <Field label={`${t("settings.buy")} (${t("common.optional")})`} htmlFor={`bu-${site.id}`}>
          <Input id={`bu-${site.id}`} type="number" step="0.001" value={s.buy_eur_kwh ?? ""} onChange={(e) => setS({ ...s, buy_eur_kwh: e.target.value === "" ? null : Number(e.target.value) })} />
        </Field>
      </Grid>
      <ArraysEditor arrays={s.arrays} onChange={(arrays) => setS({ ...s, arrays })} />
      <div className="flex gap-2">
        <Button variant="primary" onClick={save}>
          {t("common.save")}
        </Button>
        <Button variant="ghost" onClick={onDone}>
          {t("common.cancel")}
        </Button>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
    </div>
  );
}

function DeviceEditor({ device, site, adapters, onDone }: { device: Device | null; site: Site; adapters: AdapterInfo[]; onDone: () => void }) {
  const { t } = useI18n();
  const [type, setType] = useState(device?.type ?? adapters[0]?.type);
  const adapter = adapters.find((a) => a.type === type)!;
  const [draft, setDraft] = useState<DeviceDraft>(() =>
    device
      ? { name: device.name, role: device.role, config: { ...device.config }, secrets: { ...device.secrets } }
      : { name: adapter.name, role: adapter.default_role, config: {}, secrets: {} },
  );
  const [error, setError] = useState<string | null>(null);
  async function save() {
    const body = { site_id: site.id, name: draft.name, type, role: draft.role, config: draft.config, secrets: draft.secrets, enabled: device?.enabled ?? true };
    try {
      if (device) await api.put(`/api/devices/${device.id}`, body);
      else await api.post("/api/devices", body);
      onDone();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <div className="mt-3 space-y-4 rounded-xl border border-border p-3">
      {!device && (
        <Field label={t("setup.step_adapter")} htmlFor="new-type">
          <Select
            id="new-type"
            value={type}
            onChange={(e) => {
              const a = adapters.find((x) => x.type === e.target.value)!;
              setType(a.type);
              setDraft({ name: a.name, role: a.default_role, config: {}, secrets: {} });
            }}
          >
            {adapters.map((a) => (
              <option key={a.type} value={a.type}>
                {a.name}
              </option>
            ))}
          </Select>
        </Field>
      )}
      <DeviceForm adapter={adapter} draft={draft} onChange={setDraft} site={site} deviceId={device?.id} />
      <div className="flex gap-2">
        <Button variant="primary" onClick={save}>
          {t("common.save")}
        </Button>
        <Button variant="ghost" onClick={onDone}>
          {t("common.cancel")}
        </Button>
      </div>
      {error && <p className="text-sm text-danger">{error}</p>}
    </div>
  );
}

function SitesSection() {
  const { t, lang } = useI18n();
  const { sites, refreshSites } = useApp();
  const adapters = useFetch<AdapterInfo[]>("/api/adapters");
  const [editSite, setEditSite] = useState<number | null>(null);
  const [editDevice, setEditDevice] = useState<string | null>(null);
  const [yaml, setYaml] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const done = async () => {
    setEditSite(null);
    setEditDevice(null);
    await refreshSites();
  };
  async function removeSite(id: number) {
    if (!window.confirm(t("common.confirm_delete"))) return;
    await api.del(`/api/sites/${id}`);
    await refreshSites();
  }
  async function removeDevice(id: number) {
    if (!window.confirm(t("common.confirm_delete"))) return;
    await api.del(`/api/devices/${id}`);
    await refreshSites();
  }
  async function importYaml() {
    try {
      const r = await api.post<Json>("/api/config/import", { yaml });
      setMsg(JSON.stringify(r));
      setYaml("");
      await refreshSites();
    } catch (e) {
      setMsg((e as Error).message);
    }
  }

  if (!sites || !adapters.data) return <Skeleton className="h-40" />;
  return (
    <div className="space-y-4">
      {sites.map((s) => (
        <Card key={s.id}>
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div>
              <h3 className="font-semibold">{s.name}</h3>
              <p className="text-xs text-muted">
                {s.kwp} kWp · {s.lat.toFixed(3)}, {s.lon.toFixed(3)} · {s.timezone}
                {s.battery_kwh ? ` · ${s.battery_kwh} kWh` : ""}
              </p>
            </div>
            <div className="flex gap-1">
              <Button size="sm" variant="ghost" onClick={() => setEditSite(editSite === s.id ? null : s.id)}>
                <Pencil size={14} /> {t("common.edit")}
              </Button>
              <Button size="sm" variant="danger" onClick={() => removeSite(s.id)}>
                <Trash2 size={14} />
              </Button>
            </div>
          </div>
          {editSite === s.id && <SiteEditor site={s} onDone={done} />}
          <ul className="mt-3 space-y-2">
            {s.devices.map((d) => (
              <li key={d.id} className="rounded-xl bg-card-2 px-3 py-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium">{d.name}</div>
                    <div className="text-xs text-muted">
                      {adapters.data!.find((a) => a.type === d.type)?.name ?? d.type} · {t(`role.${d.role}`)}
                      {d.last_seen ? ` · ${fmtRelative(d.last_seen, lang)}` : ""}
                      {d.last_error ? ` · ${d.last_error}` : ""}
                    </div>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <Button size="sm" variant="ghost" aria-label={t("common.edit")} onClick={() => setEditDevice(editDevice === `d${d.id}` ? null : `d${d.id}`)}>
                      <Pencil size={14} />
                    </Button>
                    <Button size="sm" variant="ghost" aria-label={t("common.delete")} onClick={() => removeDevice(d.id)}>
                      <Trash2 size={14} />
                    </Button>
                  </div>
                </div>
                {editDevice === `d${d.id}` && <DeviceEditor device={d} site={s} adapters={adapters.data!} onDone={done} />}
              </li>
            ))}
          </ul>
          {editDevice === `new${s.id}` ? (
            <DeviceEditor device={null} site={s} adapters={adapters.data!} onDone={done} />
          ) : (
            <Button size="sm" className="mt-3" onClick={() => setEditDevice(`new${s.id}`)}>
              <Plus size={14} /> {t("settings.add_device")}
            </Button>
          )}
        </Card>
      ))}
      <div className="flex flex-wrap gap-2">
        <Link href="/setup/" className={cn(buttonVariants({ variant: "primary" }))}>
          <Plus size={16} /> {t("nav.setup")}
        </Link>
        <a href="/api/config/export" className={cn(buttonVariants({ variant: "secondary" }))}>
          <Download size={16} /> {t("settings.export")}
        </a>
      </div>
      <Card>
        <CardHeader title={t("settings.import")} icon={<Upload size={14} />} />
        <Textarea aria-label={t("settings.import")} rows={6} value={yaml} onChange={(e) => setYaml(e.target.value)} placeholder={"sites:\n  - name: Wohnhaus\n    location: { lat: 53.08, lon: 8.80 }"} />
        <Button className="mt-3" onClick={importYaml} disabled={!yaml.trim()}>
          {t("settings.import")}
        </Button>
        {msg && <p className="mt-2 text-sm text-muted">{msg}</p>}
      </Card>
    </div>
  );
}

/* --- Weitere Abschnitte ------------------------------------------------------ */

function TariffSection() {
  const { t } = useI18n();
  const { draft, set, save, state, error } = useSection("tariff");
  if (!draft) return <Skeleton className="h-40" />;
  return (
    <Card>
      <Grid>
        <Field label={t("settings.buy")} htmlFor="buy">
          <Num id="buy" value={draft.buy_eur_kwh} onChange={(v) => set(["buy_eur_kwh"], v)} />
        </Field>
        <Field label={t("settings.feed_in")} htmlFor="feed">
          <Num id="feed" value={draft.feed_in_eur_kwh} onChange={(v) => set(["feed_in_eur_kwh"], v)} />
        </Field>
        <Field label={t("settings.currency")} htmlFor="cur">
          <Select id="cur" value={draft.currency} onChange={(e) => set(["currency"], e.target.value)}>
            {["EUR", "CHF", "USD", "GBP"].map((c) => (
              <option key={c}>{c}</option>
            ))}
          </Select>
        </Field>
        <Field label={t("settings.zone")} htmlFor="zone">
          <Select id="zone" value={draft.price_zone} onChange={(e) => set(["price_zone"], e.target.value)}>
            <option value="DE-LU">DE-LU</option>
            <option value="AT">AT</option>
          </Select>
        </Field>
        <Field label={t("settings.provider")} htmlFor="prov">
          <Select id="prov" value={draft.price_provider} onChange={(e) => set(["price_provider"], e.target.value)}>
            <option value="energy_charts">Energy-Charts (Fraunhofer ISE)</option>
            <option value="awattar">aWATTar</option>
          </Select>
        </Field>
      </Grid>
      <div className="mt-4">
        <Switch id="dyn" label={`${t("settings.dynamic")} – ${t("settings.dynamic_hint")}`} checked={!!draft.dynamic} onChange={(v) => set(["dynamic"], v)} />
      </div>
      {draft.dynamic && (
        <Field label={t("settings.markup")} htmlFor="markup" className="mt-3 max-w-sm">
          <Num id="markup" value={draft.markup_eur_kwh} onChange={(v) => set(["markup_eur_kwh"], v)} />
        </Field>
      )}
      <SaveBar state={state} error={error} onSave={save} />
    </Card>
  );
}

function GeneralSection() {
  const { t, lang, setLang } = useI18n();
  const { theme, setTheme } = useTheme();
  const { refreshAuth } = useApp();
  const { draft, set, save, state, error } = useSection("general");
  if (!draft) return <Skeleton className="h-40" />;
  return (
    <Card>
      <Grid>
        <Field label={t("settings.language")} htmlFor="lang">
          <Select
            id="lang"
            value={lang}
            onChange={(e) => {
              setLang(e.target.value as Lang);
              set(["language"], e.target.value);
            }}
          >
            <option value="de">Deutsch</option>
            <option value="en">English</option>
          </Select>
        </Field>
        <Field label={t("settings.theme")} htmlFor="theme">
          <Select id="theme" value={theme ?? "dark"} onChange={(e) => setTheme(e.target.value)}>
            <option value="dark">{t("settings.theme_dark")}</option>
            <option value="light">{t("settings.theme_light")}</option>
            <option value="system">{t("settings.theme_system")}</option>
          </Select>
        </Field>
        <Field label={t("settings.co2")} htmlFor="co2">
          <Num id="co2" value={draft.co2_kg_per_kwh} onChange={(v) => set(["co2_kg_per_kwh"], v)} />
        </Field>
        <Field label={t("settings.base_load")} htmlFor="base">
          <Num id="base" value={draft.base_load_w} onChange={(v) => set(["base_load_w"], v)} />
        </Field>
        <Field label={t("settings.big_consumer")} htmlFor="big">
          <Num id="big" value={draft.big_consumer_w} onChange={(v) => set(["big_consumer_w"], v)} />
        </Field>
        <Field label={t("settings.ev_kwh")} htmlFor="evk">
          <Num id="evk" value={draft.ev_charge_kwh} onChange={(v) => set(["ev_charge_kwh"], v)} />
        </Field>
        <Field label={t("settings.ev_power")} htmlFor="evp">
          <Num id="evp" value={draft.ev_charge_power_w} onChange={(v) => set(["ev_charge_power_w"], v)} />
        </Field>
      </Grid>
      <div className="mt-4">
        <Switch id="public" label={t("settings.public")} checked={!!draft.public_dashboard} onChange={(v) => set(["public_dashboard"], v)} />
      </div>
      <SaveBar
        state={state}
        error={error}
        onSave={async () => {
          await save();
          await refreshAuth();
        }}
      />
    </Card>
  );
}

function NotificationsSection() {
  const { t } = useI18n();
  const { draft, set, save, state, error } = useSection("notifications");
  const [result, setResult] = useState<Record<string, string>>({});
  if (!draft) return <Skeleton className="h-40" />;
  async function test(channel: string) {
    await save();
    try {
      const r = await api.post<Record<string, string>>("/api/notifications/test", { channel });
      setResult((x) => ({ ...x, [channel]: r[channel] === "ok" ? t("settings.test_ok") : r[channel] }));
    } catch (e) {
      setResult((x) => ({ ...x, [channel]: (e as Error).message }));
    }
  }
  const channel = (name: string, title: string, fields: ReactNode) => (
    <Card>
      <CardHeader
        title={title}
        action={
          <Button size="sm" onClick={() => test(name)} disabled={!draft[name]?.enabled}>
            <Send size={14} /> {t("settings.test")}
          </Button>
        }
      />
      <Switch id={`${name}-en`} label={t("settings.enabled")} checked={!!draft[name]?.enabled} onChange={(v) => set([name, "enabled"], v)} />
      <div className="mt-3">{fields}</div>
      {result[name] && <p className="mt-2 text-sm text-muted">{result[name]}</p>}
    </Card>
  );
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title={t("settings.events")} />
        <Switch id="ev-off" label={t("settings.event_offline")} checked={!!draft.events?.offline} onChange={(v) => set(["events", "offline"], v)} />
        <Switch id="ev-under" label={t("settings.event_under")} checked={!!draft.events?.underperformance} onChange={(v) => set(["events", "underperformance"], v)} />
        <Switch id="ev-sur" label={t("settings.event_surplus")} checked={!!draft.events?.surplus} onChange={(v) => set(["events", "surplus"], v)} />
        <Switch id="ev-sum" label={t("settings.event_summary")} checked={!!draft.events?.daily_summary} onChange={(v) => set(["events", "daily_summary"], v)} />
      </Card>
      {channel(
        "ntfy",
        "ntfy",
        <Grid>
          <Field label="Server" htmlFor="ntfy-url">
            <Input id="ntfy-url" value={draft.ntfy.url} onChange={(e) => set(["ntfy", "url"], e.target.value)} />
          </Field>
          <Field label="Topic" htmlFor="ntfy-topic">
            <Input id="ntfy-topic" value={draft.ntfy.topic} onChange={(e) => set(["ntfy", "topic"], e.target.value)} />
          </Field>
          <Field label={`Token (${t("common.optional")})`} htmlFor="ntfy-token">
            <SecretInput id="ntfy-token" value={draft.ntfy.token} onChange={(v) => set(["ntfy", "token"], v)} />
          </Field>
        </Grid>,
      )}
      {channel(
        "telegram",
        "Telegram",
        <Grid>
          <Field label="Bot-Token" htmlFor="tg-token">
            <SecretInput id="tg-token" value={draft.telegram.bot_token} onChange={(v) => set(["telegram", "bot_token"], v)} />
          </Field>
          <Field label="Chat-ID" htmlFor="tg-chat">
            <Input id="tg-chat" value={draft.telegram.chat_id} onChange={(e) => set(["telegram", "chat_id"], e.target.value)} />
          </Field>
        </Grid>,
      )}
      {channel(
        "email",
        "E-Mail (SMTP)",
        <Grid>
          <Field label={t("settings.host")} htmlFor="sm-host">
            <Input id="sm-host" value={draft.email.host} onChange={(e) => set(["email", "host"], e.target.value)} />
          </Field>
          <Field label={t("settings.port")} htmlFor="sm-port">
            <Num id="sm-port" value={draft.email.port} onChange={(v) => set(["email", "port"], v)} step="1" />
          </Field>
          <Field label={t("settings.user")} htmlFor="sm-user">
            <Input id="sm-user" value={draft.email.username} onChange={(e) => set(["email", "username"], e.target.value)} />
          </Field>
          <Field label={t("settings.password")} htmlFor="sm-pass">
            <SecretInput id="sm-pass" value={draft.email.password} onChange={(v) => set(["email", "password"], v)} />
          </Field>
          <Field label="From" htmlFor="sm-from">
            <Input id="sm-from" type="email" value={draft.email.from_addr} onChange={(e) => set(["email", "from_addr"], e.target.value)} />
          </Field>
          <Field label="To" htmlFor="sm-to">
            <Input id="sm-to" type="email" value={draft.email.to_addr} onChange={(e) => set(["email", "to_addr"], e.target.value)} />
          </Field>
        </Grid>,
      )}
      <SaveBar state={state} error={error} onSave={save} />
    </div>
  );
}

function SmartHomeSection() {
  const { t } = useI18n();
  const { draft, set, save, state, error } = useSection("mqtt");
  if (!draft) return <Skeleton className="h-40" />;
  return (
    <Card>
      <CardHeader title="MQTT · Home Assistant" />
      <p className="mb-3 text-sm text-muted">{t("settings.mqtt_hint")}</p>
      <Switch id="mq-en" label={t("settings.enabled")} checked={!!draft.enabled} onChange={(v) => set(["enabled"], v)} />
      <div className="mt-3">
        <Grid>
          <Field label={t("settings.host")} htmlFor="mq-host">
            <Input id="mq-host" value={draft.host} onChange={(e) => set(["host"], e.target.value)} placeholder="192.168.1.10" />
          </Field>
          <Field label={t("settings.port")} htmlFor="mq-port">
            <Num id="mq-port" value={draft.port} onChange={(v) => set(["port"], v)} step="1" />
          </Field>
          <Field label={t("settings.user")} htmlFor="mq-user">
            <Input id="mq-user" value={draft.username} onChange={(e) => set(["username"], e.target.value)} />
          </Field>
          <Field label={t("settings.password")} htmlFor="mq-pass">
            <SecretInput id="mq-pass" value={draft.password} onChange={(v) => set(["password"], v)} />
          </Field>
          <Field label={t("settings.prefix")} htmlFor="mq-prefix">
            <Input id="mq-prefix" value={draft.prefix} onChange={(e) => set(["prefix"], e.target.value)} />
          </Field>
          <Field label="Discovery-Präfix" htmlFor="mq-dprefix">
            <Input id="mq-dprefix" value={draft.discovery_prefix} onChange={(e) => set(["discovery_prefix"], e.target.value)} />
          </Field>
        </Grid>
      </div>
      <div className="mt-3">
        <Switch id="mq-disc" label={t("settings.discovery")} checked={!!draft.discovery} onChange={(v) => set(["discovery"], v)} />
      </div>
      <SaveBar state={state} error={error} onSave={save} />
    </Card>
  );
}

function DataSection() {
  const { t } = useI18n();
  const weather = useSection("weather");
  const news = useSection("news");
  if (!weather.draft || !news.draft) return <Skeleton className="h-40" />;
  const feeds: { url: string; name?: string; lang?: string }[] = news.draft.feeds ?? [];
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader title={t("weather.title")} />
        <Switch id="bs" label={t("settings.brightsky")} checked={!!weather.draft.brightsky_alerts} onChange={(v) => weather.set(["brightsky_alerts"], v)} />
        <Switch id="fs" label={t("settings.forecast_solar")} checked={!!weather.draft.forecast_solar} onChange={(v) => weather.set(["forecast_solar"], v)} />
        {weather.draft.forecast_solar && (
          <Field label={t("settings.forecast_solar_key")} htmlFor="fs-key" className="mt-2 max-w-sm">
            <SecretInput id="fs-key" value={weather.draft.forecast_solar_key} onChange={(v) => weather.set(["forecast_solar_key"], v)} />
          </Field>
        )}
        <SaveBar state={weather.state} error={weather.error} onSave={weather.save} />
      </Card>
      <Card>
        <CardHeader title={t("news.title")} />
        <Switch id="news-en" label={t("settings.news_enabled")} checked={!!news.draft.enabled} onChange={(v) => news.set(["enabled"], v)} />
        <Field label={t("settings.feeds")} htmlFor="feeds" className="mt-3">
          <Textarea
            id="feeds"
            rows={5}
            value={feeds.map((f) => f.url).join("\n")}
            onChange={(e) =>
              news.set(
                ["feeds"],
                e.target.value
                  .split("\n")
                  .map((u) => u.trim())
                  .filter(Boolean)
                  .map((url) => ({ url, name: new URL(url, "https://x").hostname.replace(/^www\./, "") })),
              )
            }
          />
        </Field>
        <SaveBar state={news.state} error={news.error} onSave={news.save} />
      </Card>
    </div>
  );
}

function UsersSection() {
  const { t } = useI18n();
  const { auth } = useApp();
  const { data, reload } = useFetch<{ id: number; username: string; is_admin: boolean }[]>("/api/users");
  const [u, setU] = useState({ username: "", password: "", is_admin: false });
  const [error, setError] = useState<string | null>(null);
  async function add() {
    try {
      await api.post("/api/users", u);
      setU({ username: "", password: "", is_admin: false });
      setError(null);
      reload();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  return (
    <Card>
      <ul className="mb-4 space-y-2">
        {data?.map((x) => (
          <li key={x.id} className="flex items-center justify-between rounded-xl bg-card-2 px-3 py-2 text-sm">
            <span className="flex items-center gap-2">
              {x.username} {x.is_admin && <Badge tone="solar">{t("settings.admin")}</Badge>}
            </span>
            {x.id !== auth?.user?.id && (
              <Button
                size="sm"
                variant="ghost"
                aria-label={t("common.delete")}
                onClick={async () => {
                  if (window.confirm(t("common.confirm_delete"))) {
                    await api.del(`/api/users/${x.id}`);
                    reload();
                  }
                }}
              >
                <Trash2 size={14} />
              </Button>
            )}
          </li>
        ))}
      </ul>
      <CardHeader title={t("settings.new_user")} />
      <Grid>
        <Field label={t("login.username")} htmlFor="nu-name">
          <Input id="nu-name" value={u.username} onChange={(e) => setU({ ...u, username: e.target.value })} />
        </Field>
        <Field label={t("login.password")} htmlFor="nu-pass" hint={t("login.password_hint")}>
          <Input id="nu-pass" type="password" autoComplete="new-password" value={u.password} onChange={(e) => setU({ ...u, password: e.target.value })} />
        </Field>
      </Grid>
      <div className="mt-3">
        <Switch id="nu-admin" label={t("settings.admin")} checked={u.is_admin} onChange={(v) => setU({ ...u, is_admin: v })} />
      </div>
      <Button className="mt-3" variant="primary" onClick={add} disabled={!u.username || u.password.length < 8}>
        <Plus size={14} /> {t("settings.add")}
      </Button>
      {error && <p className="mt-2 text-sm text-danger">{error}</p>}
    </Card>
  );
}

function AiSection() {
  const { t } = useI18n();
  const { draft, set, save, state, error } = useSection("ai");
  if (!draft) return <Skeleton className="h-40" />;
  return (
    <Card>
      <p className="mb-3 text-sm text-muted">{t("settings.ai_hint")}</p>
      <Switch id="ai-en" label={t("settings.enabled")} checked={!!draft.enabled} onChange={(v) => set(["enabled"], v)} />
      <div className="mt-3">
        <Grid>
          <Field label={t("settings.api_key")} htmlFor="ai-key">
            <SecretInput id="ai-key" value={draft.api_key} onChange={(v) => set(["api_key"], v)} />
          </Field>
          <Field label={t("settings.model")} htmlFor="ai-model">
            <Input id="ai-model" value={draft.model} onChange={(e) => set(["model"], e.target.value)} />
          </Field>
        </Grid>
      </div>
      <SaveBar state={state} error={error} onSave={save} />
    </Card>
  );
}

export default function SettingsPage() {
  const { t } = useI18n();
  const { isAdmin } = useApp();
  const [section, setSection] = useState<Section>("sites");
  useEffect(() => {
    const h = window.location.hash.slice(1) as Section;
    if (SECTIONS.includes(h)) setSection(h);
  }, []);
  const choose = (s: Section) => {
    setSection(s);
    history.replaceState(null, "", `#${s}`);
  };
  if (!isAdmin) return <p className="text-sm text-muted">403</p>;
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold tracking-tight">{t("settings.title")}</h1>
      <div className="grid gap-4 md:grid-cols-[200px_minmax(0,1fr)]">
        <nav aria-label={t("settings.title")} className="-mx-1 flex gap-1 overflow-x-auto px-1 md:flex-col md:overflow-visible">
          {SECTIONS.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => choose(s)}
              aria-current={section === s ? "page" : undefined}
              className={cn(
                "shrink-0 cursor-pointer rounded-xl px-3 py-2 text-left text-sm font-medium",
                section === s ? "bg-card-2 text-fg" : "text-muted hover:text-fg",
              )}
            >
              {t(`settings.${s}`)}
            </button>
          ))}
        </nav>
        <div>
          {section === "sites" && <SitesSection />}
          {section === "tariff" && <TariffSection />}
          {section === "general" && <GeneralSection />}
          {section === "notifications" && <NotificationsSection />}
          {section === "smarthome" && <SmartHomeSection />}
          {section === "data" && <DataSection />}
          {section === "users" && <UsersSection />}
          {section === "ai" && <AiSection />}
        </div>
      </div>
    </div>
  );
}
