import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { SelectionSummary } from "../api";

export type AppSelection =
  | { mode: "all" }
  | { mode: "indices"; indices: number[] }
  | { mode: "regions_sectors"; regions: number[]; sectors: number[] };

export type AppState = {
  year: number;
  setYear: (y: number) => void;
  language: string;
  setLanguage: (l: string) => void;
  pendingSelection: AppSelection;
  setPendingSelection: (s: AppSelection) => void;
  selection: AppSelection;
  setSelection: (s: AppSelection) => void;
  selectionSummary: SelectionSummary | null;
  setSelectionSummary: (s: SelectionSummary | null) => void;
};

const Ctx = createContext<AppState | null>(null);

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [year, setYear] = useState<number>(2022);
  const [language, setLanguage] = useState<string>("Deutsch");
  const [selection, setSelection] = useState<AppSelection>({ mode: "all" });
  const [pendingSelection, setPendingSelection] = useState<AppSelection>({ mode: "all" });
  const [selectionSummary, setSelectionSummary] = useState<SelectionSummary | null>(null);

  useEffect(() => {
    setSelection({ mode: "all" });
    setPendingSelection({ mode: "all" });
    setSelectionSummary(null);
  }, [year, language]);

  const value = useMemo<AppState>(
    () => ({
      year,
      setYear,
      language,
      setLanguage,
      pendingSelection,
      setPendingSelection,
      selection,
      setSelection,
      selectionSummary,
      setSelectionSummary,
    }),
    [language, pendingSelection, selection, selectionSummary, year],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAppState(): AppState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAppState must be used within AppStateProvider");
  return v;
}
