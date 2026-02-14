import { GeoJSON, MapContainer, TileLayer } from "react-leaflet";
import type { Feature, FeatureCollection, GeoJsonObject } from "geojson";
import type { Layer, PathOptions } from "leaflet";

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

export default function WorldMapLeaflet({ data }: { data: GeoJsonV1 }) {
  const fc = parse(data.geojson);

  return (
    <MapContainer style={{ height: 520, width: "100%" }} center={[20, 0]} zoom={1.3} scrollWheelZoom>
      <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <GeoJSON
        data={fc as unknown as GeoJsonObject}
        style={(feature?: Feature): PathOptions => {
          const v = getValue((feature ?? ({} as Feature)) as Feature);
          return {
            color: "rgba(255,255,255,0.25)",
            weight: 1,
            fillColor: colorFor(v),
            fillOpacity: 0.75,
          };
        }}
        onEachFeature={(feature: Feature, layer: Layer) => {
          const props: any = feature.properties || {};
          const label = props.region || props.exiobase || "—";
          const value = props.percentage ?? props.value ?? "—";
          const unit = props.unit ?? (props.percentage != null ? "%" : "");
          layer.bindPopup(`${label}<br/><b>${value}</b> ${unit}`);
        }}
      />
    </MapContainer>
  );
}
