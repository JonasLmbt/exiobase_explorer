import { useState } from "react";
import { Box, Button, Card, CardContent, Container, Stack, TextField, Typography } from "@mui/material";
import { api } from "../api";
import { useLog } from "../app/log";
import { useAppState } from "../app/state";
import LogConsole from "../components/LogConsole";

export default function ConsoleTab() {
  const log = useLog();
  const { year, setYear, language, setLanguage, themeMode, setThemeMode, selection, selectionSummary, stage } = useAppState();
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
        log.info("Commands: help, clear, health, year <YYYY>, lang <Name>, theme <dark|light>, selection, stage, job <id>");
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

      if (head === "stage") {
        log.info(`stage.methodId = ${stage.methodId}`);
        log.info(`stage.impacts = ${stage.impacts.join(", ") || "—"}`);
        log.info(`stage.jobId = ${stage.jobId ?? "—"}`);
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
            <LogConsole title="Console output" />
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ xs: "stretch", sm: "center" }}>
              <Box sx={{ flex: 1 }}>
                <TextField
                  fullWidth
                  size="small"
                  label="Command"
                  placeholder='Type "help"…'
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
                  Quick: `health`, `year 2022`, `lang Deutsch`, `theme dark|light`, `job &lt;id&gt;`, `clear`
                </Typography>
              </Box>
              <Button variant="contained" onClick={run} disabled={running || !cmd.trim()}>
                Run
              </Button>
              <Button variant="outlined" onClick={() => setCmd("")} disabled={running || !cmd}>
                Reset
              </Button>
              <Button variant="outlined" onClick={() => log.info(`mode=${themeMode}, year=${year}, language=${language}`)} disabled={running}>
                Info
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Stack>
    </Container>
  );
}
