import { useEffect, useMemo, useRef } from "react";
import { Box, Typography } from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { GeoJSON, MapContainer, useMap } from "react-leaflet";
import type { Feature, FeatureCollection, GeoJsonObject } from "geojson";
import type { Layer, PathOptions } from "leaflet";
import L from "leaflet";

export type GeoJsonV1 = { kind: "geojson_v1"; geojson: string; meta: { impact: string; relative: boolean } };
export type MapSettings = {
  palette: "Reds" | "Blues" | "Greens" | "Greys" | "Viridis";
  reverse: boolean;
  showLegend: boolean;
  title: string;
  mode: "binned" | "continuous";
  relative: boolean;
  k: number;
  customBins: string;
  normMode: "linear" | "log" | "power";
  robust: number;
  gamma: number;
};

function parse(geojson: string): FeatureCollection {
  return JSON.parse(geojson) as FeatureCollection;
}

function metricFor(props: any, settings: MapSettings): number {
  const raw =
    settings.mode === "continuous" ? props?.value : settings.relative ? props?.percentage : props?.value;
  const n = Number(raw);
  return Number.isFinite(n) ? n : NaN;
}

function parseBins(customBins: string): number[] {
  const raw = String(customBins || "")
    .split(/[,\s]+/g)
    .map((s) => s.trim())
    .filter(Boolean);
  const nums = raw.map((s) => Number(s)).filter((n) => Number.isFinite(n));
  nums.sort((a, b) => a - b);
  return Array.from(new Set(nums));
}

function quantile(sorted: number[], p: number): number {
  if (!sorted.length) return NaN;
  const pp = Math.max(0, Math.min(1, p));
  const idx = pp * (sorted.length - 1);
  const lo = Math.floor(idx);
  const hi = Math.ceil(idx);
  if (lo === hi) return sorted[lo];
  const t = idx - lo;
  return sorted[lo] * (1 - t) + sorted[hi] * t;
}

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "").trim();
  const n = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
  const r = parseInt(n.slice(0, 2), 16);
  const g = parseInt(n.slice(2, 4), 16);
  const b = parseInt(n.slice(4, 6), 16);
  return [r, g, b];
}

function rgbToHex([r, g, b]: [number, number, number]): string {
  const to = (x: number) => Math.max(0, Math.min(255, Math.round(x))).toString(16).padStart(2, "0");
  return `#${to(r)}${to(g)}${to(b)}`;
}

function lerpColor(a: string, b: string, t: number): string {
  const [ar, ag, ab] = hexToRgb(a);
  const [br, bg, bb] = hexToRgb(b);
  return rgbToHex([ar + (br - ar) * t, ag + (bg - ag) * t, ab + (bb - ab) * t] as any);
}

const PALETTES: Record<MapSettings["palette"], string[]> = {
  Reds: ["#fff5f0", "#fee0d2", "#fcbba1", "#fc9272", "#fb6a4a", "#ef3b2c", "#cb181d", "#a50f15", "#67000d"],
  Blues: ["#f7fbff", "#deebf7", "#c6dbef", "#9ecae1", "#6baed6", "#4292c6", "#2171b5", "#08519c", "#08306b"],
  Greens: ["#f7fcf5", "#e5f5e0", "#c7e9c0", "#a1d99b", "#74c476", "#41ab5d", "#238b45", "#006d2c", "#00441b"],
  Greys: ["#ffffff", "#f0f0f0", "#d9d9d9", "#bdbdbd", "#969696", "#737373", "#525252", "#252525", "#000000"],
  Viridis: ["#440154", "#482777", "#3e4989", "#31688e", "#26828e", "#1f9e89", "#35b779", "#6ece58", "#b5de2b"],
};

function sampleStops(stops: string[], k: number): string[] {
  const kk = Math.max(2, Math.min(64, Math.floor(k)));
  if (kk <= stops.length) {
    const out: string[] = [];
    for (let i = 0; i < kk; i++) {
      const t = kk === 1 ? 0 : i / (kk - 1);
      const idx = Math.round(t * (stops.length - 1));
      out.push(stops[idx]);
    }
    return out;
  }
  const out: string[] = [];
  for (let i = 0; i < kk; i++) {
    const t = kk === 1 ? 0 : i / (kk - 1);
    const f = t * (stops.length - 1);
    const lo = Math.floor(f);
    const hi = Math.min(stops.length - 1, Math.ceil(f));
    const u = f - lo;
    out.push(lo === hi ? stops[lo] : lerpColor(stops[lo], stops[hi], u));
  }
  return out;
}

function tooltipHtml(props: any): string {
  const region = String(props?.region ?? props?.exiobase ?? "—");
  const pct = Number(props?.percentage);
  const abs = Number(props?.value);
  const unit = String(props?.unit ?? "");

  const parts: string[] = [];
  parts.push(`<div style="font-weight:700; margin-bottom:2px;">${region}</div>`);
  if (Number.isFinite(pct)) parts.push(`<div>${pct.toFixed(2)}%</div>`);
  if (Number.isFinite(abs)) parts.push(`<div style="opacity:0.85;">${abs.toLocaleString()} ${unit}</div>`);
  return parts.join("");
}

function InvalidateSizeOnResize({ watchEl }: { watchEl: () => HTMLElement | null }) {
  const map = useMap();

  useEffect(() => {
    const el = watchEl();
    if (!el) return;

    const invalidate = () => {
      try {
        map.invalidateSize({ pan: false });
      } catch {
        // ignore
      }
    };

    // Initial: often needed after tab switches / flex layout changes.
    const t1 = window.setTimeout(invalidate, 0);
    const t2 = window.setTimeout(invalidate, 60);

    const ro = new ResizeObserver(() => invalidate());
    ro.observe(el);

    const onVis = () => invalidate();
    document.addEventListener("visibilitychange", onVis);

    return () => {
      window.clearTimeout(t1);
      window.clearTimeout(t2);
      ro.disconnect();
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [map, watchEl]);

  return null;
}

function FitBoundsOnData({ fc }: { fc: FeatureCollection }) {
  const map = useMap();

  useEffect(() => {
    try {
      const bounds = L.geoJSON(fc as any).getBounds();
      if (bounds && bounds.isValid()) map.fitBounds(bounds, { padding: [18, 18] });
    } catch {
      // ignore
    }
  }, [map, fc]);

  return null;
}

export default function WorldMapLeaflet({
  data,
  settings,
  onRegionClick,
}: {
  data: GeoJsonV1;
  settings: MapSettings;
  onRegionClick?: (info: { exiobase: string; region: string }) => void;
}) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const fc = useMemo(() => parse(data.geojson), [data.geojson]);
  const theme = useTheme();

  const border = theme.palette.mode === "dark" ? "rgba(255,255,255,0.28)" : "rgba(0,0,0,0.28)";
  const borderHover = theme.palette.mode === "dark" ? "rgba(255,255,255,0.55)" : "rgba(0,0,0,0.55)";
  const bg = theme.palette.mode === "dark" ? "#0b1220" : "#f6f7fb";

  const features = (fc.features ?? []) as Feature[];
  const values = useMemo(() => features.map((f) => metricFor((f.properties ?? {}) as any, settings)), [features, settings]);
  const finite = useMemo(() => values.filter((v) => Number.isFinite(v)).sort((a, b) => a - b), [values]);

  const scale = useMemo(() => {
    const palStops = PALETTES[settings.palette] ?? PALETTES.Reds;

    if (settings.mode === "binned") {
      const mn = finite.length ? finite[0] : 0;
      const mx = finite.length ? finite[finite.length - 1] : 1;
      const k = Math.max(2, Math.min(20, Math.floor(settings.k || 7)));
      const custom = parseBins(settings.customBins);
      const edges = custom.length
        ? [mn, ...custom.filter((x) => x > mn && x < mx), mx]
        : Array.from({ length: k + 1 }, (_, i) => mn + (i / k) * (mx - mn));
      const colors = sampleStops(palStops, edges.length - 1);
      const cols = settings.reverse ? colors.slice().reverse() : colors;

      const toColor = (v: number) => {
        if (!Number.isFinite(v)) return "rgba(0,0,0,0)";
        for (let i = 0; i < edges.length - 1; i++) {
          if (v <= edges[i + 1] || i === edges.length - 2) return cols[i];
        }
        return cols[cols.length - 1];
      };

      return { kind: "binned" as const, edges, colors: cols, toColor, mn, mx };
    }

    const loP = Math.max(0, Math.min(49, Number(settings.robust) || 0));
    const hiP = 100 - loP;
    let vmin = quantile(finite, loP / 100);
    let vmax = quantile(finite, hiP / 100);
    if (!Number.isFinite(vmin) || !Number.isFinite(vmax) || vmin === vmax) {
      vmin = finite.length ? finite[0] : 0;
      vmax = finite.length ? finite[finite.length - 1] : 1;
      if (vmin === vmax) vmax = vmin + 1;
    }

    const stops = sampleStops(palStops, 9);
    const cols = settings.reverse ? stops.slice().reverse() : stops;

    const colorAt = (t: number) => {
      const tt = Math.max(0, Math.min(1, t));
      const f = tt * (cols.length - 1);
      const lo = Math.floor(f);
      const hi = Math.min(cols.length - 1, Math.ceil(f));
      const u = f - lo;
      return lo === hi ? cols[lo] : lerpColor(cols[lo], cols[hi], u);
    };

    const eps = 1e-12;
    const norm = (v: number) => {
      if (!Number.isFinite(v)) return NaN;
      const vv = Math.max(vmin, Math.min(vmax, v));
      if (settings.normMode === "log") {
        const a = Math.log(Math.max(vmin, eps));
        const b = Math.log(Math.max(vmax, eps));
        const x = Math.log(Math.max(vv, eps));
        return (x - a) / (b - a);
      }
      const t = (vv - vmin) / (vmax - vmin);
      if (settings.normMode === "power") return Math.pow(Math.max(0, Math.min(1, t)), Number(settings.gamma) || 0.7);
      return t;
    };

    const toColor = (v: number) => colorAt(norm(v));
    return { kind: "continuous" as const, vmin, vmax, toColor, colors: cols };
  }, [finite, settings]);

  const styleFor = (feature?: Feature): PathOptions => {
    const props: any = (feature ?? ({} as Feature)).properties || {};
    const v = metricFor(props, settings);
    return { color: border, weight: 1, fillColor: scale.toColor(v), fillOpacity: 0.82 };
  };

  return (
    <Box ref={containerRef} sx={{ position: "relative", height: "100%" }}>
      <MapContainer
        style={{ height: "100%", width: "100%", background: bg, borderRadius: 14, minHeight: 520 }}
        center={[20, 0]}
        zoom={1.3}
        scrollWheelZoom
      >
        <InvalidateSizeOnResize watchEl={() => containerRef.current} />
        <FitBoundsOnData fc={fc} />
        <GeoJSON
          data={fc as unknown as GeoJsonObject}
          style={styleFor}
          onEachFeature={(feature: Feature, layer: Layer) => {
            const props: any = feature.properties || {};
            const label = String(props.region || props.exiobase || "—");
            const exiobase = String(props.exiobase || "");
            const base = styleFor(feature);

            (layer as any).bindTooltip(tooltipHtml(props), { sticky: true, opacity: 0.95, direction: "auto" });

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

      {settings.title ? (
        <Box sx={{ position: "absolute", left: 16, top: 12, pointerEvents: "none" }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 800, opacity: 0.92 }}>
            {settings.title}
          </Typography>
        </Box>
      ) : null}

      {settings.showLegend ? (
        <Box
          sx={{
            position: "absolute",
            right: 14,
            top: 12,
            p: 1.2,
            borderRadius: 2,
            background: theme.palette.mode === "dark" ? "rgba(15,23,42,0.92)" : "rgba(255,255,255,0.92)",
            border: theme.palette.mode === "dark" ? "1px solid rgba(255,255,255,0.14)" : "1px solid rgba(0,0,0,0.12)",
            minWidth: 180,
            pointerEvents: "none",
          }}
        >
          <Typography variant="caption" sx={{ display: "block", opacity: 0.85, mb: 0.75 }}>
            Legend
          </Typography>
          {scale.kind === "binned" ? (
            <Box sx={{ display: "grid", gap: 0.5 }}>
              {scale.colors.map((c, i) => {
                const lo = scale.edges[i];
                const hi = scale.edges[i + 1];
                return (
                  <Box key={i} sx={{ display: "grid", gridTemplateColumns: "14px 1fr", gap: 1, alignItems: "center" }}>
                    <Box sx={{ width: 14, height: 10, borderRadius: 0.5, background: c }} />
                    <Typography variant="caption" sx={{ opacity: 0.85 }}>
                      {lo.toFixed(2)} – {hi.toFixed(2)}
                    </Typography>
                  </Box>
                );
              })}
            </Box>
          ) : (
            <Box sx={{ display: "grid", gap: 0.75 }}>
              <Box sx={{ height: 10, borderRadius: 1, background: `linear-gradient(90deg, ${scale.colors.join(",")})` }} />
              <Box sx={{ display: "flex", justifyContent: "space-between" }}>
                <Typography variant="caption" sx={{ opacity: 0.85 }}>
                  {scale.vmin.toFixed(2)}
                </Typography>
                <Typography variant="caption" sx={{ opacity: 0.85 }}>
                  {scale.vmax.toFixed(2)}
                </Typography>
              </Box>
            </Box>
          )}
        </Box>
      ) : null}
    </Box>
  );
}
