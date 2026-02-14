import { Card, CardContent, Container, Stack } from "@mui/material";
import LogConsole from "../components/LogConsole";

export default function ConsoleTab() {
  return (
    <Container sx={{ py: 3 }}>
      <Stack spacing={2}>
        <Card>
          <CardContent>
            <LogConsole title="Console output" />
          </CardContent>
        </Card>
      </Stack>
    </Container>
  );
}
