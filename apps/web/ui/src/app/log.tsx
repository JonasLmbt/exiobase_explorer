import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

type Level = "info" | "error";

export type LogLine = { ts: number; level: Level; message: string };

export type LogApi = {
  lines: LogLine[];
  info: (msg: string) => void;
  error: (msg: string) => void;
  clear: () => void;
};

const Ctx = createContext<LogApi | null>(null);

export function LogProvider({ children }: { children: ReactNode }) {
  const [lines, setLines] = useState<LogLine[]>([]);

  const push = useCallback((level: Level, message: string) => {
    setLines((prev) => {
      const next = [...prev, { ts: Date.now(), level, message }];
      return next.length > 500 ? next.slice(next.length - 500) : next;
    });
  }, []);

  const api = useMemo<LogApi>(
    () => ({
      lines,
      info: (m) => push("info", m),
      error: (m) => push("error", m),
      clear: () => setLines([]),
    }),
    [lines, push],
  );

  return <Ctx.Provider value={api}>{children}</Ctx.Provider>;
}

export function useLog(): LogApi {
  const v = useContext(Ctx);
  if (!v) throw new Error("useLog must be used within LogProvider");
  return v;
}

