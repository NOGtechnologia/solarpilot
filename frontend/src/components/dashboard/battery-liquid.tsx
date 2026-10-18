"use client";

import { useId } from "react";

import { COLORS } from "@/lib/utils";

/** Batterie als füllende Flüssigkeit mit sanfter Welle (SVG, Bewegung via CSS – respektiert reduced motion). */
export function BatteryLiquid({
  x,
  y,
  width,
  height,
  soc,
}: {
  x: number;
  y: number;
  width: number;
  height: number;
  soc: number;
}) {
  const id = useId().replace(/:/g, "");
  const level = Math.max(0, Math.min(100, soc));
  const fillY = y + height * (1 - level / 100);
  const waveW = width * 2;
  const amp = level > 2 && level < 98 ? 2 : 0;
  // Wellenpfad über doppelte Breite, horizontal animiert
  const d = `M0 ${amp} Q ${width / 4} ${-amp} ${width / 2} ${amp} T ${width} ${amp} T ${width * 1.5} ${amp} T ${waveW} ${amp} V ${height + 4} H 0 Z`;
  const color = level < 15 ? COLORS.gridImport : COLORS.battery;
  return (
    <g>
      <defs>
        <clipPath id={`bat-${id}`}>
          <rect x={x} y={y} width={width} height={height} rx={5} />
        </clipPath>
      </defs>
      <rect x={x + width / 2 - 5} y={y - 4} width={10} height={4} rx={1.5} fill="var(--muted)" opacity={0.7} />
      <rect x={x} y={y} width={width} height={height} rx={5} fill="var(--bg)" stroke="var(--muted)" strokeOpacity={0.5} />
      <g clipPath={`url(#bat-${id})`}>
        <g transform={`translate(${x} ${fillY})`}>
          <path d={d} fill={color} opacity={0.9} style={{ animation: "wave 2.6s linear infinite", transformBox: "fill-box" }} />
        </g>
      </g>
    </g>
  );
}
