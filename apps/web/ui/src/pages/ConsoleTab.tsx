import { useState } from "react";
import { Box, Button, Card, CardContent, Container, Stack, TextField, Typography } from "@mui/material";
import { api, type JobRequest } from "../api";
import { useLog } from "../app/log";
import { useAppState } from "../app/state";
import LogConsole from "../components/LogConsole";
import { useT } from "../app/i18n";

export default function ConsoleTab() {
  const log = useLog();
  const { t } = useT();
  const {
    year,
    setYear,
    language,
    setLanguage,
    themeMode,
    setThemeMode,
    selection,
    selectionSummary,
    stageSessions,
    activeStageSessionId,
    regionSessions,
    activeRegionSessionId,
  } = useAppState();
  const [cmd, setCmd] = useState("");
  const [running, setRunning] = useState(false);

  const run = async () => {
    const input = cmd.trim();
    if (!input || running) return;
    setCmd("");
    const [headRaw, ...rest] = input.split(/\s+/);
    const head = (headRaw || "").toLowerCase();
    const arg = rest.join(" ");

    if (head === "clear") {
      log.clear();
      return;
    }

    log.info(`> ${input}`);
    setRunning(true);
    try {
      if (head === "help" || head === "?") {
        log.info(
          "Commands: help, clear, health, year <YYYY>, lang <Name>, theme <dark|light>, selection, stage, region, job <id>",
        );
        return;
      }

      if (head === "health") {
        const h = await api.health();
        log.info(`API health: ${h.status}`);
        return;
      }

      if (head === "year") {
        const n = Number(rest[0]);
        if (!Number.isFinite(n)) {
          log.error("Usage: year <YYYY>");
          return;
        }
        setYear(n);
        log.info(`year = ${n}`);
        return;
      }

      if (head === "lang" || head === "language") {
        const l = arg.trim();
        if (!l) {
          log.error("Usage: lang <Name>");
          return;
        }
        setLanguage(l);
        log.info(`language = ${l}`);
        return;
      }

      if (head === "theme") {
        const m = (rest[0] || "").toLowerCase();
        if (m !== "dark" && m !== "light") {
          log.error("Usage: theme <dark|light>");
          return;
        }
        setThemeMode(m);
        log.info(`theme = ${m}`);
        return;
      }

      if (head === "selection") {
        log.info(`selection = ${JSON.stringify(selection)}`);
        if (selectionSummary) log.info(`selectionSummary = ${selectionSummary.supplychain_repr}`);
        return;
      }

      if (head === "app.supplychain" || head === "supplychain") {
        const sel =
          selection.mode === "all"
            ? { mode: "all" as const, regions: [], sectors: [], indices: [] }
            : selection.mode === "indices"
              ? { mode: "indices" as const, regions: [], sectors: [], indices: selection.indices }
              : { mode: "regions_sectors" as const, regions: selection.regions, sectors: selection.sectors, indices: [] };

        const payload: { year: number; language: string; selection: JobRequest["selection"] } = {
          year,
          language,
          selection: sel,
        };

        const sum = await api.selectionSummary(payload);
        log.info(sum.supplychain_repr);
        if (sum.hierarchy_kwargs && Object.keys(sum.hierarchy_kwargs).length) {
          log.info(`hierarchy_kwargs = ${JSON.stringify(sum.hierarchy_kwargs)}`);
        }
        return;
      }

      if (head === "stage") {
        const s = stageSessions.find((x) => x.id === activeStageSessionId) ?? stageSessions[0];
        if (!s) {
          log.error("No stage session");
          return;
        }
        log.info(`stage.tab = ${s.title} (${s.id})`);
        log.info(`stage.methodId = ${s.state.methodId}`);
        log.info(`stage.impacts = ${s.state.impacts.join(", ") || "—"}`);
        log.info(`stage.jobId = ${s.state.jobId ?? "—"}`);
        return;
      }

      if (head === "region") {
        const r = regionSessions.find((x) => x.id === activeRegionSessionId) ?? regionSessions[0];
        if (!r) {
          log.error("No region session");
          return;
        }
        log.info(`region.tab = ${r.title} (${r.id})`);
        log.info(`region.methodId = ${r.state.methodId}`);
        log.info(`region.impacts = ${r.state.impacts.join(", ") || "—"}`);
        log.info(`region.jobId = ${r.state.jobId ?? "—"}`);
        return;
      }

      if (head === "job") {
        const id = (rest[0] || "").trim();
        if (!id) {
          log.error("Usage: job <id>");
          return;
        }
        const st = await api.jobStatus(id);
        log.info(`job ${st.job_id}: ${st.state} (${Math.round(st.progress * 100)}%) ${st.message ?? ""}`.trim());
        return;
      }

      log.error(`Unknown command: ${head}. Type "help".`);
    } catch (e) {
      log.error(String(e));
    } finally {
      setRunning(false);
    }
  };

  return (
    <Container sx={{ py: 3 }}>
      <Stack spacing={2}>
        <Card>
          <CardContent>
            <LogConsole title={t("Console output")} />
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ xs: "stretch", sm: "center" }}>
              <Box sx={{ flex: 1 }}>
                <TextField
                  fullWidth
                  size="small"
                  label={t("Command")}
                  placeholder={t('Type "help"…')}
                  value={cmd}
                  onChange={(e) => setCmd(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      run();
                    }
                  }}
                  disabled={running}
                />
                <Typography variant="caption" sx={{ opacity: 0.75 }}>
                  {t("ConsoleTab.QuickHelp")}
                </Typography>
              </Box>
              <Button variant="contained" onClick={run} disabled={running || !cmd.trim()}>
                {t("Run")}
              </Button>
              <Button variant="outlined" onClick={() => setCmd("")} disabled={running || !cmd}>
                {t("Reset")}
              </Button>
              <Button variant="outlined" onClick={() => log.info(`mode=${themeMode}, year=${year}, language=${language}`)} disabled={running}>
                {t("Info")}
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Stack>
    </Container>
  );
}
