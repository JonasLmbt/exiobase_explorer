import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AppBar, Box, Chip, IconButton, Tab, Tabs, Toolbar, Tooltip, Typography } from "@mui/material";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import SelectionTab from "../pages/SelectionTab";
import VisualisationTab from "../pages/VisualisationTab";
import SettingsTab from "../pages/SettingsTab";
import ConsoleTab from "../pages/ConsoleTab";
import { api } from "../api";
import { useLog } from "./log";
import { useT } from "./i18n";
import exioLogo2 from "../assets/exiobase_logo_2_transparent_128.png";
import HelpDialog from "./HelpDialog";

type TabId = "selection" | "visualisation" | "console" | "settings";

export default function AppShell() {
  const [tab, setTab] = useState<TabId>("selection");
  const [helpOpen, setHelpOpen] = useState(false);
  const log = useLog();
  const lastApiOnline = useRef<boolean | null>(null);
  const { t } = useT();

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
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.25 }}>
            <Box
              component="img"
              alt="EXIOBASE"
              src={exioLogo2}
              sx={{ width: 28, height: 28, display: "block" }}
            />
            <Typography variant="h6" sx={{ fontWeight: 700 }}>
              EXIOBASE Explorer
            </Typography>
          </Box>
          <Tabs value={tab} onChange={(_, v) => setTab(v)} textColor="inherit" indicatorColor="secondary">
            <Tab value="selection" label={t("Selection")} />
            <Tab value="visualisation" label={t("Visualisation")} />
            <Tab value="console" label={t("Console")} />
            <Tab value="settings" label={t("Settings")} />
          </Tabs>

          <Box sx={{ flex: 1 }} />

          <Tooltip title={t("Help")}>
            <IconButton color="inherit" onClick={() => setHelpOpen(true)} aria-label={t("Help")}>
              <HelpOutlineIcon fontSize="small" />
            </IconButton>
          </Tooltip>

          <Chip
            size="small"
            variant="outlined"
            label={healthQ.data?.status === "ok" ? `${t("API")}: ${t("online")}` : `${t("API")}: ${t("offline")}`}
            color={healthQ.data?.status === "ok" ? "success" : "error"}
          />
        </Toolbar>
      </AppBar>

      {content}
      <HelpDialog open={helpOpen} onClose={() => setHelpOpen(false)} />
    </Box>
  );
}
