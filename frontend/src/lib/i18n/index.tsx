"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { storageGet, storageSet } from "../utils";
import de, { type Dict } from "./de";
import en from "./en";

export type Lang = "de" | "en";
export type TKey = keyof Dict;
const DICTS: Record<Lang, Dict> = { de, en };

export function translate(lang: Lang, key: TKey | string, params?: Record<string, unknown>): string {
  const dict = DICTS[lang] as Record<string, string>;
  let text = dict[key] ?? (DICTS.de as Record<string, string>)[key] ?? key;
  if (params) {
    text = text.replace(/\{(\w+)\}/g, (_, k) => {
      const v = params[k];
      return v === undefined || v === null ? "" : String(v);
    });
  }
  return text;
}

interface I18nCtx {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: TKey | string, params?: Record<string, unknown>) => string;
}

const Ctx = createContext<I18nCtx>({
  lang: "de",
  setLang: () => {},
  t: (k, p) => translate("de", k, p),
});

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>("de");

  useEffect(() => {
    const stored = storageGet("sp_lang");
    if (stored === "de" || stored === "en") setLangState(stored);
    else if (navigator.language && !navigator.language.startsWith("de")) setLangState("en");
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    storageSet("sp_lang", l);
  }, []);

  const value = useMemo<I18nCtx>(
    () => ({ lang, setLang, t: (k, p) => translate(lang, k, p) }),
    [lang, setLang],
  );
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useI18n() {
  return useContext(Ctx);
}
