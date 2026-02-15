import React from "react";
import ReactDOM from "react-dom/client";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LogProvider } from "./app/log";
import { AppStateProvider, useAppState } from "./app/state";
import { createAppTheme } from "./theme";
import AppShell from "./app/AppShell";
import "leaflet/dist/leaflet.css";

const queryClient = new QueryClient();

function ThemeFromState({ children }: { children: React.ReactNode }) {
  const { themeMode } = useAppState();
  const theme = React.useMemo(() => createAppTheme(themeMode), [themeMode]);
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </ThemeProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <LogProvider>
        <AppStateProvider>
          <ThemeFromState>
            <AppShell />
          </ThemeFromState>
        </AppStateProvider>
      </LogProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
