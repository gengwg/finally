"use client";

import { useEffect, useRef, useState } from "react";

export type Flash = "up" | "down" | null;

/** Returns the tick direction for ~500ms after `value` changes, then null. */
export function useFlash(value: number | null | undefined): Flash {
  const previous = useRef(value);
  const [flash, setFlash] = useState<Flash>(null);

  useEffect(() => {
    const before = previous.current;
    previous.current = value;
    if (value == null || before == null || value === before) return;

    setFlash(value > before ? "up" : "down");
    const timer = setTimeout(() => setFlash(null), 500);
    return () => clearTimeout(timer);
  }, [value]);

  return flash;
}

export const flashClass = (flash: Flash) =>
  flash === "up" ? "flash-up" : flash === "down" ? "flash-down" : "";
