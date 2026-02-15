import ReactECharts from "echarts-for-react";

type ImpactRow = { key: string; unit: string; color: string; relative: number[]; absolute: number[] };
export type StageTableV1 = { kind: "stage_table_v1"; stages: string[]; impacts: ImpactRow[] };

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

  const points: Array<[number, number, number, number, string, string]> = [];
  for (let y = 0; y < impacts.length; y++) {
    for (let x = 0; x < stages.length; x++) {
      points.push([
        x,
        y,
        impacts[y].relative[x] ?? 0,
        impacts[y].absolute[x] ?? 0,
        impacts[y].key,
        stages[x],
      ]);
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
        const [, , vRel, vAbs, k, s] = p.data as any[];
        const label = impactLabelByKey[k] ?? k;
        const rel = typeof vRel === "number" ? vRel : Number(vRel);
        const abs = typeof vAbs === "number" ? vAbs : Number(vAbs);
        const row = impacts.find((i) => i.key === k);
        const unit = row?.unit ? ` ${row.unit}` : "";
        return `${label}<br/>${s}: <b>${(rel * 100).toFixed(2)}%</b><br/>abs: <b>${abs.toLocaleString()}</b>${unit}`;
      },
    },
    series: [
      {
        type: "scatter",
        data: points,
        symbolSize: (val: any[]) => {
          const v = Number(val[2] ?? 0);
          // Scale bubbles based on available row height to avoid overlapping for many impacts.
          const rowHeight = 64;
          const maxBubble = Math.max(18, Math.min(56, rowHeight * 0.85));
          return Math.max(6, Math.min(maxBubble, 6 + Math.sqrt(Math.max(v, 0)) * maxBubble));
        },
        itemStyle: {
          color: (p: any) => {
            const impactKey = p.data?.[4];
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
      // Ensure enough vertical spacing per impact row for multi-impact selections.
      style={{ height: Math.max(360, 160 + impacts.length * 64), width: "100%" }}
      onEvents={
        onCellClick
          ? {
              click: (p: any) => {
                const [, , v, , k, s] = p.data as any[];
                onCellClick({ impactKey: String(k), stage: String(s), value: Number(v) });
              },
            }
          : undefined
      }
    />
  );
}
