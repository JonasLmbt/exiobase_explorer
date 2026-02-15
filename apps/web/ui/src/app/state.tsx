import { createContext, useContext, useEffect, useMemo, useState, type Dispatch, type ReactNode, type SetStateAction } from "react";
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
  themeMode: "dark" | "light";
  setThemeMode: (m: "dark" | "light") => void;
  stageSessions: StageSession[];
  setStageSessions: Dispatch<SetStateAction<StageSession[]>>;
  activeStageSessionId: string;
  setActiveStageSessionId: (id: string) => void;
  regionSessions: RegionSession[];
  setRegionSessions: Dispatch<SetStateAction<RegionSession[]>>;
  activeRegionSessionId: string;
  setActiveRegionSessionId: (id: string) => void;
  pendingSelection: AppSelection;
  setPendingSelection: (s: AppSelection) => void;
  selection: AppSelection;
  setSelection: (s: AppSelection) => void;
  selectionSummary: SelectionSummary | null;
  setSelectionSummary: (s: SelectionSummary | null) => void;
};

export type StageState = {
  methodId: string;
  impacts: string[];
  jobId: string | null;
  lastResult: unknown | null;
  showStagePercentLabels: boolean;
  showTotalAbsoluteLabel: boolean;
};
export type RegionState = {
  methodId: string;
  impacts: string[];
  n: number;
  jobId: string | null;
  lastResult: unknown | null;
  mapPalette: "Reds" | "Blues" | "Greens" | "Greys" | "Viridis";
  mapReverse: boolean;
  mapShowLegend: boolean;
  mapTitle: string;
  mapProjection: "mercator" | "equirectangular" | "robinson";
  mapMode: "binned" | "continuous";
  mapRelative: boolean;
  mapK: number;
  mapCustomBins: string;
  mapNormMode: "linear" | "log" | "power";
  mapRobust: number;
  mapGamma: number;
};

export type StageSession = { id: string; title: string; state: StageState };
export type RegionSession = { id: string; title: string; state: RegionState };

const Ctx = createContext<AppState | null>(null);

function newId(): string {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const c: any = globalThis as any;
    if (c.crypto?.randomUUID) return String(c.crypto.randomUUID());
  } catch {
    // ignore
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function defaultStageState(): StageState {
  return {
    methodId: "bubble",
    impacts: [],
    jobId: null,
    lastResult: null,
    showStagePercentLabels: true,
    showTotalAbsoluteLabel: true,
  };
}

function defaultRegionState(): RegionState {
  return {
    methodId: "world_map",
    impacts: [],
    n: 10,
    jobId: null,
    lastResult: null,
    mapPalette: "Reds",
    mapReverse: false,
    mapShowLegend: false,
    mapTitle: "",
    mapProjection: "robinson",
    mapMode: "binned",
    mapRelative: true,
    mapK: 7,
    mapCustomBins: "",
    mapNormMode: "linear",
    mapRobust: 2.0,
    mapGamma: 0.7,
  };
}

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [themeMode, setThemeMode] = useState<"dark" | "light">(() => {
    const raw = localStorage.getItem("exiobase_explorer_theme_mode");
    return raw === "light" ? "light" : "dark";
  });
  const [year, setYear] = useState<number>(2022);
  const [language, setLanguage] = useState<string>("Deutsch");

  const [activeStageSessionId, setActiveStageSessionId] = useState<string>(() => newId());
  const [stageSessions, setStageSessions] = useState<StageSession[]>(() => [
    { id: activeStageSessionId, title: "Stage 1", state: defaultStageState() },
  ]);

  const [activeRegionSessionId, setActiveRegionSessionId] = useState<string>(() => newId());
  const [regionSessions, setRegionSessions] = useState<RegionSession[]>(() => [
    { id: activeRegionSessionId, title: "Region 1", state: defaultRegionState() },
  ]);

  const [selection, setSelection] = useState<AppSelection>({ mode: "all" });
  const [pendingSelection, setPendingSelection] = useState<AppSelection>({ mode: "all" });
  const [selectionSummary, setSelectionSummary] = useState<SelectionSummary | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem("exiobase_explorer_theme_mode", themeMode);
    } catch {
      // ignore
    }
  }, [themeMode]);

  useEffect(() => {
    setSelection({ mode: "all" });
    setPendingSelection({ mode: "all" });
    setSelectionSummary(null);

    const sid = newId();
    setStageSessions([{ id: sid, title: "Stage 1", state: defaultStageState() }]);
    setActiveStageSessionId(sid);

    const rid = newId();
    setRegionSessions([{ id: rid, title: "Region 1", state: defaultRegionState() }]);
    setActiveRegionSessionId(rid);
  }, [year, language]);

  const value = useMemo<AppState>(
    () => ({
      year,
      setYear,
      language,
      setLanguage,
      themeMode,
      setThemeMode,
      stageSessions,
      setStageSessions,
      activeStageSessionId,
      setActiveStageSessionId,
      regionSessions,
      setRegionSessions,
      activeRegionSessionId,
      setActiveRegionSessionId,
      pendingSelection,
      setPendingSelection,
      selection,
      setSelection,
      selectionSummary,
      setSelectionSummary,
    }),
    [
      activeRegionSessionId,
      activeStageSessionId,
      language,
      pendingSelection,
      regionSessions,
      selection,
      selectionSummary,
      stageSessions,
      themeMode,
      year,
    ],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAppState(): AppState {
  const v = useContext(Ctx);
  if (!v) throw new Error("useAppState must be used within AppStateProvider");
  return v;
}
