import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
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
  Typography,
} from "@mui/material";
import { api, type JobRequest } from "../../api";
import { useAppState } from "../../app/state";
import { useLog } from "../../app/log";
import { stageMethods } from "./methodRegistry";
import StageMatrixChart, { type StageTableV1 } from "./StageMatrixChart";

export default function StageAnalysisTab() {
  const { year, language, selection, stage, setStage } = useAppState();
  const log = useLog();
  const methodId = stage.methodId;
  const impacts = stage.impacts;
  const jobId = stage.jobId;
  const [error, setError] = useState<string | null>(null);

  const method = useMemo(() => stageMethods.find((m) => m.id === methodId) ?? stageMethods[0], [methodId]);

  const impactsQ = useQuery({
    queryKey: ["impacts", year, language],
    queryFn: () => api.impacts(year, language),
    retry: false,
  });

  useEffect(() => {
    if (impacts.length) return;
    const items = impactsQ.data?.impacts ?? [];
    if (!items.length) return;

    const want = ["wertschöpfung", "arbeitszeit", "treibhausgasemissionen", "wasserverbrauch", "landnutzung"];
    const keyByWanted: Record<string, string | null> = {};
    for (const w of want) keyByWanted[w] = null;

    for (const it of items) {
      const lbl = (it.label ?? "").toString().trim().toLowerCase();
      for (const w of want) {
        if (keyByWanted[w]) continue;
        if (lbl === w || lbl.startsWith(w) || lbl.includes(w)) keyByWanted[w] = it.key;
      }
    }

    const defaults = want.map((w) => keyByWanted[w]).filter(Boolean) as string[];
    if (defaults.length) {
      setStage((s) => ({ ...s, impacts: defaults }));
      return;
    }

    const first = items[0]?.key;
    if (first) setStage((s) => ({ ...s, impacts: [first] }));
  }, [impacts.length, impactsQ.data?.impacts, setStage]);

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
      analysis: { type: method.analysisType, impacts, params: {} },
    };
  }, [impacts, language, method.analysisType, selection, year]);

  const createJobM = useMutation({
    mutationFn: () => api.createJob(payload),
    onSuccess: (data) => {
      setStage((s) => ({ ...s, jobId: data.job_id }));
      log.info(`Stage job started: ${data.job_id}`);
    },
    onError: (e) => log.error(`Stage job failed: ${String(e)}`),
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
    setStage((s) => ({ ...s, lastResult: jobResultQ.data!.result }));
  }, [jobResultQ.data?.result, setStage]);

  const labelByKey = useMemo(() => {
    const map: Record<string, string> = {};
    (impactsQ.data?.impacts ?? []).forEach((it) => {
      map[it.key] = it.label;
    });
    return map;
  }, [impactsQ.data?.impacts]);

  const onRun = () => {
    setError(null);
    createJobM.mutate(undefined, { onError: (e) => setError(String(e)) });
  };

  const runDisabled = impacts.length === 0 || createJobM.isPending;

  return (
    <Card>
      <CardContent>
        <Stack spacing={2}>
          <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
            Stage analysis
          </Typography>

          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            <FormControl sx={{ minWidth: 220 }}>
              <InputLabel id="method-label">Method</InputLabel>
              <Select
                labelId="method-label"
                label="Method"
                value={methodId}
                onChange={(e) => setStage((s) => ({ ...s, methodId: String(e.target.value) }))}
              >
                {stageMethods.map((m) => (
                  <MenuItem key={m.id} value={m.id}>
                    {m.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl sx={{ minWidth: 320, flex: 1 }}>
              <InputLabel id="impact-label">Impact</InputLabel>
              <Select
                labelId="impact-label"
                label="Impact"
                multiple
                value={impacts}
                onChange={(e) =>
                  setStage((s) => ({
                    ...s,
                    impacts: typeof e.target.value === "string" ? e.target.value.split(",") : e.target.value,
                  }))
                }
                renderValue={(selected) => (selected as string[]).map((k) => labelByKey[k] ?? k).join(", ")}
              >
                {(impactsQ.data?.impacts ?? []).map((it) => (
                  <MenuItem key={it.key} value={it.key}>
                    <Checkbox size="small" checked={impacts.includes(it.key)} sx={{ mr: 1 }} />
                    {it.label}
                    {it.unit ? ` (${it.unit})` : ""}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

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

          {jobResultQ.data?.result && isStageTable(jobResultQ.data.result) ? (
            <StageMatrixChart
              data={jobResultQ.data.result}
              impactLabelByKey={labelByKey}
              onCellClick={({ impactKey, stage, value }) =>
                log.info(`Clicked cell: ${labelByKey[impactKey] ?? impactKey} / ${stage} = ${(value * 100).toFixed(2)}%`)
              }
            />
          ) : null}

          {!jobResultQ.data?.result && stage.lastResult && isStageTable(stage.lastResult) ? (
            <StageMatrixChart
              data={stage.lastResult}
              impactLabelByKey={labelByKey}
              onCellClick={({ impactKey, stage, value }) =>
                log.info(`Clicked cell: ${labelByKey[impactKey] ?? impactKey} / ${stage} = ${(value * 100).toFixed(2)}%`)
              }
            />
          ) : null}

          {jobResultQ.data?.result && isImageResult(jobResultQ.data.result) ? (
            <Box
              component="img"
              alt={method.label}
              sx={{ width: "100%", maxWidth: 1100, borderRadius: 2, border: "1px solid rgba(255,255,255,0.12)" }}
              src={`data:${jobResultQ.data.result.mime};base64,${jobResultQ.data.result.data}`}
            />
          ) : null}

          {jobResultQ.data?.result &&
          !isImageResult(jobResultQ.data.result) &&
          !isStageTable(jobResultQ.data.result) ? (
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

function isStageTable(v: unknown): v is StageTableV1 {
  if (!v || typeof v !== "object") return false;
  const obj = v as any;
  return obj.kind === "stage_table_v1" && Array.isArray(obj.stages) && Array.isArray(obj.impacts);
}
