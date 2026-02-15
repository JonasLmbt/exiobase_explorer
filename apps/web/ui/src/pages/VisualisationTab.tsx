import { useMemo, useState, type Dispatch, type SetStateAction } from "react";
import { Box, Container, IconButton, Stack, Tab, Tabs, Tooltip, Typography } from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import CloseIcon from "@mui/icons-material/Close";
import StageAnalysisTab from "../features/stageAnalysis/StageAnalysisTab";
import RegionAnalysisTab from "../features/regionAnalysis/RegionAnalysisTab";
import { useAppState, type RegionState, type StageState } from "../app/state";

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
  const [inner, setInner] = useState<Inner>("stage");

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
    const title = `Stage ${stageSessions.length + 1}`;
    setStageSessions((prev) => [...prev, { id, title, state: { methodId: "bubble", impacts: [], jobId: null, lastResult: null } }]);
    setActiveStageSessionId(id);
  };

  const addRegion = () => {
    const id = newId();
    const title = `Region ${regionSessions.length + 1}`;
    setRegionSessions((prev) => [
      ...prev,
      { id, title, state: { methodId: "world_map", impacts: [], n: 10, jobId: null, lastResult: null } },
    ]);
    setActiveRegionSessionId(id);
  };

  const closeStage = (id: string) => {
    setStageSessions((prev) => {
      const next = prev.filter((s) => s.id !== id);
      if (!next.length) {
        const nid = newId();
        setActiveStageSessionId(nid);
        return [{ id: nid, title: "Stage 1", state: { methodId: "bubble", impacts: [], jobId: null, lastResult: null } }];
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
        return [{ id: nid, title: "Region 1", state: { methodId: "world_map", impacts: [], n: 10, jobId: null, lastResult: null } }];
      }
      if (activeRegionSessionId === id) setActiveRegionSessionId(next[0].id);
      return next;
    });
  };

  return (
    <Container maxWidth={false} sx={{ py: 3, px: { xs: 2, md: 3 } }}>
      <Stack spacing={2}>
        <Tabs value={inner} onChange={(_, v) => setInner(v)} textColor="inherit" indicatorColor="secondary">
          <Tab value="stage" label="Stage analysis" />
          <Tab value="region" label="Region analysis" />
        </Tabs>

        {inner === "stage" ? (
          <Stack spacing={2}>
            <Stack direction="row" spacing={1} alignItems="center">
              <Typography variant="subtitle2" sx={{ fontWeight: 700, opacity: 0.8 }}>
                Tabs
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
              <Tooltip title="New stage tab">
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
                Tabs
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
              <Tooltip title="New region tab">
                <IconButton onClick={addRegion} size="small">
                  <AddIcon />
                </IconButton>
              </Tooltip>
            </Stack>

            {activeRegion ? <RegionAnalysisTab region={activeRegion.state} setRegion={setRegionState} /> : null}
          </Stack>
        )}
      </Stack>
    </Container>
  );
}
