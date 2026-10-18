import {
  Cloud,
  CloudDrizzle,
  CloudFog,
  CloudLightning,
  CloudMoon,
  CloudRain,
  CloudSnow,
  CloudSun,
  Moon,
  Sun,
  type LucideIcon,
} from "lucide-react";

/** WMO-Wettercodes (Open-Meteo) → Icon und Übersetzungsschlüssel. */
export function weatherInfo(code: number | null | undefined, isDay = true): { icon: LucideIcon; key: string } {
  const c = code ?? 0;
  if (c === 0) return { icon: isDay ? Sun : Moon, key: "weather.clear" };
  if (c <= 2) return { icon: isDay ? CloudSun : CloudMoon, key: "weather.partly" };
  if (c === 3) return { icon: Cloud, key: "weather.overcast" };
  if (c === 45 || c === 48) return { icon: CloudFog, key: "weather.fog" };
  if (c >= 51 && c <= 57) return { icon: CloudDrizzle, key: "weather.drizzle" };
  if ((c >= 61 && c <= 67) || (c >= 80 && c <= 82)) return { icon: CloudRain, key: "weather.rain" };
  if ((c >= 71 && c <= 77) || c === 85 || c === 86) return { icon: CloudSnow, key: "weather.snow" };
  if (c >= 95) return { icon: CloudLightning, key: "weather.thunder" };
  return { icon: Cloud, key: "weather.overcast" };
}
