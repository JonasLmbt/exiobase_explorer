import { useMemo, useState } from "react";
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
  TextField,
  Typography,
} from "@mui/material";
import { api, type JobRequest } from "../../api";
import { useAppState } from "../../app/state";
import { useLog } from "../../app/log";
import { regionMethods } from "./methodRegistry";

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

            <FormControl sx={{ minWidth: 320, flex: 1 }}>
              <InputLabel id="impact-label">Impact</InputLabel>
              <Select
                labelId="impact-label"
                label="Impact"
                multiple={method.maxImpacts > 1}
                value={method.maxImpacts > 1 ? impacts : impacts.slice(0, 1)}
                onChange={(e) => {
                  const v = typeof e.target.value === "string" ? e.target.value.split(",") : e.target.value;
                  const next = (v as string[]).slice(0, method.maxImpacts);
                  setImpacts(next);
                }}
                renderValue={(selected) =>
                  Array.isArray(selected) ? (selected as string[]).join(", ") : String(selected)
                }
              >
                {(impactsQ.data?.impacts ?? []).map((it) => (
                  <MenuItem key={it.impact} value={it.impact}>
                    {method.maxImpacts > 1 ? (
                      <Checkbox size="small" checked={impacts.includes(it.impact)} sx={{ mr: 1 }} />
                    ) : null}
                    {it.impact}
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

          {(createJobM.isPending || jobStatusQ.isFetching) && (
            <Stack direction="row" spacing={1} alignItems="center" sx={{ opacity: 0.9 }}>
              <CircularProgress size={18} />
              <Typography variant="body2">Berechne…</Typography>
            </Stack>
          )}

          {jobResultQ.data?.result && isImageResult(jobResultQ.data.result) ? (
            <Box
              component="img"
              alt={method.label}
              sx={{ width: "100%", maxWidth: 1100, borderRadius: 2, border: "1px solid rgba(255,255,255,0.12)" }}
              src={`data:${jobResultQ.data.result.mime};base64,${jobResultQ.data.result.data}`}
            />
          ) : null}

          {jobResultQ.data?.result && !isImageResult(jobResultQ.data.result) ? (
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
