"use client";

import "leaflet/dist/leaflet.css";

import type { CircleMarker, Map as LeafletMap } from "leaflet";
import { useEffect, useRef } from "react";

/** Karte zur Standortwahl (OpenStreetMap). Klick setzt die Koordinaten. */
export function LocationMap({
  lat,
  lon,
  onChange,
}: {
  lat: number;
  lon: number;
  onChange: (lat: number, lon: number) => void;
}) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<LeafletMap | null>(null);
  const marker = useRef<CircleMarker | null>(null);
  const cb = useRef(onChange);
  cb.current = onChange;

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const L = await import("leaflet");
      if (cancelled || !el.current || map.current) return;
      const m = L.map(el.current, { zoomControl: true, attributionControl: true }).setView([lat, lon], 11);
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      }).addTo(m);
      marker.current = L.circleMarker([lat, lon], {
        radius: 10,
        color: "#F5A524",
        weight: 3,
        fillColor: "#F5A524",
        fillOpacity: 0.5,
      }).addTo(m);
      m.on("click", (e) => cb.current(+e.latlng.lat.toFixed(5), +e.latlng.lng.toFixed(5)));
      map.current = m;
    })();
    return () => {
      cancelled = true;
      map.current?.remove();
      map.current = null;
    };
    // Karte nur einmal erzeugen; Positionswechsel übernimmt der zweite Effekt
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!map.current || !marker.current) return;
    marker.current.setLatLng([lat, lon]);
    if (!map.current.getBounds().contains([lat, lon])) map.current.setView([lat, lon], map.current.getZoom());
  }, [lat, lon]);

  return <div ref={el} className="h-64 w-full overflow-hidden rounded-[14px] border border-border" />;
}
