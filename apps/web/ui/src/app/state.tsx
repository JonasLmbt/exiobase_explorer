import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

export type AppSelection =
  | { mode: "all" }
  | { mode: "indices"; indices: number[] }
  | { mode: "regions_sectors"; regions: number[]; sectors: number[] };

export type AppState = {
  year: number;
  setYear: (y: number) => void;
  language: string;
  setLanguage: (l: string) => void;
  selection: AppSelection;
  setSelection: (s: AppSelection) => void;
};

const Ctx = createContext<AppState | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [year, setYear] = useState<number>(2022);
  const [language, setLanguage] = useState<string>("Deutsch");
  const [selection, setSelection] = useState<AppSelection>({ mode: "all" });

  const value = useMemo<AppState>(
    () => ({ year, setYear, language, setLanguage, selection, setSelection }),
    [language, selection, year],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAppState(): AppState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAppState must be used within AppStateProvider");
  return v;
}

