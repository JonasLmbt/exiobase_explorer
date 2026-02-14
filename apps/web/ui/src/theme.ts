import { createTheme } from "@mui/material/styles";

export const theme = createTheme({
  palette: {
    mode: "dark",
    background: {
      default: "#0b1220",
      paper: "rgba(255, 255, 255, 0.04)",
    },
  },
  shape: {
    borderRadius: 14,
  },
});

