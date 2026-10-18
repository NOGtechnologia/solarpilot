"use client";

import { animate, useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState } from "react";

const counted = new Set<string>();

/** Zählt beim ersten Laden hoch – danach (Live-Updates) wird der Wert direkt gesetzt. */
export function CountUp({ id, value, format }: { id: string; value: number; format: (v: number) => string }) {
  const reduce = useReducedMotion();
  const [display, setDisplay] = useState(() => (counted.has(id) || reduce ? value : 0));
  const first = useRef(!counted.has(id));

  useEffect(() => {
    if (first.current && !reduce) {
      first.current = false;
      counted.add(id);
      const controls = animate(0, value, { duration: 1.1, ease: [0.16, 1, 0.3, 1], onUpdate: setDisplay });
      return () => controls.stop();
    }
    counted.add(id);
    setDisplay(value);
  }, [id, value, reduce]);

  return <>{format(display)}</>;
}
