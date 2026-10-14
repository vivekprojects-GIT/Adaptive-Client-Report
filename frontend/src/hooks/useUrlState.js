import { useCallback } from "react";
import { useLocation, useNavigate } from "react-router-dom";

/**
 * useState kept in the address bar's query string, so a refresh, a bookmark
 * or a shared link lands on the same page, tab and filters. The default is
 * left out of the URL, so a bare address always opens the default.
 *
 *   push: true adds a history entry (Back returns to the previous page);
 *   otherwise the current entry is replaced (filters, selections).
 */
export function useUrlState(key, initial, { push = false, allowed } = {}) {
  const location = useLocation();
  const navigate = useNavigate();
  const raw = new URLSearchParams(location.search).get(key);
  let value = initial;
  if (raw !== null && (!allowed || allowed.includes(raw))) {
    value = typeof initial === "number" ? Number(raw) : raw;
    if (typeof initial === "number" && Number.isNaN(value)) value = initial;
  }

  const set = useCallback((next) => {
    // Read the live URL rather than this render's copy, so two updates in
    // the same tick (say, a page and a client) both survive.
    const params = new URLSearchParams(window.location.search);
    if (next === initial || next === null || next === undefined || next === "") params.delete(key);
    else params.set(key, String(next));
    const search = params.toString();
    if (`?${search}` === window.location.search || (!search && !window.location.search)) return;
    navigate({ pathname: window.location.pathname, search: search ? `?${search}` : "" },
             { replace: !push });
  }, [key, initial, push, navigate]);

  return [value, set];
}
