import { useQuery } from "@tanstack/react-query";
import {
  Box,
  Card,
  CardContent,
  Container,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Typography,
} from "@mui/material";
import { api } from "../api";
import { useAppState } from "../app/state";
import TreeMultiSelect from "../components/TreeMultiSelect";

export default function SelectionTab() {
  const { year, setYear, language, setLanguage, selection, setSelection } = useAppState();

  const yearsQ = useQuery({ queryKey: ["years"], queryFn: api.years, retry: false });
  const languagesQ = useQuery({ queryKey: ["languages", year], queryFn: () => api.languages(year), retry: false });
  const regionsQ = useQuery({
    queryKey: ["regionsHierarchy", year, language],
    queryFn: () => api.regionHierarchy(year, language),
    retry: false,
  });
  const sectorsQ = useQuery({
    queryKey: ["sectorsHierarchy", year, language],
    queryFn: () => api.sectorHierarchy(year, language),
    retry: false,
  });

  const regionSel = selection.mode === "regions_sectors" ? selection.regions : [];
  const sectorSel = selection.mode === "regions_sectors" ? selection.sectors : [];

  const setRegionSel = (regions: number[]) => {
    const sectors = sectorSel;
    if (regions.length === 0 && sectors.length === 0) return setSelection({ mode: "all" });
    setSelection({ mode: "regions_sectors", regions, sectors });
  };
  const setSectorSel = (sectors: number[]) => {
    const regions = regionSel;
    if (regions.length === 0 && sectors.length === 0) return setSelection({ mode: "all" });
    setSelection({ mode: "regions_sectors", regions, sectors });
  };

  return (
    <Container sx={{ py: 3 }}>
      <Stack spacing={2}>
        <Card>
          <CardContent>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
              Selection
            </Typography>

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

              <Box sx={{ flex: 1 }} />
            </Stack>
          </CardContent>
        </Card>

        <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
          <Card sx={{ flex: 1, minWidth: 320 }}>
            <CardContent>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                Regions
              </Typography>
              {regionsQ.data ? (
                <TreeMultiSelect
                  leaves={regionsQ.data.leaves}
                  selected={regionSel}
                  onChange={setRegionSel}
                  placeholder="Search region…"
                />
              ) : (
                <Typography variant="body2" sx={{ opacity: 0.8 }}>
                  {regionsQ.isLoading ? "Loading…" : regionsQ.error ? String(regionsQ.error) : "—"}
                </Typography>
              )}
            </CardContent>
          </Card>

          <Card sx={{ flex: 1, minWidth: 320 }}>
            <CardContent>
              <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1 }}>
                Sectors
              </Typography>
              {sectorsQ.data ? (
                <TreeMultiSelect
                  leaves={sectorsQ.data.leaves}
                  selected={sectorSel}
                  onChange={setSectorSel}
                  placeholder="Search sector…"
                />
              ) : (
                <Typography variant="body2" sx={{ opacity: 0.8 }}>
                  {sectorsQ.isLoading ? "Loading…" : sectorsQ.error ? String(sectorsQ.error) : "—"}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Stack>
      </Stack>
    </Container>
  );
}
