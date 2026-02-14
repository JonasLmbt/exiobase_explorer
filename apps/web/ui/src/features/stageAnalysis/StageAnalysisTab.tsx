import { useMemo, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
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
  Typography,
} from "@mui/material";
import { api, type JobRequest } from "../../api";
import { useAppState } from "../../app/state";
import { stageMethods } from "./methodRegistry";

export default function StageAnalysisTab() {
  const { year, language, selection } = useAppState();
  const [methodId, setMethodId] = useState(stageMethods[0]?.id ?? "bubble");
  const [impacts, setImpacts] = useState<string[]>([]);
  const [jobId, setJobId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const method = useMemo(() => stageMethods.find((m) => m.id === methodId) ?? stageMethods[0], [methodId]);

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

    return {
      year,
      language,
      selection: sel,
      analysis: { type: method.analysisType, impacts, params: {} },
    };
  }, [impacts, language, method.analysisType, selection, year]);

  const createJobM = useMutation({
    mutationFn: () => api.createJob(payload),
    onSuccess: (data) => setJobId(data.job_id),
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
              <Select labelId="method-label" label="Method" value={methodId} onChange={(e) => setMethodId(String(e.target.value))}>
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
                onChange={(e) => setImpacts(typeof e.target.value === "string" ? e.target.value.split(",") : e.target.value)}
                renderValue={(selected) => (selected as string[]).join(", ")}
              >
                {(impactsQ.data?.impacts ?? []).map((it) => (
                  <MenuItem key={it.impact} value={it.impact}>
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
