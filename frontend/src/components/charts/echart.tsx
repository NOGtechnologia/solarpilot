"use client";

import { BarChart, LineChart } from "echarts/charts";
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  MarkPointComponent,
  TooltipComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { SVGRenderer } from "echarts/renderers";
import { useTheme } from "next-themes";
import { useEffect, useRef } from "react";

echarts.use([
  LineChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkAreaComponent,
  MarkPointComponent,
  SVGRenderer,
]);

export type EChartsOption = echarts.EChartsCoreOption;

export function chartTheme(dark: boolean) {
  return {
    text: dark ? "#95A1B2" : "#5B6573",
    grid: dark ? "rgba(255,255,255,0.06)" : "rgba(11,15,20,0.07)",
    tooltipBg: dark ? "#18202B" : "#FFFFFF",
    tooltipBorder: dark ? "#222C39" : "#E3E7ED",
    fg: dark ? "#EEF2F7" : "#0B0F14",
  };
}

export function EChart({
  option,
  height = 280,
  ariaLabel,
}: {
  option: (dark: boolean) => EChartsOption;
  height?: number;
  ariaLabel: string;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const { resolvedTheme } = useTheme();
  const dark = resolvedTheme !== "light";

  useEffect(() => {
    if (!ref.current) return;
    chart.current = echarts.init(ref.current, undefined, { renderer: "svg" });
    const ro = new ResizeObserver(() => chart.current?.resize());
    ro.observe(ref.current);
    return () => {
      ro.disconnect();
      chart.current?.dispose();
      chart.current = null;
    };
  }, []);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    chart.current?.setOption({ animation: !reduce, ...option(dark) }, { notMerge: true });
  }, [option, dark]);

  return <div ref={ref} role="img" aria-label={ariaLabel} style={{ height, width: "100%" }} />;
}
