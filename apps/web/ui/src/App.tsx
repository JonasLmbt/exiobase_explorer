import { useCallback, useMemo, useState } from "react";
import {
  AppBar,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Container,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Toolbar,
  Typography,
} from "@mui/material";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, type Impacts, type JobRequest } from "./api";

export default function App() {
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [year, setYear] = useState<number>(2022);
  const [language, setLanguage] = useState<string>("Deutsch");
  const [impact, setImpact] = useState<string>("");

  const healthQ = useQuery({ queryKey: ["health"], queryFn: api.health, enabled: false, retry: false });
  const yearsQ = useQuery({ queryKey: ["years"], queryFn: api.years, enabled: false, retry: false });
  const languagesQ = useQuery({
    queryKey: ["languages", year],
    queryFn: () => api.languages(year),
    enabled: false,
    retry: false,
  });
  const impactsQ = useQuery<Impacts>({
    queryKey: ["impacts", year, language],
    queryFn: () => api.impacts(year, language),
    enabled: false,
    retry: false,
  });

  const defaultJobPayload = useMemo<JobRequest>(
    () => ({
      year,
      language,
      selection: { mode: "all", regions: [], sectors: [], indices: [] },
      analysis: { type: "stage_bubble", impacts: impact ? [impact] : [], params: {} },
    }),
    [impact, language, year],
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
    const [, yearsRes] = await Promise.all([healthQ.refetch(), yearsQ.refetch()]);
    if (yearsRes.data?.years?.length && !yearsRes.data.years.includes(String(year))) {
      const first = Number(yearsRes.data.years[0]);
      if (!Number.isNaN(first)) setYear(first);
    }
    await Promise.all([languagesQ.refetch(), impactsQ.refetch()]);
    await createJobM.mutateAsync();
  }, [createJobM, healthQ, impactsQ, languagesQ, year, yearsQ]);

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

              <Stack spacing={2} sx={{ mt: 2 }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
                  Bubble diagram (MVP)
                </Typography>

                <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                  <FormControl sx={{ minWidth: 180 }}>
                    <InputLabel id="year-label">Year</InputLabel>
                    <Select
                      labelId="year-label"
                      label="Year"
                      value={year}
                      onChange={(e) => setYear(Number(e.target.value))}
                    >
                      {(yearsQ.data?.years ?? ["2022"]).map((y) => (
                        <MenuItem key={y} value={Number(y)}>
                          {y}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  <FormControl sx={{ minWidth: 220 }}>
                    <InputLabel id="lang-label">Language</InputLabel>
                    <Select
                      labelId="lang-label"
                      label="Language"
                      value={language}
                      onChange={(e) => setLanguage(String(e.target.value))}
                    >
                      {(languagesQ.data?.languages ?? [language]).map((l) => (
                        <MenuItem key={l} value={l}>
                          {l}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>

                  <FormControl sx={{ minWidth: 320, flex: 1 }}>
                    <InputLabel id="impact-label">Impact</InputLabel>
                    <Select
                      labelId="impact-label"
                      label="Impact"
                      value={impact}
                      onChange={(e) => setImpact(String(e.target.value))}
                    >
                      {(impactsQ.data?.impacts ?? []).map((it) => (
                        <MenuItem key={it.impact} value={it.impact}>
                          {it.impact}
                          {it.unit ? ` (${it.unit})` : ""}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Stack>
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
                    Result
                  </Typography>
                  {isImageResult(jobResultQ.data.result) ? (
                    <Box
                      component="img"
                      alt="Bubble diagram"
                      sx={{ mt: 1, width: "100%", maxWidth: 980, borderRadius: 2, border: "1px solid rgba(255,255,255,0.12)" }}
                      src={`data:${jobResultQ.data.result.mime};base64,${jobResultQ.data.result.data}`}
                    />
                  ) : (
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
                  )}
                </Box>
              ) : null}

              {(createJobM.isPending || jobStatusQ.isFetching) && (
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 2, opacity: 0.9 }}>
                  <CircularProgress size={18} />
                  <Typography variant="body2">Berechne…</Typography>
                </Stack>
              )}

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

function isImageResult(v: unknown): v is { kind: "image_base64"; mime: string; data: string } {
  if (!v || typeof v !== "object") return false;
  const obj = v as any;
  return obj.kind === "image_base64" && typeof obj.mime === "string" && typeof obj.data === "string";
}
