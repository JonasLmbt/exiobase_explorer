import { useCallback, useState } from "react";
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

type Health = { status: string };
type Years = { years: string[] };

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [years, setYears] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError(null);
    const h = await fetch("/api/v1/health").then((r) => r.json() as Promise<Health>);
    const y = await fetch("/api/v1/meta/years").then((r) => r.json() as Promise<Years>);
    setHealth(h);
    setYears(y.years);
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
                  {health ? health.status : "—"}
                </Box>
              </Stack>

              <Stack direction={{ xs: "column", sm: "row" }} spacing={2} sx={{ mt: 1 }}>
                <Box sx={{ minWidth: 160, opacity: 0.85 }}>Years</Box>
                <Box sx={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace" }}>
                  {years.length ? years.join(", ") : "—"}
                </Box>
              </Stack>

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
