import { useCallback, useMemo, useState } from "react";
import {
  AppBar,
  Box,
  Button,
  Card,
  CardContent,
  Container,
  Stack,
  Toolbar,
  Typography,
} from "@mui/material";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, type JobRequest } from "./api";

export default function App() {
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);

  const healthQ = useQuery({ queryKey: ["health"], queryFn: api.health, enabled: false, retry: false });
  const yearsQ = useQuery({ queryKey: ["years"], queryFn: api.years, enabled: false, retry: false });

  const defaultJobPayload = useMemo<JobRequest>(
    () => ({
      year: 2022,
      language: "Deutsch",
      selection: { mode: "all", regions: [], sectors: [], indices: [] },
      analysis: { type: "noop", impacts: [], params: {} },
    }),
    [],
  );

  const createJobM = useMutation({
    mutationFn: () => api.createJob(defaultJobPayload),
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

  const load = useCallback(async () => {
    setError(null);
    await Promise.all([healthQ.refetch(), yearsQ.refetch()]);
    await createJobM.mutateAsync();
  }, []);

  const onClick = useCallback(() => {
    load().catch((e) => setError(String(e)));
  }, [load]);

  return (
    <Box sx={{ minHeight: "100vh" }}>
      <AppBar position="sticky" elevation={0} sx={{ borderBottom: "1px solid rgba(255,255,255,0.12)" }}>
        <Toolbar>
          <Typography variant="h6" sx={{ fontWeight: 700, flexGrow: 1 }}>
            EXIOBASE Explorer
          </Typography>
          <Button variant="contained" onClick={onClick}>
            API testen
          </Button>
        </Toolbar>
      </AppBar>

      <Container sx={{ py: 3 }}>
        <Stack spacing={2}>
          <Card>
            <CardContent>
              <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
                Backend
              </Typography>

              <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                <Box sx={{ minWidth: 160, opacity: 0.85 }}>Health</Box>
                <Box sx={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" }}>
                  {healthQ.data ? healthQ.data.status : "—"}
                </Box>
              </Stack>

              <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mt: 1 }}>
                <Box sx={{ minWidth: 160, opacity: 0.85 }}>Years</Box>
                <Box sx={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" }}>
                  {yearsQ.data?.years?.length ? yearsQ.data.years.join(", ") : "—"}
                </Box>
              </Stack>

              <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mt: 1 }}>
                <Box sx={{ minWidth: 160, opacity: 0.85 }}>Job</Box>
                <Box sx={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" }}>
                  {jobId ?? "—"}
                </Box>
              </Stack>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mt: 1 }}>
                <Box sx={{ minWidth: 160, opacity: 0.85 }}>Job status</Box>
                <Box sx={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" }}>
                  {jobStatusQ.data ? `${jobStatusQ.data.state} (${Math.round(jobStatusQ.data.progress * 100)}%)` : "—"}
                </Box>
              </Stack>

              {jobResultQ.data ? (
                <Box sx={{ mt: 1 }}>
                  <Typography variant="body2" sx={{ opacity: 0.85 }}>
                    Result (stub)
                  </Typography>
                  <Box
                    component="pre"
                    sx={{
                      mt: 0.5,
                      p: 1.5,
                      borderRadius: 2,
                      background: "rgba(255,255,255,0.04)",
                      overflow: "auto",
                      fontSize: "0.85rem",
                    }}
                  >
                    {JSON.stringify(jobResultQ.data.result, null, 2)}
                  </Box>
                </Box>
              ) : null}

              {error ? (
                <Box sx={{ mt: 2, color: "#ffd2d2" }}>
                  <Typography variant="body2">{error}</Typography>
                </Box>
              ) : null}
            </CardContent>
          </Card>
        </Stack>
      </Container>
    </Box>
  );
}
