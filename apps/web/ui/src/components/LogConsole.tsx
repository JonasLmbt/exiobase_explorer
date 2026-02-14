import { Box, Button, Stack, TextField, Typography } from "@mui/material";
import { useLog } from "../app/log";

export default function LogConsole({ title }: { title: string }) {
  const log = useLog();
  return (
    <Box>
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
          {title}
        </Typography>
        <Button size="small" variant="outlined" onClick={log.clear}>
          Clear
        </Button>
      </Stack>
      <TextField
        multiline
        minRows={12}
        fullWidth
        value={log.lines
          .map((l) => {
            const ts = new Date(l.ts).toLocaleTimeString();
            return `${ts} [${l.level}] ${l.message}`;
          })
          .join("\n")}
        InputProps={{ readOnly: true }}
      />
    </Box>
  );
}

