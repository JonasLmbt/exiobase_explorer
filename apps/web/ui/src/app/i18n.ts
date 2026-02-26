import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { useAppState } from "./state";

/**
 * Minimal i18n helper backed by `general.xlsx` via the API.
 *
 * The backend exposes `/api/v1/meta/translations` which returns a map of
 * canonical keys -> localized strings for the currently selected language.
 */
export function useT() {
  const { year, language } = useAppState();

  const q = useQuery({
    queryKey: ["translations", year, language],
    queryFn: () => api.translations(year, language),
    retry: false,
    staleTime: 60_000,
  });

  const dict = q.data?.translations ?? {};

  return useMemo(() => {
    const t = (key: string, params?: Record<string, string | number>) => {
      const raw = (dict[key] ?? key) as string;
      if (!params) return raw;
      return raw.replace(/\{(\w+)\}/g, (_m, name) => (name in params ? String(params[name]) : `{${name}}`));
    };
    return { t, ready: Boolean(q.data), language: q.data?.language ?? language };
  }, [dict, language, q.data]);
}
