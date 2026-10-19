import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Repository-URL für Doku-Links (beim Veröffentlichen per NEXT_PUBLIC_REPO_URL setzen). */
export const REPO_URL = process.env.NEXT_PUBLIC_REPO_URL ?? "https://github.com/NOGtechnologia/solarpilot";

export const COLORS = {
  solar: "#F5A524",
  load: "#3B82F6",
  battery: "#22C55E",
  gridImport: "#F97316",
  gridExport: "#8B5CF6",
} as const;

/** Farbtöne für mehrere Anlagen in der Summenansicht (auf Basis Amber). */
export const SITE_TONES = ["#F5A524", "#F59E0B", "#FBBF24", "#D97706", "#FCD34D", "#B45309"];

export function storageGet(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function storageSet(key: string, value: string) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* privater Modus */
  }
}
