export type StageMethod = {
  id: string;
  label: string;
  analysisType: string;
};

export const stageMethods: StageMethod[] = [
  { id: "bubble", label: "Bubble diagram", analysisType: "stage_bubble" },
];

