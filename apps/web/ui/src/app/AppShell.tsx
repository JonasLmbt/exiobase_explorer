import { useMemo, useState } from "react";
import { AppBar, Box, Tab, Tabs, Toolbar, Typography } from "@mui/material";
import SelectionTab from "../pages/SelectionTab";
import VisualisationTab from "../pages/VisualisationTab";
import SettingsTab from "../pages/SettingsTab";
import ConsoleTab from "../pages/ConsoleTab";

type TabId = "selection" | "visualisation" | "console" | "settings";

export default function AppShell() {
  const [tab, setTab] = useState<TabId>("selection");

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
        </Toolbar>
      </AppBar>

      {content}
    </Box>
  );
}

