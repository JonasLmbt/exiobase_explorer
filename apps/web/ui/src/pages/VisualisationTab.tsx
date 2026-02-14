import { useState } from "react";
import { Box, Container, Tab, Tabs } from "@mui/material";
import StageAnalysisTab from "../features/stageAnalysis/StageAnalysisTab";
import RegionAnalysisTab from "../features/regionAnalysis/RegionAnalysisTab";

type Inner = "stage" | "region";

export default function VisualisationTab() {
  const [inner, setInner] = useState<Inner>("stage");

  return (
    <Container sx={{ py: 3 }}>
      <Tabs value={inner} onChange={(_, v) => setInner(v)} textColor="inherit" indicatorColor="secondary">
        <Tab value="stage" label="Stage analysis" />
        <Tab value="region" label="Region analysis" />
      </Tabs>
      <Box sx={{ pt: 2 }}>
        {inner === "stage" ? <StageAnalysisTab /> : <RegionAnalysisTab />}
      </Box>
    </Container>
  );
}
