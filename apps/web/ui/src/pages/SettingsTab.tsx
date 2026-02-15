import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, Container, FormControl, InputLabel, MenuItem, Select, Stack, Switch, Typography } from "@mui/material";
import { api } from "../api";
import { useAppState } from "../app/state";
import LogConsole from "../components/LogConsole";

export default function SettingsTab() {
  const { year, setYear, language, setLanguage, themeMode, setThemeMode } = useAppState();

  const yearsQ = useQuery({ queryKey: ["years"], queryFn: api.years, retry: false });
  const languagesQ = useQuery({ queryKey: ["languages", year], queryFn: () => api.languages(year), retry: false });

  return (
    <Container sx={{ py: 3 }}>
      <Stack spacing={2}>
        <Card>
          <CardContent>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
              Settings
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.8 }}>
              Hier stellst du Year/Language ein (wirkt auf Selection + Analysen).
            </Typography>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
              <FormControl sx={{ minWidth: 180 }}>
                <InputLabel id="year-label">Year</InputLabel>
                <Select labelId="year-label" label="Year" value={year} onChange={(e) => setYear(Number(e.target.value))}>
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
            </Stack>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
              Appearance
            </Typography>
            <Stack direction="row" spacing={2} alignItems="center">
              <Switch checked={themeMode === "dark"} onChange={(e) => setThemeMode(e.target.checked ? "dark" : "light")} />
              <Typography variant="body2" sx={{ opacity: 0.85 }}>
                {themeMode === "dark" ? "Dark mode" : "Light mode"}
              </Typography>
            </Stack>
          </CardContent>
        </Card>

        <Card>
          <CardContent>
            <LogConsole title="Console output" />
          </CardContent>
        </Card>
      </Stack>
    </Container>
  );
}
