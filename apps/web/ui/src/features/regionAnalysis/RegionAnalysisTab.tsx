import { useEffect, useMemo, useState, type Dispatch, type SetStateAction } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Checkbox,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { api, type JobRequest } from "../../api";
import { useAppState, type RegionState } from "../../app/state";
import { useLog } from "../../app/log";
import { regionMethods } from "./methodRegistry";
import WorldMapLeaflet, { type GeoJsonV1 } from "./WorldMapLeaflet";
import ReactECharts from "echarts-for-react";
import RegionContributionDialog from "./RegionContributionDialog";

export default function RegionAnalysisTab({
  region,
  setRegion,
}: {
  region: RegionState;
  setRegion: Dispatch<SetStateAction<RegionState>>;
}) {
  const { year, language, selection } = useAppState();
  const log = useLog();
  const [error, setError] = useState<string | null>(null);
  const [contribOpen, setContribOpen] = useState(false);
  const [contribRegionExiobase, setContribRegionExiobase] = useState<string | null>(null);
  const [contribRegionLabel, setContribRegionLabel] = useState<string>("");
  const methodId = region.methodId;
  const impacts = region.impacts;
  const n = region.n;
  const jobId = region.jobId;

  const method = useMemo(() => regionMethods.find((m) => m.id === methodId) ?? regionMethods[0], [methodId]);

  const impactsQ = useQuery({
    queryKey: ["impacts", year, language],
    queryFn: () => api.impacts(year, language),
    retry: false,
  });

  const impactOptions = impactsQ.data?.impacts ?? [];
  const selectedImpactOptions = useMemo(() => {
    const byKey = new Map(impactOptions.map((o) => [o.key, o] as const));
    return impacts.map((k) => byKey.get(k)).filter(Boolean) as typeof impactOptions;
  }, [impactOptions, impacts]);

  useEffect(() => {
    if (impacts.length) return;
    const first = impactsQ.data?.impacts?.[0]?.key;
    if (first) setRegion((s) => ({ ...s, impacts: [first] }));
  }, [impacts.length, impactsQ.data?.impacts, setRegion]);

  const payload = useMemo<JobRequest>(() => {
    const sel =
      selection.mode === "all"
        ? { mode: "all" as const, regions: [], sectors: [], indices: [] }
        : selection.mode === "indices"
          ? { mode: "indices" as const, regions: [], sectors: [], indices: selection.indices }
          : { mode: "regions_sectors" as const, regions: selection.regions, sectors: selection.sectors, indices: [] };

    const trimmed = impacts.slice(0, method.maxImpacts);
    const params = method.analysisType === "region_topn" || method.analysisType === "region_flopn" ? { n } : {};

    return {
      year,
      language,
      selection: sel,
      analysis: { type: method.analysisType, impacts: trimmed, params },
    };
  }, [impacts, language, method.analysisType, method.maxImpacts, n, selection, year]);

  const createJobM = useMutation({
    mutationFn: () => api.createJob(payload),
    onSuccess: (data) => {
      setRegion((s) => ({ ...s, jobId: data.job_id }));
      log.info(`Region job started: ${data.job_id}`);
    },
    onError: (e) => log.error(`Region job failed: ${String(e)}`),
  });

  const jobStatusQ = useQuery({
    queryKey: ["job", jobId, "status"],
    queryFn: () => api.jobStatus(jobId!),
    enabled: Boolean(jobId),
    refetchInterval: (q) => (q.state.data?.state === "done" || q.state.data?.state === "failed" ? false : 500),
    retry: false,
  });

  const jobResultQ = useQuery({
    queryKey: ["job", jobId, "result"],
    queryFn: () => api.jobResult(jobId!),
    enabled: Boolean(jobId) && jobStatusQ.data?.state === "done",
    retry: false,
  });

  useEffect(() => {
    if (!jobResultQ.data?.result) return;
    setRegion((s) => ({ ...s, lastResult: jobResultQ.data!.result }));
  }, [jobResultQ.data?.result, setRegion]);

  const onRun = () => {
    setError(null);
    createJobM.mutate(undefined, { onError: (e) => setError(String(e)) });
  };

  const runDisabled = impacts.length === 0 || createJobM.isPending;

  const result = jobResultQ.data?.result ?? region.lastResult;
  const impactKey = impacts[0] ?? "";
  const impactLabelByKey = useMemo(() => {
    const m: Record<string, string> = {};
    (impactsQ.data?.impacts ?? []).forEach((it) => (m[it.key] = it.label));
    return m;
  }, [impactsQ.data?.impacts]);

  return (
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "420px 1fr" }, gap: 2, alignItems: "start" }}>
      <Card>
        <CardContent>
          <Stack spacing={2}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
              Region analysis
            </Typography>

            <FormControl>
              <InputLabel id="method-label">Method</InputLabel>
              <Select
                labelId="method-label"
                label="Method"
                value={methodId}
                onChange={(e) => setRegion((s) => ({ ...s, methodId: String(e.target.value) }))}
              >
                {regionMethods.map((m) => (
                  <MenuItem key={m.id} value={m.id}>
                    {m.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {(method.analysisType === "region_topn" || method.analysisType === "region_flopn") ? (
              <TextField
                label="n"
                type="number"
                size="small"
                value={n}
                onChange={(e) => setRegion((s) => ({ ...s, n: Math.max(1, Number(e.target.value) || 1) }))}
                inputProps={{ min: 1, max: 50 }}
              />
            ) : null}

            <Autocomplete
              multiple={method.maxImpacts > 1}
              disablePortal
              disableCloseOnSelect={method.maxImpacts > 1}
              options={impactOptions}
              value={method.maxImpacts > 1 ? selectedImpactOptions : (selectedImpactOptions[0] ?? null)}
              onChange={(_, next) => {
                if (method.maxImpacts > 1) {
                  const arr = Array.isArray(next) ? next : [];
                  setRegion((s) => ({ ...s, impacts: arr.slice(0, method.maxImpacts).map((x) => x.key) }));
                } else {
                  const one = Array.isArray(next) ? next[0] : next;
                  setRegion((s) => ({ ...s, impacts: one ? [one.key] : [] }));
                }
              }}
              getOptionLabel={(o) => `${o.label}${o.unit ? ` (${o.unit})` : ""}`}
              slotProps={{
                paper: {
                  sx: (t) => ({
                    bgcolor: t.palette.mode === "dark" ? "#0f172a" : t.palette.background.paper,
                    backgroundImage: "none",
                    opacity: 1,
                    border: t.palette.mode === "dark" ? "1px solid rgba(255,255,255,0.12)" : "1px solid rgba(0,0,0,0.12)",
                  }),
                },
              }}
              filterOptions={(opts, state) => {
                const q = state.inputValue.trim().toLowerCase();
                if (!q) return opts;
                return opts.filter((o) => (o.label ?? "").toLowerCase().includes(q) || (o.key ?? "").toLowerCase().includes(q));
              }}
              renderInput={(params) => <TextField {...params} label="Impact" placeholder="Search impacts…" size="small" />}
              ListboxProps={{ style: { maxHeight: 360 } }}
              isOptionEqualToValue={(a, b) => a.key === b.key}
              renderOption={(props, option, { selected }) => (
                <li {...props} key={option.key}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, width: "100%" }}>
                    {method.maxImpacts > 1 ? <Checkbox size="small" checked={selected} sx={{ mr: 0.5 }} /> : null}
                    <Box
                      sx={{
                        width: 10,
                        height: 10,
                        borderRadius: 999,
                        background: option.color || "rgba(255,255,255,0.3)",
                        border: "1px solid rgba(0,0,0,0.3)",
                        flex: "0 0 auto",
                      }}
                    />
                    <Box sx={{ flex: 1, minWidth: 0, opacity: selected ? 0.95 : 0.8 }}>
                      <Box sx={{ fontWeight: selected ? 700 : 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {option.label}
                      </Box>
                      <Box sx={{ fontSize: "0.8rem", opacity: 0.7, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                        {option.key}
                      </Box>
                    </Box>
                  </Box>
                </li>
              )}
            />

            <Button variant="contained" onClick={onRun} disabled={runDisabled} size="large" sx={{ py: 1.2 }}>
              Run
            </Button>

            <Typography variant="body2" sx={{ opacity: 0.75 }}>
              Auswahl kommt aus dem Tab <b>Selection</b> (Region/Sektor). Ohne Auswahl wird global gerechnet.
            </Typography>

            <Stack spacing={1} sx={{ opacity: 0.9 }}>
              <Stack direction="row" spacing={2}>
                <Box sx={{ minWidth: 80 }}>Job</Box>
                <Box sx={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" }}>{jobId ?? "—"}</Box>
              </Stack>
              <Stack direction="row" spacing={2}>
                <Box sx={{ minWidth: 80 }}>Status</Box>
                <Box sx={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" }}>
                  {jobStatusQ.data ? `${jobStatusQ.data.state} (${Math.round(jobStatusQ.data.progress * 100)}%)` : "—"}
                </Box>
              </Stack>
            </Stack>

            {jobStatusQ.data?.state === "failed" ? (
              <Box sx={{ color: "#ffd2d2" }}>
                <Typography variant="body2" sx={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" }}>
                  {jobStatusQ.data.message ?? "Job failed"}
                </Typography>
              </Box>
            ) : null}

            {(createJobM.isPending || jobStatusQ.isFetching) && (
              <Stack direction="row" spacing={1} alignItems="center" sx={{ opacity: 0.9 }}>
                <CircularProgress size={18} />
                <Typography variant="body2">Berechne…</Typography>
              </Stack>
            )}

            {error ? (
              <Box sx={{ color: "#ffd2d2" }}>
                <Typography variant="body2">{error}</Typography>
              </Box>
            ) : null}
          </Stack>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          {result && isGeoJson(result) ? (
            <WorldMapLeaflet
              data={result}
              onRegionClick={({ exiobase, region }) => {
                if (!impactKey) return;
                setContribRegionExiobase(exiobase);
                setContribRegionLabel(region);
                setContribOpen(true);
              }}
            />
          ) : null}
          {result && isTable(result) ? <ReactECharts option={tableToBarOption(result)} style={{ height: 480, width: "100%" }} /> : null}
          {result && isPie(result) ? <ReactECharts option={pieToOption(result)} style={{ height: 420, width: "100%" }} /> : null}

          {result && !isGeoJson(result) && !isTable(result) && !isPie(result) ? (
            <Box
              component="pre"
              sx={{
                p: 1.5,
                borderRadius: 2,
                background: "rgba(255,255,255,0.04)",
                overflow: "auto",
                fontSize: "0.85rem",
              }}
            >
              {JSON.stringify(result, null, 2)}
            </Box>
          ) : null}
        </CardContent>
      </Card>

      {contribRegionExiobase ? (
        <RegionContributionDialog
          open={contribOpen}
          onClose={() => setContribOpen(false)}
          impactKey={impactKey}
          impactLabel={impactLabelByKey[impactKey] ?? impactKey}
          regionExiobase={contribRegionExiobase}
          regionLabel={contribRegionLabel || contribRegionExiobase}
        />
      ) : null}
    </Box>
  );
}

function isGeoJson(v: unknown): v is GeoJsonV1 {
  if (!v || typeof v !== "object") return false;
  const obj = v as any;
  return obj.kind === "geojson_v1" && typeof obj.geojson === "string";
}

function isTable(v: unknown): v is { kind: "table_v1"; columns: string[]; index: string[]; values: number[][]; meta?: any } {
  if (!v || typeof v !== "object") return false;
  const obj = v as any;
  return obj.kind === "table_v1" && Array.isArray(obj.columns) && Array.isArray(obj.index) && Array.isArray(obj.values);
}

function isPie(v: unknown): v is { kind: "pie_v1"; rows: { label: string; value: number; unit?: string }[]; meta?: any } {
  if (!v || typeof v !== "object") return false;
  const obj = v as any;
  return obj.kind === "pie_v1" && Array.isArray(obj.rows);
}

function tableToBarOption(tbl: { columns: string[]; index: string[]; values: number[][]; meta?: any }) {
  const series = tbl.columns.map((name, j) => ({
    name,
    type: "bar",
    data: tbl.values.map((row) => row[j]),
  }));

  return {
    tooltip: { trigger: "axis" },
    legend: { top: 0 },
    grid: { left: 70, right: 20, top: 50, bottom: 80 },
    xAxis: { type: "category", data: tbl.index, axisLabel: { rotate: 30 } },
    yAxis: { type: "value" },
    series,
  };
}

function pieToOption(pie: { rows: { label: string; value: number; unit?: string }[]; meta?: any }) {
  return {
    tooltip: { trigger: "item" },
    series: [
      {
        type: "pie",
        radius: ["30%", "70%"],
        data: pie.rows.map((r) => ({ name: r.label, value: r.value })),
        label: { overflow: "truncate" },
      },
    ],
  };
}
