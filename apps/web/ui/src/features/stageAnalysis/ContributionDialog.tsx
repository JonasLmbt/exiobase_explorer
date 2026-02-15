import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  Stack,
  Tab,
  Tabs,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import ReactECharts from "echarts-for-react";
import { api, type JobRequest } from "../../api";
import { useAppState } from "../../app/state";

type Dimension = "sectors" | "regions";
type ContribTableV1 = {
  kind: "contrib_table_v1";
  meta?: { unit?: string; stage_id?: string; impact_key?: string; impact_resolved?: string };
  rows: { label: string; share: number; absolute: number }[];
};

function clamp01(x: number) {
  return Math.max(0, Math.min(1, x));
}

function toRgb(hex: string): [number, number, number] | null {
  const h = String(hex || "").trim().replace("#", "");
  if (!/^[0-9a-fA-F]{3}$|^[0-9a-fA-F]{6}$/.test(h)) return null;
  const n = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  const r = parseInt(n.slice(0, 2), 16);
  const g = parseInt(n.slice(2, 4), 16);
  const b = parseInt(n.slice(4, 6), 16);
  return [r, g, b];
}

function rgbToHex([r, g, b]: [number, number, number]) {
  const to = (x: number) => Math.max(0, Math.min(255, Math.round(x))).toString(16).padStart(2, "0");
  return `#${to(r)}${to(g)}${to(b)}`;
}

function mixWithWhite(hex: string, t: number): string {
  const rgb = toRgb(hex);
  if (!rgb) return hex;
  const tt = clamp01(t);
  const [r, g, b] = rgb;
  return rgbToHex([r + (255 - r) * tt, g + (255 - g) * tt, b + (255 - b) * tt] as any);
}

export default function ContributionDialog({
  open,
  onClose,
  impactKeys,
  initialImpactKey,
  stageId,
  stageLabel,
}: {
  open: boolean;
  onClose: () => void;
  impactKeys: string[];
  initialImpactKey?: string;
  stageId: string;
  stageLabel: string;
}) {
  const { year, language, selection } = useAppState();
  const theme = useTheme();

  const [dim, setDim] = useState<Dimension>("sectors");
  const [activeImpact, setActiveImpact] = useState<string>(() => initialImpactKey || impactKeys[0] || "");
  const [view, setView] = useState<"bars" | "pie">("bars");
  const [jobId, setJobId] = useState<string | null>(null);

  useEffect(() => {
    if (!impactKeys.length) return;
    setActiveImpact((cur) =>
      impactKeys.includes(cur)
        ? cur
        : initialImpactKey && impactKeys.includes(initialImpactKey)
          ? initialImpactKey
          : impactKeys[0],
    );
  }, [impactKeys, initialImpactKey]);

  const impactsQ = useQuery({
    queryKey: ["impacts", year, language],
    queryFn: () => api.impacts(year, language),
    retry: false,
  });

  const impactMetaByKey = useMemo(() => {
    const m: Record<string, { label: string; color: string; unit: string }> = {};
    (impactsQ.data?.impacts ?? []).forEach((it) => (m[it.key] = { label: it.label, color: it.color, unit: it.unit }));
    return m;
  }, [impactsQ.data?.impacts]);

  const impactLabel = impactMetaByKey[activeImpact]?.label ?? activeImpact;
  const impactColorRaw = impactMetaByKey[activeImpact]?.color ?? "";
  const impactColor = impactColorRaw || theme.palette.primary.main;

  const payload = useMemo<JobRequest>(() => {
    const sel =
      selection.mode === "all"
        ? { mode: "all" as const, regions: [], sectors: [], indices: [] }
        : selection.mode === "indices"
          ? { mode: "indices" as const, regions: [], sectors: [], indices: selection.indices }
          : { mode: "regions_sectors" as const, regions: selection.regions, sectors: selection.sectors, indices: [] };

    return {
      year,
      language,
      selection: sel,
      analysis: { type: "contrib_breakdown", impacts: [activeImpact], params: { stage_id: stageId, dimension: dim, top_n: 30 } },
    };
  }, [activeImpact, dim, language, selection, stageId, year]);

  const createJobM = useMutation({
    mutationFn: () => api.createJob(payload),
    onSuccess: (data) => setJobId(data.job_id),
    retry: false,
  });

  const statusQ = useQuery({
    queryKey: ["job", jobId, "status"],
    queryFn: () => api.jobStatus(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: (q) => (q.state.data?.state === "done" || q.state.data?.state === "failed" ? false : 400),
    retry: false,
  });

  const resultQ = useQuery({
    queryKey: ["job", jobId, "result"],
    queryFn: () => api.jobResult(jobId!),
    enabled: Boolean(jobId) && statusQ.data?.state === "done",
    retry: false,
  });

  const table = (resultQ.data?.result ?? null) as ContribTableV1 | null;
  const unit = table?.meta?.unit ?? "";

  const start = useCallback(() => {
    setJobId(null);
    createJobM.mutate();
  }, [createJobM]);

  useEffect(() => {
    if (!open) return;
    start();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, dim, activeImpact, stageId]);

  const pieOption = useMemo(() => {
    if (!table || table.kind !== "contrib_table_v1") return null;
    const rows = table.rows.slice(0, 30);
    const total = rows.reduce((acc, r) => acc + (Number.isFinite(r.absolute) ? r.absolute : 0), 0) || 1;
    const colors = rows.map((_, i) => mixWithWhite(impactColor, clamp01(i / Math.max(1, rows.length - 1)) * 0.55));

    return {
      tooltip: {
        trigger: "item",
        formatter: (p: any) => {
          const v = Number(p?.value);
          const pct = (v / total) * 100;
          return `${p?.name}<br/>${pct.toFixed(2)}%<br/>${v.toLocaleString()} ${unit}`;
        },
      },
      series: [
        {
          type: "pie",
          radius: ["30%", "74%"],
          minAngle: 2,
          avoidLabelOverlap: true,
          itemStyle: { borderColor: theme.palette.background.paper, borderWidth: 1 },
          label: { overflow: "truncate" },
          data: rows.map((r, i) => ({ name: r.label, value: r.absolute, itemStyle: { color: colors[i] } })),
        },
      ],
    };
  }, [impactColor, table, theme.palette.background.paper, unit]);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Stack spacing={0.5}>
          <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
            Beitragsanalyse
          </Typography>
          <Typography variant="body2" sx={{ opacity: 0.8 }}>
            {impactLabel} • {stageLabel}
          </Typography>
        </Stack>
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2}>
          {impactKeys.length > 1 ? (
            <Tabs
              value={activeImpact}
              onChange={(_, v) => setActiveImpact(String(v))}
              variant="scrollable"
              allowScrollButtonsMobile
              textColor="inherit"
              indicatorColor="secondary"
            >
              {impactKeys.map((k) => (
                <Tab key={k} value={k} label={impactMetaByKey[k]?.label ?? k} />
              ))}
            </Tabs>
          ) : null}

          <Tabs value={dim} onChange={(_, v) => setDim(v)} textColor="inherit" indicatorColor="secondary">
            <Tab value="sectors" label="Sectors" />
            <Tab value="regions" label="Regions" />
          </Tabs>

          <ToggleButtonGroup
            value={view}
            exclusive
            onChange={(_, v) => (v ? setView(v) : null)}
            size="small"
            sx={{ alignSelf: "flex-start" }}
          >
            <ToggleButton value="bars">Bars</ToggleButton>
            <ToggleButton value="pie">Pie</ToggleButton>
          </ToggleButtonGroup>

          <Stack direction="row" spacing={2} alignItems="center">
            <Button variant="outlined" onClick={start} disabled={createJobM.isPending}>
              Refresh
            </Button>
            <Box sx={{ flex: 1 }} />
            <Typography variant="body2" sx={{ opacity: 0.75 }}>
              {statusQ.data ? `${statusQ.data.state} (${Math.round(statusQ.data.progress * 100)}%)` : "—"}
            </Typography>
          </Stack>

          {statusQ.data?.state === "failed" ? (
            <Typography variant="body2" sx={{ color: "#ffd2d2", fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" }}>
              {statusQ.data.message ?? "Job failed"}
            </Typography>
          ) : null}

          {(createJobM.isPending || statusQ.isFetching || resultQ.isFetching) && (
            <Stack direction="row" spacing={1} alignItems="center" sx={{ opacity: 0.85 }}>
              <CircularProgress size={18} />
              <Typography variant="body2">Lade…</Typography>
            </Stack>
          )}

          {view === "pie" && pieOption ? <ReactECharts option={pieOption} style={{ height: 520, width: "100%" }} /> : null}

          {view === "bars" && table?.kind === "contrib_table_v1" ? (
            <Stack spacing={1}>
              {table.rows.map((r) => (
                <Box
                  key={r.label}
                  sx={{
                    display: "grid",
                    gridTemplateColumns: "1fr 90px 130px",
                    gap: 1.5,
                    alignItems: "center",
                    p: 1,
                    borderRadius: 2,
                    background: "rgba(255,255,255,0.04)",
                  }}
                >
                  <Box sx={{ minWidth: 0 }}>
                    <Typography variant="body2" sx={{ fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {r.label}
                    </Typography>
                    <Box sx={{ height: 6, borderRadius: 999, background: "rgba(255,255,255,0.10)", mt: 0.5, overflow: "hidden" }}>
                      <Box
                        sx={{
                          height: "100%",
                          width: `${clamp01(r.share) * 100}%`,
                          background: alpha(impactColor, theme.palette.mode === "dark" ? 0.85 : 0.9),
                        }}
                      />
                    </Box>
                  </Box>
                  <Typography variant="body2" sx={{ textAlign: "right", fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" }}>
                    {(r.share * 100).toFixed(2)}%
                  </Typography>
                  <Typography variant="body2" sx={{ textAlign: "right", fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" }}>
                    {Number(r.absolute).toLocaleString()} {unit}
                  </Typography>
                </Box>
              ))}
            </Stack>
          ) : null}
        </Stack>
      </DialogContent>
    </Dialog>
  );
}

