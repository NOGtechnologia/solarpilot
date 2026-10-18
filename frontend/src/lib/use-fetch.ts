"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { api } from "./api";

const cache = new Map<string, unknown>();

/** Kleiner Daten-Hook: Cache pro URL, optionales Intervall, „letzter Stand“ bei Fehlern. */
export function useFetch<T>(url: string | null, refreshMs?: number) {
  const [data, setData] = useState<T | undefined>(() => (url ? (cache.get(url) as T) : undefined));
  const [error, setError] = useState<Error | null>(null);
  const [loading, setLoading] = useState<boolean>(!!url && !cache.has(url));
  const urlRef = useRef(url);
  urlRef.current = url;

  const load = useCallback(async () => {
    const u = urlRef.current;
    if (!u) return;
    try {
      const res = await api.get<T>(u);
      if (urlRef.current !== u) return;
      cache.set(u, res);
      setData(res);
      setError(null);
    } catch (e) {
      if (urlRef.current === u) setError(e as Error);
    } finally {
      if (urlRef.current === u) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!url) return;
    setData(cache.get(url) as T | undefined);
    setLoading(!cache.has(url));
    load();
    if (!refreshMs) return;
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") load();
    }, refreshMs);
    return () => window.clearInterval(id);
  }, [url, refreshMs, load]);

  return { data, error, loading, reload: load };
}

export function invalidate(prefix: string) {
  for (const k of cache.keys()) if (k.startsWith(prefix)) cache.delete(k);
}
