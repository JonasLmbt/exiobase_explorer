import { useMemo, useState, type Dispatch, type SetStateAction } from "react";
import { Box, Button, Container, Dialog, DialogActions, DialogContent, DialogTitle, IconButton, Stack, Tab, Tabs, TextField, Tooltip, Typography } from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import CloseIcon from "@mui/icons-material/Close";
import EditIcon from "@mui/icons-material/Edit";
import StageAnalysisTab from "../features/stageAnalysis/StageAnalysisTab";
import RegionAnalysisTab from "../features/regionAnalysis/RegionAnalysisTab";
import { useAppState, type RegionState, type StageState } from "../app/state";
import { useT } from "../app/i18n";

type Inner = "stage" | "region";

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

export default function VisualisationTab() {
  const {
    stageSessions,
    setStageSessions,
    activeStageSessionId,
    setActiveStageSessionId,
    regionSessions,
    setRegionSessions,
    activeRegionSessionId,
    setActiveRegionSessionId,
  } = useAppState();
  const { t } = useT();
  const [inner, setInner] = useState<Inner>("stage");
  const [renameOpen, setRenameOpen] = useState(false);
  const [renameKind, setRenameKind] = useState<Inner>("stage");
  const [renameId, setRenameId] = useState<string>("");
  const [renameValue, setRenameValue] = useState<string>("");

  const activeStage = useMemo(
    () => stageSessions.find((s) => s.id === activeStageSessionId) ?? stageSessions[0],
    [activeStageSessionId, stageSessions],
  );
  const activeRegion = useMemo(
    () => regionSessions.find((s) => s.id === activeRegionSessionId) ?? regionSessions[0],
    [activeRegionSessionId, regionSessions],
  );

  const setStageState: Dispatch<SetStateAction<StageState>> = (next) => {
    setStageSessions((prev) =>
      prev.map((s) => {
        if (s.id !== activeStageSessionId) return s;
        const state = typeof next === "function" ? (next as any)(s.state) : next;
        return { ...s, state };
      }),
    );
  };

  const setRegionState: Dispatch<SetStateAction<RegionState>> = (next) => {
    setRegionSessions((prev) =>
      prev.map((s) => {
        if (s.id !== activeRegionSessionId) return s;
        const state = typeof next === "function" ? (next as any)(s.state) : next;
        return { ...s, state };
      }),
    );
  };

  const addStage = () => {
    const id = newId();
    const title = t("Stage {n}", { n: stageSessions.length + 1 });
    setStageSessions((prev) => [
      ...prev,
      {
        id,
        title,
        state: { methodId: "bubble", impacts: [], jobId: null, lastResult: null, showStagePercentLabels: true, showTotalAbsoluteLabel: true },
      },
    ]);
    setActiveStageSessionId(id);
  };

  const addRegion = () => {
    const id = newId();
    const title = t("Region {n}", { n: regionSessions.length + 1 });
    setRegionSessions((prev) => [
      ...prev,
      {
        id,
        title,
        state: {
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
          mapValueMode: "value",
          mapK: 7,
          mapCustomBins: "",
          mapNormMode: "linear",
          mapRobust: 2.0,
          mapGamma: 0.7,
        },
      },
    ]);
    setActiveRegionSessionId(id);
  };

  const openRename = (kind: Inner, id: string, currentTitle: string) => {
    setRenameKind(kind);
    setRenameId(id);
    setRenameValue(currentTitle);
    setRenameOpen(true);
  };

  const applyRename = () => {
    const title = renameValue.trim() || (renameKind === "stage" ? t("Stage") : t("Region"));
    if (renameKind === "stage") {
      setStageSessions((prev) => prev.map((s) => (s.id === renameId ? { ...s, title } : s)));
    } else {
      setRegionSessions((prev) => prev.map((s) => (s.id === renameId ? { ...s, title } : s)));
    }
    setRenameOpen(false);
  };

  const closeStage = (id: string) => {
    setStageSessions((prev) => {
      const next = prev.filter((s) => s.id !== id);
      if (!next.length) {
        const nid = newId();
        setActiveStageSessionId(nid);
        return [
          {
            id: nid,
            title: t("Stage {n}", { n: 1 }),
            state: { methodId: "bubble", impacts: [], jobId: null, lastResult: null, showStagePercentLabels: true, showTotalAbsoluteLabel: true },
          },
        ];
      }
      if (activeStageSessionId === id) setActiveStageSessionId(next[0].id);
      return next;
    });
  };

  const closeRegion = (id: string) => {
    setRegionSessions((prev) => {
      const next = prev.filter((s) => s.id !== id);
      if (!next.length) {
        const nid = newId();
        setActiveRegionSessionId(nid);
        return [
          {
            id: nid,
            title: t("Region {n}", { n: 1 }),
            state: {
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
              mapValueMode: "value",
              mapK: 7,
              mapCustomBins: "",
              mapNormMode: "linear",
              mapRobust: 2.0,
              mapGamma: 0.7,
            },
          },
        ];
      }
      if (activeRegionSessionId === id) setActiveRegionSessionId(next[0].id);
      return next;
    });
  };

  return (
    <Container maxWidth={false} sx={{ py: 3, px: { xs: 2, md: 3 } }}>
      <Stack spacing={2}>
        <Tabs value={inner} onChange={(_, v) => setInner(v)} textColor="inherit" indicatorColor="secondary">
          <Tab value="stage" label={t("Stage analysis")} />
          <Tab value="region" label={t("Region analysis")} />
        </Tabs>

        {inner === "stage" ? (
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="subtitle2" sx={{ fontWeight: 700, opacity: 0.8 }}>
                {t("Tabs")}
              </Typography>
              <Tabs
                value={activeStageSessionId}
                onChange={(_, v) => setActiveStageSessionId(String(v))}
                variant="scrollable"
                scrollButtons="auto"
                textColor="inherit"
                indicatorColor="secondary"
                sx={{ flex: 1, minHeight: 36 }}
              >
                {stageSessions.map((s) => (
                  <Tab
                    key={s.id}
                    value={s.id}
                    sx={{ minHeight: 36 }}
                    label={
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        <Box>{s.title}</Box>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            openRename("stage", s.id, s.title);
                          }}
                        >
                          <EditIcon fontSize="inherit" />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            closeStage(s.id);
                          }}
                        >
                          <CloseIcon fontSize="inherit" />
                        </IconButton>
                      </Box>
                    }
                  />
                ))}
              </Tabs>
              <Tooltip title={t("New stage tab")}>
                <IconButton onClick={addStage} size="small">
                  <AddIcon />
                </IconButton>
              </Tooltip>
            </Stack>

            {activeStage ? <StageAnalysisTab stage={activeStage.state} setStage={setStageState} /> : null}
          </Stack>
        ) : (
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="subtitle2" sx={{ fontWeight: 700, opacity: 0.8 }}>
                {t("Tabs")}
              </Typography>
              <Tabs
                value={activeRegionSessionId}
                onChange={(_, v) => setActiveRegionSessionId(String(v))}
                variant="scrollable"
                scrollButtons="auto"
                textColor="inherit"
                indicatorColor="secondary"
                sx={{ flex: 1, minHeight: 36 }}
              >
                {regionSessions.map((s) => (
                  <Tab
                    key={s.id}
                    value={s.id}
                    sx={{ minHeight: 36 }}
                    label={
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                        <Box>{s.title}</Box>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            openRename("region", s.id, s.title);
                          }}
                        >
                          <EditIcon fontSize="inherit" />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            closeRegion(s.id);
                          }}
                        >
                          <CloseIcon fontSize="inherit" />
                        </IconButton>
                      </Box>
                    }
                  />
                ))}
              </Tabs>
              <Tooltip title={t("New region tab")}>
                <IconButton onClick={addRegion} size="small">
                  <AddIcon />
                </IconButton>
              </Tooltip>
            </Stack>

            {activeRegion ? <RegionAnalysisTab region={activeRegion.state} setRegion={setRegionState} /> : null}
          </Stack>
        )}
      </Stack>

      <Dialog open={renameOpen} onClose={() => setRenameOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>{t("Rename tab")}</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label={t("Name")}
            fullWidth
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") applyRename();
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenameOpen(false)}>{t("Cancel")}</Button>
          <Button variant="contained" onClick={applyRename}>
            {t("OK")}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
}
