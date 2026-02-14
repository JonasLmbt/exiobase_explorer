import { useMutation, useQuery } from "@tanstack/react-query";
import { Button, Card, CardContent, Container, Stack, Typography } from "@mui/material";
import { api } from "../api";
import { useAppState } from "../app/state";
import { useLog } from "../app/log";
import TreeMultiSelect from "../components/TreeMultiSelect";

export default function SelectionTab() {
  const { year, language, pendingSelection, setPendingSelection, setSelection, selectionSummary, setSelectionSummary } =
    useAppState();
  const log = useLog();

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

  const regionSel = pendingSelection.mode === "regions_sectors" ? pendingSelection.regions : [];
  const sectorSel = pendingSelection.mode === "regions_sectors" ? pendingSelection.sectors : [];

  const setRegionSel = (regions: number[]) => {
    const sectors = sectorSel;
    if (regions.length === 0 && sectors.length === 0) return setPendingSelection({ mode: "all" });
    setPendingSelection({ mode: "regions_sectors", regions, sectors });
  };
  const setSectorSel = (sectors: number[]) => {
    const regions = regionSel;
    if (regions.length === 0 && sectors.length === 0) return setPendingSelection({ mode: "all" });
    setPendingSelection({ mode: "regions_sectors", regions, sectors });
  };

  const summaryM = useMutation({
    mutationFn: () =>
      api.selectionSummary({
        year,
        language,
        selection:
          pendingSelection.mode === "all"
            ? { mode: "all", regions: [], sectors: [], indices: [] }
            : pendingSelection.mode === "indices"
              ? { mode: "indices", regions: [], sectors: [], indices: pendingSelection.indices }
              : { mode: "regions_sectors", regions: pendingSelection.regions, sectors: pendingSelection.sectors, indices: [] },
      }),
    onSuccess: (data) => {
      setSelectionSummary(data);
      log.info(`Selection applied: ${data.supplychain_repr}`);
    },
    onError: (e) => log.error(`Selection apply failed: ${String(e)}`),
  });

  const apply = () => {
    setSelection(pendingSelection);
    summaryM.mutate();
  };

  return (
    <Container sx={{ py: 3 }}>
      <Stack spacing={2}>
        <Card>
          <CardContent>
            <Typography variant="subtitle1" sx={{ fontWeight: 700, mb: 1 }}>
              Selection
            </Typography>
            <Typography variant="body2" sx={{ opacity: 0.8 }}>
              Year/Language kommen aus <b>Settings</b>. Aktuell: {year} / {language}
            </Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
              <Button variant="contained" onClick={apply} disabled={summaryM.isPending}>
                Apply selection
              </Button>
              <Button
                variant="outlined"
                onClick={() => setPendingSelection({ mode: "all" })}
                disabled={pendingSelection.mode === "all"}
              >
                Clear pending
              </Button>
            </Stack>
            {selectionSummary ? (
              <Typography variant="body2" sx={{ mt: 1, opacity: 0.85, fontFamily: "ui-monospace, Menlo, Consolas, monospace" }}>
                {selectionSummary.supplychain_repr}
              </Typography>
            ) : null}
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
                  placeholder="Search region..."
                />
              ) : (
                <Typography variant="body2" sx={{ opacity: 0.8 }}>
                  {regionsQ.isLoading ? "Loading..." : regionsQ.error ? String(regionsQ.error) : "—"}
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
                  placeholder="Search sector..."
                />
              ) : (
                <Typography variant="body2" sx={{ opacity: 0.8 }}>
                  {sectorsQ.isLoading ? "Loading..." : sectorsQ.error ? String(sectorsQ.error) : "—"}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Stack>
      </Stack>
    </Container>
  );
}
