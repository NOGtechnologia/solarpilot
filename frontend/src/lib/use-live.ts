"use client";

import { useEffect, useRef, useState } from "react";

import { api, wsUrl } from "./api";
import type { LivePayload } from "./types";

export type LiveState = "connecting" | "live" | "polling";

/** Live-Werte per WebSocket; bei Problemen automatisch Polling alle 10 s und Wiederverbinden. */
export function useLive(enabled = true) {
  const [payload, setPayload] = useState<LivePayload | null>(null);
  const [state, setState] = useState<LiveState>("connecting");
  const retry = useRef(0);

  useEffect(() => {
    if (!enabled) return;
    let ws: WebSocket | null = null;
    let closed = false;
    let pollTimer: number | undefined;
    let reconnectTimer: number | undefined;
    let pingTimer: number | undefined;

    const poll = async () => {
      try {
        setPayload(await api.get<LivePayload>("/api/live"));
      } catch {
        /* ignorieren, nächster Versuch */
      }
    };

    const startPolling = () => {
      setState("polling");
      if (pollTimer) return;
      poll();
      pollTimer = window.setInterval(poll, 10_000);
    };

    const connect = () => {
      if (closed) return;
      try {
        ws = new WebSocket(wsUrl());
      } catch {
        startPolling();
        return;
      }
      ws.onopen = () => {
        retry.current = 0;
        setState("live");
        if (pollTimer) {
          window.clearInterval(pollTimer);
          pollTimer = undefined;
        }
        pingTimer = window.setInterval(() => ws?.readyState === 1 && ws.send("ping"), 25_000);
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.type === "live") setPayload(msg);
        } catch {
          /* ungültige Nachricht */
        }
      };
      ws.onclose = () => {
        if (pingTimer) window.clearInterval(pingTimer);
        if (closed) return;
        startPolling();
        const delay = Math.min(30_000, 1000 * 2 ** retry.current++);
        reconnectTimer = window.setTimeout(connect, delay);
      };
    };

    connect();
    return () => {
      closed = true;
      ws?.close();
      if (pollTimer) window.clearInterval(pollTimer);
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      if (pingTimer) window.clearInterval(pingTimer);
    };
  }, [enabled]);

  return { payload, state };
}
