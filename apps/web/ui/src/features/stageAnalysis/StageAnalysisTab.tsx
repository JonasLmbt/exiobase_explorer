import { useEffect, useMemo, useState, type Dispatch, type SetStateAction } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
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
import { useAppState, type StageState } from "../../app/state";
import { useLog } from "../../app/log";
import { stageMethods } from "./methodRegistry";
import StageMatrixChart, { type StageTableV1 } from "./StageMatrixChart";
import ContributionDialog from "./ContributionDialog";

export default function StageAnalysisTab({
  stage,
  setStage,
}: {
  stage: StageState;
  setStage: Dispatch<SetStateAction<StageState>>;
}) {
  const { year, language, selection } = useAppState();
  const log = useLog();

  const methodId = stage.methodId;
  const impacts = stage.impacts;
  const jobId = stage.jobId;

  const [error, setError] = useState<string | null>(null);
  const [contribOpen, setContribOpen] = useState(false);
  const [contribImpactKey, setContribImpactKey] = useState<string | null>(null);
  const [contribStageId, setContribStageId] = useState<string | null>(null);
  const [contribStageLabel, setContribStageLabel] = useState<string>("");

  const method = useMemo(() => stageMethods.find((m) => m.id === methodId) ?? stageMethods[0], [methodId]);

  const impactsQ = useQuery({
    queryKey: ["impacts", year, language],
    queryFn: () => api.impacts(year, language),
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

  useEffect(() => {
    if (impacts.length) return;
    const items = impactsQ.data?.impacts ?? [];
    if (!items.length) return;

    const wantLabelsDe = ["Wertschöpfung", "Arbeitszeit", "Treibhausgasemissionen", "Wasserverbrauch", "Landnutzung"];
    const want = (language || "").trim().toLowerCase() === "deutsch" ? wantLabelsDe : [];

    const byExactLabel = new Map<string, string>();
    for (const it of items) {
      const lbl = (it.label ?? "").toString().trim().toLowerCase();
      if (!lbl) continue;
      if (!byExactLabel.has(lbl)) byExactLabel.set(lbl, it.key);
    }

    const defaults: string[] = [];
    for (const w of want) {
      const key = byExactLabel.get(w.toLowerCase());
      if (key) defaults.push(key);
    }
    if (defaults.length) {
      setStage((s) => ({ ...s, impacts: defaults }));
      return;
    }

    const first = items[0]?.key;
    if (first) setStage((s) => ({ ...s, impacts: [first] }));
  }, [impacts.length, impactsQ.data?.impacts, language, setStage]);

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

  const onRun = () => {
    setError(null);
    createJobM.mutate(undefined, { onError: (e) => setError(String(e)) });
  };

  const runDisabled = impacts.length === 0 || createJobM.isPending;

  return (
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "420px 1fr" }, gap: 2, alignItems: "start" }}>
      <Card>
        <CardContent>
          <Stack spacing={2}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
              Stage analysis
            </Typography>

            <FormControl>
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

            <Autocomplete
              multiple
              disablePortal
              disableCloseOnSelect
              options={impactOptions}
              value={selectedImpactOptions}
              onChange={(_, next) => setStage((s) => ({ ...s, impacts: next.map((x) => x.key) }))}
              getOptionLabel={(o) => `${o.label}${o.unit ? ` (${o.unit})` : ""}`}
              filterOptions={(opts, state) => {
                const q = state.inputValue.trim().toLowerCase();
                if (!q) return opts;
                return opts.filter(
                  (o) => (o.label ?? "").toLowerCase().includes(q) || (o.key ?? "").toLowerCase().includes(q),
                );
              }}
              renderInput={(params) => <TextField {...params} label="Impact" placeholder="Search impacts…" size="small" />}
              ListboxProps={{ style: { maxHeight: 360 } }}
              isOptionEqualToValue={(a, b) => a.key === b.key}
              renderOption={(props, option, { selected }) => (
                <li {...props} key={option.key}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1, width: "100%" }}>
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
          {jobResultQ.data?.result && isStageTable(jobResultQ.data.result) ? (
            <StageMatrixChart
              data={jobResultQ.data.result}
              impactLabelByKey={labelByKey}
              onCellClick={({ impactKey, stageId, stageLabel, value }) => {
                log.info(`Clicked cell: ${labelByKey[impactKey] ?? impactKey} / ${stageLabel} = ${(value * 100).toFixed(2)}%`);
                setContribImpactKey(impactKey);
                setContribStageId(stageId);
                setContribStageLabel(stageLabel);
                setContribOpen(true);
              }}
            />
          ) : null}

          {!jobResultQ.data?.result && stage.lastResult && isStageTable(stage.lastResult) ? (
            <StageMatrixChart
              data={stage.lastResult}
              impactLabelByKey={labelByKey}
              onCellClick={({ impactKey, stageId, stageLabel, value }) => {
                log.info(`Clicked cell: ${labelByKey[impactKey] ?? impactKey} / ${stageLabel} = ${(value * 100).toFixed(2)}%`);
                setContribImpactKey(impactKey);
                setContribStageId(stageId);
                setContribStageLabel(stageLabel);
                setContribOpen(true);
              }}
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

          {jobResultQ.data?.result && !isImageResult(jobResultQ.data.result) && !isStageTable(jobResultQ.data.result) ? (
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
        </CardContent>
      </Card>

      {contribImpactKey && contribStageId ? (
        <ContributionDialog
          open={contribOpen}
          onClose={() => setContribOpen(false)}
          impactKey={contribImpactKey}
          impactLabel={labelByKey[contribImpactKey] ?? contribImpactKey}
          stageId={contribStageId}
          stageLabel={contribStageLabel}
        />
      ) : null}
    </Box>
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
