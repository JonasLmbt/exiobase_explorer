import ReactECharts from "echarts-for-react";
import type { EChartsType } from "echarts";
import { useTheme } from "@mui/material/styles";
import { useEffect, useMemo, useRef } from "react";

type ImpactRow = { key: string; unit: string; color: string; relative: number[]; absolute: number[] };
export type StageTableV1 = { kind: "stage_table_v1"; stage_ids?: string[]; stages: string[]; impacts: ImpactRow[] };

function wrapLabel(value: string, maxLen = 14): string {
  const parts = String(value ?? "").split(/\s+/).filter(Boolean);
  if (parts.length <= 1) return String(value ?? "");
  const lines: string[] = [];
  let cur = "";
  for (const p of parts) {
    const next = cur ? `${cur} ${p}` : p;
    if (next.length > maxLen && cur) {
      lines.push(cur);
      cur = p;
    } else {
      cur = next;
    }
  }
  if (cur) lines.push(cur);
  return lines.join("\n");
}

export default function StageMatrixChart({
  data,
  impactLabelByKey,
  showStagePercentLabels,
  showTotalAbsoluteLabel,
  onCellClick,
}: {
  data: StageTableV1;
  impactLabelByKey: Record<string, string>;
  showStagePercentLabels?: boolean;
  showTotalAbsoluteLabel?: boolean;
  onCellClick?: (info: { impactKey: string; stageId: string; stageLabel: string; value: number }) => void;
}) {
  const stages = data.stages;
  const stageIds = data.stage_ids ?? stages.map((_, i) => String(i));
  const impacts = data.impacts;
  const theme = useTheme();

  const showLabels = Boolean(showStagePercentLabels || showTotalAbsoluteLabel);
  const rowHeight = showLabels ? 90 : 64;

  const axisTextColor = theme.palette.mode === "dark" ? "rgba(255,255,255,0.72)" : "rgba(0,0,0,0.72)";
  const axisLineColor = theme.palette.mode === "dark" ? "rgba(255,255,255,0.35)" : "rgba(0,0,0,0.35)";
  const chartRef = useRef<EChartsType | null>(null);

  // Use category strings (not indices) for better compatibility with ECharts category axes.
  const points: Array<{ value: [string, string, number, number, string, string, string] }> = [];
  for (let y = 0; y < impacts.length; y++) {
    const yLabel = impactLabelByKey[impacts[y].key] ?? impacts[y].key;
    for (let x = 0; x < stages.length; x++) {
      points.push({
        value: [
          stages[x],
          yLabel,
          impacts[y].relative[x] ?? 0,
          impacts[y].absolute[x] ?? 0,
          impacts[y].key,
          stages[x],
          stageIds[x] ?? String(x),
        ],
      });
    }
  }

  const option = useMemo(
    () => ({
    grid: { left: 220, right: 30, top: 20, bottom: showLabels ? 110 : 90 },
    animation: false,
    xAxis: {
      type: "category",
      data: stages,
      axisLabel: {
        rotate: 0,
        interval: 0,
        lineHeight: 14,
        color: axisTextColor,
        formatter: (v: string) => wrapLabel(v, 18),
      },
      axisLine: { lineStyle: { color: axisLineColor } },
      axisTick: { lineStyle: { color: axisLineColor } },
    },
    yAxis: {
      type: "category",
      data: impacts.map((i) => impactLabelByKey[i.key] ?? i.key),
      axisLabel: { color: axisTextColor },
      axisLine: { lineStyle: { color: axisLineColor } },
      axisTick: { lineStyle: { color: axisLineColor } },
    },
    tooltip: {
      trigger: "item",
      triggerOn: "mousemove|click",
      showDelay: 0,
      hideDelay: 50,
      confine: true,
      transitionDuration: 0,
      formatter: (p: any) => {
        const v = (p?.data?.value ?? p?.value ?? []) as any[];
        const [, , vRel, vAbs, k, s] = v;
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
        dimensions: ["x", "y", "rel", "abs", "impactKey", "stageLabel", "stageId"],
        encode: { x: "x", y: "y" },
        data: points,
        progressive: 0,
        animation: false,
        labelLayout: { hideOverlap: true },
        label: {
          show: showLabels,
          position: "bottom",
          distance: 6,
          fontSize: 11,
          color: axisTextColor,
          formatter: (p: any) => {
            const arr = (p?.data?.value ?? p?.value ?? []) as any[];
            const rel = Number(arr?.[2] ?? 0);
            const abs = Number(arr?.[3] ?? 0);
            const impactKey = String(arr?.[4] ?? "");
            const stageId = String(arr?.[6] ?? "");

            if (stageId === "total") {
              if (!showTotalAbsoluteLabel || !Number.isFinite(abs) || abs === 0) return "";
              const unit = impacts.find((i) => i.key === impactKey)?.unit ?? "";
              return unit ? `${abs.toLocaleString()} ${unit}` : abs.toLocaleString();
            }

            if (!showStagePercentLabels || !Number.isFinite(rel) || rel === 0) return "";
            return `${(rel * 100).toFixed(1)}%`;
          },
        },
        symbolSize: (val: any, params: any) => {
          const arr = (Array.isArray(val) ? val : (params?.data?.value ?? [])) as any[];
          const v = Number(arr?.[2] ?? 0);
          // Scale bubbles based on available row height to avoid overlapping for many impacts.
          const maxBubble = Math.max(18, Math.min(56, rowHeight * 0.85));
          return Math.max(6, Math.min(maxBubble, 6 + Math.sqrt(Math.max(v, 0)) * maxBubble));
        },
        itemStyle: {
          color: (p: any) => {
            const impactKey = p.data?.value?.[4];
            const row = impacts.find((i) => i.key === impactKey);
            return row?.color || "#8ab4f8";
          },
          opacity: 0.9,
        },
      },
    ],
  }),
    [axisLineColor, axisTextColor, impactLabelByKey, impacts, rowHeight, showLabels, showStagePercentLabels, showTotalAbsoluteLabel, stageIds, stages],
  );

  useEffect(() => {
    // Ensure tooltip appears on "resting hover" by explicitly showing it on mouseover events.
    const chart = chartRef.current;
    if (!chart) return;
    const onOver = (p: any) => {
      if (!p || p.componentType !== "series") return;
      if (typeof p.dataIndex !== "number") return;
      chart.dispatchAction({ type: "showTip", seriesIndex: p.seriesIndex, dataIndex: p.dataIndex });
    };
    chart.on("mouseover", onOver);
    return () => {
      try {
        chart.off("mouseover", onOver);
      } catch {
        // ignore
      }
    };
  }, [option]);

  return (
    <ReactECharts
      option={option as any}
      notMerge
      lazyUpdate={false}
      opts={{ renderer: "canvas" }}
      // Ensure enough vertical spacing per impact row for multi-impact selections.
      style={{ height: Math.max(360, 160 + impacts.length * rowHeight), width: "100%" }}
      onChartReady={(chart) => {
        chartRef.current = chart as unknown as EChartsType;
        chart.resize();
      }}
      onEvents={
        onCellClick
          ? {
              click: (p: any) => {
                const arr = (p?.data?.value ?? p?.value ?? []) as any[];
                const [, , v, , k, sLabel, sId] = arr;
                onCellClick({
                  impactKey: String(k),
                  stageId: String(sId),
                  stageLabel: String(sLabel),
                  value: Number(v),
                });
              },
            }
          : undefined
      }
    />
  );
}
