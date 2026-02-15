import { createTheme } from "@mui/material/styles";

export function createAppTheme(mode: "dark" | "light") {
  const dark = mode === "dark";

  return createTheme({
    palette: {
      mode,
      background: dark
        ? { default: "#0b1220", paper: "rgba(255, 255, 255, 0.04)" }
        : { default: "#f6f7fb", paper: "#ffffff" },
    },
    shape: {
      borderRadius: 14,
    },
    components: {
      MuiCard: {
        styleOverrides: {
          root: {
            border: dark ? "1px solid rgba(255,255,255,0.08)" : "1px solid rgba(0,0,0,0.08)",
            backgroundImage: "none",
          },
        },
      },
    },
  });
}

