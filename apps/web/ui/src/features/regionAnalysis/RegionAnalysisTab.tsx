import { useEffect, useMemo, useState } from "react";
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
import { useAppState } from "../../app/state";
import { useLog } from "../../app/log";
import { regionMethods } from "./methodRegistry";
import WorldMapLeaflet, { type GeoJsonV1 } from "./WorldMapLeaflet";
import ReactECharts from "echarts-for-react";

export default function RegionAnalysisTab() {
  const { year, language, selection } = useAppState();
  const log = useLog();
  const [methodId, setMethodId] = useState(regionMethods[0]?.id ?? "world_map");
  const [impacts, setImpacts] = useState<string[]>([]);
  const [n, setN] = useState<number>(10);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const method = useMemo(() => regionMethods.find((m) => m.id === methodId) ?? regionMethods[0], [methodId]);

  const impactsQ = useQuery({
    queryKey: ["impacts", year, language],
    queryFn: () => api.impacts(year, language),
    retry: false,
  });

  useEffect(() => {
    if (impacts.length) return;
    const first = impactsQ.data?.impacts?.[0]?.key;
    if (first) setImpacts([first]);
  }, [impacts.length, impactsQ.data?.impacts]);

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
      setJobId(data.job_id);
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

  const labelByKey = useMemo(() => {
    const map: Record<string, string> = {};
    (impactsQ.data?.impacts ?? []).forEach((it) => {
      map[it.key] = it.label;
    });
    return map;
  }, [impactsQ.data?.impacts]);

  const impactOptions = impactsQ.data?.impacts ?? [];
  const selectedImpactOptions = useMemo(() => {
    const byKey = new Map(impactOptions.map((o) => [o.key, o] as const));
    return impacts.map((k) => byKey.get(k)).filter(Boolean) as typeof impactOptions;
  }, [impactOptions, impacts]);

  const runDisabled = impacts.length === 0 || createJobM.isPending;

  const onRun = () => {
    setError(null);
    createJobM.mutate(undefined, { onError: (e) => setError(String(e)) });
  };

  return (
    <Card>
      <CardContent>
        <Stack spacing={2}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            Region analysis
          </Typography>

          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            <FormControl sx={{ minWidth: 220 }}>
              <InputLabel id="method-label">Method</InputLabel>
              <Select labelId="method-label" label="Method" value={methodId} onChange={(e) => setMethodId(String(e.target.value))}>
                {regionMethods.map((m) => (
                  <MenuItem key={m.id} value={m.id}>
                    {m.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {(method.analysisType === "region_topn" || method.analysisType === "region_flopn") && (
              <TextField
                label="n"
                type="number"
                size="small"
                value={n}
                onChange={(e) => setN(Math.max(1, Number(e.target.value) || 1))}
                sx={{ width: 120 }}
                inputProps={{ min: 1, max: 50 }}
              />
            )}

            <Autocomplete
              multiple={method.maxImpacts > 1}
              disableCloseOnSelect={method.maxImpacts > 1}
              options={impactOptions}
              value={
                method.maxImpacts > 1
                  ? selectedImpactOptions
                  : (selectedImpactOptions[0] ?? null)
              }
              onChange={(_, next) => {
                if (method.maxImpacts > 1) {
                  const arr = Array.isArray(next) ? next : [];
                  setImpacts(arr.slice(0, method.maxImpacts).map((x) => x.key));
                } else {
                  const one = Array.isArray(next) ? next[0] : next;
                  setImpacts(one ? [one.key] : []);
                }
              }}
              getOptionLabel={(o) => `${o.label}${o.unit ? ` (${o.unit})` : ""}`}
              filterOptions={(opts, state) => {
                const q = state.inputValue.trim().toLowerCase();
                if (!q) return opts;
                return opts.filter(
                  (o) => (o.label ?? "").toLowerCase().includes(q) || (o.key ?? "").toLowerCase().includes(q),
                );
              }}
              renderInput={(params) => <TextField {...params} label="Impact" placeholder="Search impacts…" size="small" />}
              sx={{ minWidth: 360, flex: 1 }}
              isOptionEqualToValue={(a, b) => a.key === b.key}
              renderOption={(props, option, { selected }) => (
                <li {...props} key={option.key}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, width: "100%" }}>
                    {method.maxImpacts > 1 ? (
                      <Checkbox size="small" checked={selected} sx={{ mr: 0.5 }} />
                    ) : null}
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
                      <Box
                        sx={{
                          fontWeight: selected ? 700 : 500,
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {option.label}
                      </Box>
                      <Box
                        sx={{
                          fontSize: "0.8rem",
                          opacity: 0.7,
                          whiteSpace: "nowrap",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {option.key}
                      </Box>
                    </Box>
                  </Box>
                </li>
              )}
            />

            <Button variant="contained" onClick={onRun} disabled={runDisabled}>
              Run
            </Button>
          </Stack>

          <Typography variant="body2" sx={{ opacity: 0.75 }}>
            Auswahl kommt aus dem Tab <b>Selection</b> (Region/Sektor). Ohne Auswahl wird global gerechnet.
          </Typography>

          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ opacity: 0.9 }}>
            <Box sx={{ minWidth: 100 }}>Job</Box>
            <Box sx={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" }}>{jobId ?? "—"}</Box>
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ opacity: 0.9 }}>
            <Box sx={{ minWidth: 100 }}>Status</Box>
            <Box sx={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" }}>
              {jobStatusQ.data ? `${jobStatusQ.data.state} (${Math.round(jobStatusQ.data.progress * 100)}%)` : "—"}
            </Box>
          </Stack>

          {jobStatusQ.data?.state === "failed" ? (
            <Box sx={{ color: "#ffd2d2" }}>
              <Typography
                variant="body2"
                sx={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" }}
              >
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

          {jobResultQ.isFetching ? (
            <Typography variant="body2" sx={{ opacity: 0.8 }}>
              Lade Ergebnis…
            </Typography>
          ) : null}

          {jobResultQ.data?.result && isGeoJson(jobResultQ.data.result) ? (
            <WorldMapLeaflet data={jobResultQ.data.result} />
          ) : null}

          {jobResultQ.data?.result && isTable(jobResultQ.data.result) ? (
            <ReactECharts option={tableToBarOption(jobResultQ.data.result)} style={{ height: 480, width: "100%" }} />
          ) : null}

          {jobResultQ.data?.result && isPie(jobResultQ.data.result) ? (
            <ReactECharts option={pieToOption(jobResultQ.data.result)} style={{ height: 420, width: "100%" }} />
          ) : null}

          {jobResultQ.data?.result &&
          !isGeoJson(jobResultQ.data.result) &&
          !isTable(jobResultQ.data.result) &&
          !isPie(jobResultQ.data.result) ? (
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
              {JSON.stringify(jobResultQ.data.result, null, 2)}
            </Box>
          ) : null}

          {error ? (
            <Box sx={{ color: "#ffd2d2" }}>
              <Typography variant="body2">{error}</Typography>
            </Box>
          ) : null}
        </Stack>
      </CardContent>
    </Card>
  );
}

function isImageResult(v: unknown): v is { kind: "image_base64"; mime: string; data: string } {
  if (!v || typeof v !== "object") return false;
  const obj = v as any;
  return obj.kind === "image_base64" && typeof obj.mime === "string" && typeof obj.data === "string";
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
    grid: { left: 60, right: 20, top: 40, bottom: 90 },
    xAxis: { type: "category", data: tbl.index, axisLabel: { rotate: 35 } },
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
        radius: "70%",
        data: pie.rows.map((r) => ({ name: r.label, value: r.value })),
      },
    ],
  };
}
