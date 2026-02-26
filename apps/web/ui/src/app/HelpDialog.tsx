import { Box, Dialog, DialogContent, DialogTitle, Divider, Stack, Typography } from "@mui/material";
import { useT } from "./i18n";

export default function HelpDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useT();

  const Section = ({ titleKey, bodyKey }: { titleKey: string; bodyKey: string }) => (
    <Box>
      <Typography variant="subtitle1" sx={{ fontWeight: 800, mb: 0.5 }}>
        {t(titleKey)}
      </Typography>
      <Typography variant="body2" sx={{ opacity: 0.9, whiteSpace: "pre-line" }}>
        {t(bodyKey)}
      </Typography>
    </Box>
  );

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>
        <Stack spacing={0.25}>
          <Typography variant="h6" sx={{ fontWeight: 900 }}>
            {t("Help.Title")}
          </Typography>
          <Typography variant="body2" sx={{ opacity: 0.8 }}>
            {t("Help.Subtitle")}
          </Typography>
        </Stack>
      </DialogTitle>
      <DialogContent>
        <Stack spacing={2.25} sx={{ pb: 1 }}>
          <Section titleKey="Help.Intro.Title" bodyKey="Help.Intro.Body" />
          <Divider />
          <Section titleKey="Help.Selection.Title" bodyKey="Help.Selection.Body" />
          <Section titleKey="Help.Visualisation.Title" bodyKey="Help.Visualisation.Body" />
          <Section titleKey="Help.Map.Title" bodyKey="Help.Map.Body" />
          <Section titleKey="Help.Contrib.Title" bodyKey="Help.Contrib.Body" />
          <Divider />
          <Section titleKey="Help.Tips.Title" bodyKey="Help.Tips.Body" />
        </Stack>
      </DialogContent>
    </Dialog>
  );
}

