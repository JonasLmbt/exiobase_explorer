import { GeoJSON, MapContainer } from "react-leaflet";
import type { Feature, FeatureCollection, GeoJsonObject } from "geojson";
import type { Layer, PathOptions } from "leaflet";
import { useTheme } from "@mui/material/styles";

export type GeoJsonV1 = { kind: "geojson_v1"; geojson: string; meta: { impact: string; relative: boolean } };

function parse(geojson: string): FeatureCollection {
  return JSON.parse(geojson) as FeatureCollection;
}

function getValue(f: Feature): number {
  const props: any = f.properties || {};
  const v = props.percentage ?? props.value;
  const n = Number(v);
  return Number.isFinite(n) ? n : 0;
}

function colorFor(v: number): string {
  // v is share in % in current backend (world df uses percentage + value). For relative maps we use percentage.
  // simple ramp
  if (v > 20) return "#0b4f6c";
  if (v > 10) return "#145c9e";
  if (v > 5) return "#2a7ab0";
  if (v > 2) return "#4aa3c5";
  if (v > 1) return "#7cc6d6";
  return "#b7e3ea";
}

function tooltipHtml(props: any): string {
  const region = String(props?.region ?? props?.exiobase ?? "—");
  const pctRaw = props?.percentage;
  const absRaw = props?.value;
  const unit = String(props?.unit ?? "");
  const pct = Number(pctRaw);
  const abs = Number(absRaw);

  const parts: string[] = [];
  parts.push(`<div style="font-weight:700; margin-bottom:2px;">${region}</div>`);
  if (Number.isFinite(pct)) parts.push(`<div>${pct.toFixed(2)}%</div>`);
  if (Number.isFinite(abs)) parts.push(`<div style="opacity:0.85;">${abs.toLocaleString()} ${unit}</div>`);
  return parts.join("");
}

export default function WorldMapLeaflet({
  data,
  onRegionClick,
}: {
  data: GeoJsonV1;
  onRegionClick?: (info: { exiobase: string; region: string }) => void;
}) {
  const fc = parse(data.geojson);
  const theme = useTheme();

  const border = theme.palette.mode === "dark" ? "rgba(255,255,255,0.28)" : "rgba(0,0,0,0.28)";
  const borderHover = theme.palette.mode === "dark" ? "rgba(255,255,255,0.55)" : "rgba(0,0,0,0.55)";
  const bg = theme.palette.mode === "dark" ? "#0b1220" : "#f6f7fb";

  const styleFor = (feature?: Feature): PathOptions => {
    const v = getValue((feature ?? ({} as Feature)) as Feature);
    return {
      color: border,
      weight: 1,
      fillColor: colorFor(v),
      fillOpacity: 0.82,
    };
  };

  return (
    <MapContainer
      style={{ height: 520, width: "100%", background: bg, borderRadius: 14 }}
      center={[20, 0]}
      zoom={1.3}
      scrollWheelZoom
    >
      <GeoJSON
        data={fc as unknown as GeoJsonObject}
        style={styleFor}
        onEachFeature={(feature: Feature, layer: Layer) => {
          const props: any = feature.properties || {};
          const label = String(props.region || props.exiobase || "—");
          const exiobase = String(props.exiobase || "");
          const base = styleFor(feature);

          (layer as any).bindTooltip(tooltipHtml(props), {
            sticky: true,
            opacity: 0.95,
            direction: "auto",
          });

          (layer as any).on("mouseover", () => {
            try {
              (layer as any).setStyle({ ...base, weight: 2.5, color: borderHover, fillOpacity: 0.9 });
              if ((layer as any).bringToFront) (layer as any).bringToFront();
            } catch {
              // ignore
            }
          });
          (layer as any).on("mouseout", () => {
            try {
              (layer as any).setStyle(base);
            } catch {
              // ignore
            }
          });

          (layer as any).on("click", () => {
            if (!onRegionClick) return;
            onRegionClick({ exiobase, region: label });
          });
        }}
      />
    </MapContainer>
  );
}

