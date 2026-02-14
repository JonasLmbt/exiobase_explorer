export type RegionMethod = {
  id: string;
  label: string;
  analysisType: string;
  maxImpacts: number;
  defaultParams?: Record<string, unknown>;
};

export const regionMethods: RegionMethod[] = [
  { id: "world_map", label: "World map", analysisType: "region_world_map", maxImpacts: 1 },
  { id: "topn", label: "Top n", analysisType: "region_topn", maxImpacts: 4, defaultParams: { n: 10 } },
  { id: "flopn", label: "Flop n", analysisType: "region_flopn", maxImpacts: 4, defaultParams: { n: 10 } },
  { id: "pie", label: "Pie chart", analysisType: "region_pie", maxImpacts: 1 },
];

