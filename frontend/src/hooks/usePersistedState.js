import { useEffect, useState } from "react";

/**
 * useState with localStorage sync. Reads on mount, writes on change.
 * Useful for survivng tab refresh and navigation away/back.
 */
export function usePersistedState(key, initial) {
  const [value, setValue] = useState(() => {
    try {
      const raw = localStorage.getItem(key);
      return raw !== null ? JSON.parse(raw) : initial;
    } catch {
      return initial;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch { /* quota or serialization error — ignore */ }
  }, [key, value]);

  return [value, setValue];
}
