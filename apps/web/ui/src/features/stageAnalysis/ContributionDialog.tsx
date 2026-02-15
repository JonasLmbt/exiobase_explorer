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
  Typography,
} from "@mui/material";
import { api, type JobRequest } from "../../api";
import { useAppState } from "../../app/state";

type Dimension = "sectors" | "regions";
type ContribTableV1 = {
  kind: "contrib_table_v1";
  meta?: { unit?: string; stage_id?: string; impact_key?: string; impact_resolved?: string };
  rows: { label: string; share: number; absolute: number }[];
};

export default function ContributionDialog({
  open,
  onClose,
  impactKey,
  impactLabel,
  stageId,
  stageLabel,
}: {
  open: boolean;
  onClose: () => void;
  impactKey: string;
  impactLabel: string;
  stageId: string;
  stageLabel: string;
}) {
  const { year, language, selection } = useAppState();
  const [dim, setDim] = useState<Dimension>("sectors");
  const [jobId, setJobId] = useState<string | null>(null);

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
      analysis: { type: "contrib_breakdown", impacts: [impactKey], params: { stage_id: stageId, dimension: dim, top_n: 30 } },
    };
  }, [dim, impactKey, language, selection, stageId, year]);

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
  }, [open, dim, impactKey, stageId]);

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
          <Tabs value={dim} onChange={(_, v) => { setDim(v); }} textColor="inherit" indicatorColor="secondary">
            <Tab value="sectors" label="Sectors" />
            <Tab value="regions" label="Regions" />
          </Tabs>

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

          {table?.kind === "contrib_table_v1" ? (
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
                      <Box sx={{ height: "100%", width: `${Math.max(0, Math.min(1, r.share)) * 100}%`, background: "rgba(138,180,248,0.85)" }} />
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
