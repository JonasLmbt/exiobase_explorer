import React from "react";
import ReactDOM from "react-dom/client";
import { CssBaseline, ThemeProvider } from "@mui/material";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { theme } from "./theme";
import { AppStateProvider } from "./app/state";
import AppShell from "./app/AppShell";

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <AppStateProvider>
          <AppShell />
        </AppStateProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
