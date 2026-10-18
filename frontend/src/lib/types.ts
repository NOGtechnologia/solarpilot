export interface Snapshot {
  timestamp_utc: string;
  pv_power_w: number | null;
  load_power_w: number | null;
  grid_power_w: number | null;
  battery_power_w: number | null;
  battery_soc_pct: number | null;
  energy_today_wh: number | null;
  temperature_c?: number | null;
  strings?: { name: string; power_w: number | null; voltage_v?: number | null; current_a?: number | null }[];
}

export interface DeviceStatus {
  id: number;
  site_id: number;
  name: string;
  type: string;
  role: string;
  online: boolean;
  last_seen: number | null;
  error: string | null;
  snapshot: Snapshot | null;
}

export interface LivePayload {
  type: "live";
  ts: number;
  all: Snapshot | null;
  sites: Record<string, Snapshot>;
  devices: DeviceStatus[];
}

export interface PvArray {
  kwp: number;
  tilt: number;
  azimuth: number;
  losses_pct?: number;
  name?: string | null;
}

export interface Device {
  id: number;
  site_id: number;
  name: string;
  type: string;
  role: string;
  config: Record<string, unknown>;
  secrets: Record<string, string>;
  enabled: boolean;
  last_seen: number | null;
  last_error: string | null;
}

export interface Site {
  id: number;
  name: string;
  lat: number;
  lon: number;
  timezone: string;
  arrays: PvArray[];
  battery_kwh: number | null;
  buy_eur_kwh: number | null;
  feed_in_eur_kwh: number | null;
  color: string | null;
  source: string;
  kwp: number;
  devices: Device[];
}

export interface ConfigField {
  name: string;
  label_de: string;
  label_en: string;
  type: "text" | "number" | "password" | "bool" | "select" | "textarea";
  required: boolean;
  default: unknown;
  secret: boolean;
  options: string[] | null;
  help_de: string | null;
  help_en: string | null;
}

export interface AdapterInfo {
  type: string;
  name: string;
  vendor: string;
  connection: "local" | "cloud" | "simulated";
  status: "stable" | "beta";
  default_role: string;
  capabilities: Record<string, boolean>;
  config_schema: ConfigField[];
  docs: string | null;
}

export interface DayStats {
  pv_wh: number;
  load_wh: number;
  import_wh: number;
  export_wh: number;
  charge_wh: number;
  discharge_wh: number;
  self_consumption_wh: number;
  savings_eur: number;
  co2_kg: number;
  forecast_wh: number | null;
  self_consumption_pct: number | null;
  autarky_pct: number | null;
}

export interface EnergySeries {
  labels: string[];
  pv_kwh: number[];
  load_kwh: number[];
  import_kwh: number[];
  export_kwh: number[];
  self_kwh: number[];
  forecast_kwh: (number | null)[];
  savings_eur: number[];
  total: DayStats;
}

export interface HistoryResponse {
  range: "day" | "week" | "month" | "year";
  date: string;
  resolution_s?: number;
  series?: {
    ts: number[];
    pv: (number | null)[];
    load: (number | null)[];
    grid: (number | null)[];
    battery: (number | null)[];
    soc: (number | null)[];
  } | null;
  forecast?: { ts: number[]; pv: number[] };
  per_site?: Record<string, (number | null)[]>;
  energy?: EnergySeries | null;
}

export interface WeatherResponse {
  weather: {
    current: {
      ts: number;
      temperature: number;
      weather_code: number;
      cloud_cover: number;
      wind_speed: number;
      is_day: number;
    };
    hourly: { ts: number[]; temperature: number[]; cloud_cover: number[]; weather_code: number[]; radiation: number[] };
    daily: {
      ts: number;
      weather_code: number;
      temp_max: number;
      temp_min: number;
      sunrise: number;
      sunset: number;
      radiation_mj: number;
      precipitation_probability: number | null;
      cloud_cover: number | null;
    }[];
  } | null;
  fetched_at: number | null;
  stale: boolean;
  error: string | null;
  sun: { sunrise: number | null; sunset: number | null; elevation: number; azimuth: number };
  alerts: { headline_de: string; headline_en: string; severity: string; onset: string; expires: string }[];
}

export interface ForecastSite {
  site_id: number;
  points: { ts: number; power_w: number; raw_w: number; cloud_cover: number | null }[];
  daily: { day: string; energy_wh: number; forecast_solar_wh: number | null }[];
  correction?: { factor: number; accuracy_pct: number | null; days: number };
  accuracy_history: { day: string; actual_wh: number; forecast_wh: number | null }[];
  stale: boolean;
  error: string | null;
  fetched_at?: number | null;
}

export interface PricePoint {
  ts: number;
  duration_s: number;
  eur_mwh: number;
  ct_kwh: number;
  total_ct_kwh: number | null;
}

export interface PricesResponse {
  zone: string;
  points: PricePoint[];
  current: PricePoint | null;
  cheapest: PricePoint | null;
  most_expensive: PricePoint | null;
  cheapest_3h: { start: number; end: number; avg_ct_kwh: number } | null;
  dynamic: boolean;
}

export interface NewsItem {
  title: string;
  source: string;
  link: string;
  published: number;
  teaser: string;
  lang: string;
}

export interface Insight {
  id: string;
  kind: "tip" | "warning" | "info";
  key: string;
  params: Record<string, string | number | null>;
  site_id: number | null;
  start: number | null;
  end: number | null;
  priority: number;
}

export interface AuthStatus {
  has_users: boolean;
  authenticated: boolean;
  user: { id: number; username: string; is_admin: boolean } | null;
  public_dashboard: boolean;
  language: "de" | "en";
}

export interface MonthlyReport {
  year: number;
  month: number;
  sites: string[];
  total: DayStats;
  previous_year: DayStats;
  change_pct: number | null;
  best_day: { day: string; pv_kwh: number } | null;
  days: EnergySeries;
}
