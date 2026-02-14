import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppBar, Box, Chip, Tab, Tabs, Toolbar, Typography } from "@mui/material";
import SelectionTab from "../pages/SelectionTab";
import VisualisationTab from "../pages/VisualisationTab";
import SettingsTab from "../pages/SettingsTab";
import ConsoleTab from "../pages/ConsoleTab";
import { api } from "../api";
import { useLog } from "./log";

type TabId = "selection" | "visualisation" | "console" | "settings";

export default function AppShell() {
  const [tab, setTab] = useState<TabId>("selection");
  const log = useLog();
  const lastApiOnline = useRef<boolean | null>(null);

  const healthQ = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    retry: false,
    refetchInterval: 10_000,
  });

  useEffect(() => {
    const online = healthQ.data?.status === "ok";
    if (lastApiOnline.current === null) {
      lastApiOnline.current = online;
      return;
    }
    if (lastApiOnline.current !== online) {
      lastApiOnline.current = online;
      log.info(online ? "API online" : "API offline");
    }
  }, [healthQ.data?.status, log]);

  const content = useMemo(() => {
    switch (tab) {
      case "selection":
        return <SelectionTab />;
      case "visualisation":
        return <VisualisationTab />;
      case "console":
        return <ConsoleTab />;
      case "settings":
        return <SettingsTab />;
      default:
        return null;
    }
  }, [tab]);

  return (
    <Box sx={{ minHeight: "100vh" }}>
      <AppBar position="sticky" elevation={0} sx={{ borderBottom: "1px solid rgba(255,255,255,0.12)" }}>
        <Toolbar sx={{ gap: 3 }}>
          <Typography variant="h6" sx={{ fontWeight: 700 }}>
            EXIOBASE Explorer
          </Typography>
          <Tabs value={tab} onChange={(_, v) => setTab(v)} textColor="inherit" indicatorColor="secondary">
            <Tab value="selection" label="Selection" />
            <Tab value="visualisation" label="Visualisation" />
            <Tab value="console" label="Console" />
            <Tab value="settings" label="Settings" />
          </Tabs>

          <Box sx={{ flex: 1 }} />
          <Chip
            size="small"
            variant="outlined"
            label={healthQ.data?.status === "ok" ? "API: online" : "API: offline"}
            color={healthQ.data?.status === "ok" ? "success" : "error"}
          />
        </Toolbar>
      </AppBar>

      {content}
    </Box>
  );
}
