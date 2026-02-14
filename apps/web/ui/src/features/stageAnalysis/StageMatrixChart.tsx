import ReactECharts from "echarts-for-react";

type ImpactRow = { key: string; unit: string; color: string; values: number[] };
export type StageTableV1 = { kind: "stage_table_v1"; stages: string[]; impacts: ImpactRow[]; relative: boolean };

export default function StageMatrixChart({
  data,
  impactLabelByKey,
  onCellClick,
}: {
  data: StageTableV1;
  impactLabelByKey: Record<string, string>;
  onCellClick?: (info: { impactKey: string; stage: string; value: number }) => void;
}) {
  const stages = data.stages;
  const impacts = data.impacts;

  const points: Array<[number, number, number, string, string]> = [];
  for (let y = 0; y < impacts.length; y++) {
    for (let x = 0; x < stages.length; x++) {
      points.push([x, y, impacts[y].values[x] ?? 0, impacts[y].key, stages[x]]);
    }
  }

  const option = {
    grid: { left: 220, right: 30, top: 20, bottom: 60 },
    xAxis: {
      type: "category",
      data: stages,
      axisLabel: { rotate: 20 },
    },
    yAxis: {
      type: "category",
      data: impacts.map((i) => impactLabelByKey[i.key] ?? i.key),
    },
    tooltip: {
      trigger: "item",
      formatter: (p: any) => {
        const [, , v, k, s] = p.data as any[];
        const label = impactLabelByKey[k] ?? k;
        const val = typeof v === "number" ? v : Number(v);
        return `${label}<br/>${s}: <b>${(val * 100).toFixed(2)}%</b>`;
      },
    },
    series: [
      {
        type: "scatter",
        data: points,
        symbolSize: (val: any[]) => {
          const v = Number(val[2] ?? 0);
          return Math.max(6, Math.min(50, 6 + Math.sqrt(Math.max(v, 0)) * 60));
        },
        itemStyle: {
          color: (p: any) => {
            const impactKey = p.data?.[3];
            const row = impacts.find((i) => i.key === impactKey);
            return row?.color || "#8ab4f8";
          },
          opacity: 0.9,
        },
      },
    ],
  };

  return (
    <ReactECharts
      option={option as any}
      style={{ height: Math.max(320, 70 + impacts.length * 32), width: "100%" }}
      onEvents={
        onCellClick
          ? {
              click: (p: any) => {
                const [, , v, k, s] = p.data as any[];
                onCellClick({ impactKey: String(k), stage: String(s), value: Number(v) });
              },
            }
          : undefined
      }
    />
  );
}

