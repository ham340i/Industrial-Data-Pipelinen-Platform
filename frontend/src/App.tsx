import { useEffect, useRef } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  CssBaseline,
  Divider,
  Paper,
  Stack,
  TextField,
  ThemeProvider,
  Typography,
  createTheme,
} from "@mui/material";
import { Link, NavLink, Route, Routes, useLocation } from "react-router-dom";
import { useHealth } from "./api/health";
import { useEditorStore } from "./state/editor";

const theme = createTheme({
  palette: {
    primary: { main: "#12675c" },
    background: { default: "#f5f7f6", paper: "#ffffff" },
    text: { primary: "#163238", secondary: "#52666a" },
  },
  typography: {
    fontFamily: "Inter, ui-sans-serif, system-ui, -apple-system, sans-serif",
    h1: { fontSize: "2.4rem", fontWeight: 700, letterSpacing: "-0.04em" },
    h2: { fontSize: "1.2rem", fontWeight: 650 },
    button: { textTransform: "none", fontWeight: 600 },
  },
  shape: { borderRadius: 12 },
  components: { MuiButton: { defaultProps: { disableElevation: true } } },
});

function HealthStatus() {
  const health = useHealth();
  let feedback = <Alert severity="success">Local API is connected.</Alert>;
  if (health.isPending) {
    feedback = (
      <Stack direction="row" role="status" sx={{ gap: 1.5 }}>
        <CircularProgress size={20} aria-label="Checking API" />
        <Typography>Checking the local API…</Typography>
      </Stack>
    );
  } else if (health.isError) {
    feedback = (
      <Alert
        severity="warning"
        action={
          <Button
            color="inherit"
            onClick={() => void health.refetch()}
            disabled={health.isFetching}
          >
            Retry
          </Button>
        }
      >
        {health.error.message}
      </Alert>
    );
  }
  return (
    <Paper variant="outlined" sx={{ p: 3 }}>
      <Stack
        direction="row"
        sx={{
          justifyContent: "space-between",
          alignItems: "center",
          gap: 2,
          mb: 2,
        }}
      >
        <Typography component="h2" variant="h2">
          Local API connection
        </Typography>
        <Chip size="small" variant="outlined" label="Live check" />
      </Stack>
      {feedback}
      <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
        The workbench can open while the API is offline. Project storage and
        pipeline execution require the backend.
      </Typography>
    </Paper>
  );
}

function Overview() {
  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="overline" color="primary">
          YOUR LOCAL WORKSPACE
        </Typography>
        <Typography variant="h1" component="h1" sx={{ mt: 1 }}>
          A clear path from data to insight.
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 2, maxWidth: 620 }}>
          Bring your pipeline work together in one place. Start with the
          workbench, then connect the tools that turn raw data into useful
          results.
        </Typography>
      </Box>
      <Paper
        variant="outlined"
        sx={{ p: { xs: 3, md: 4 }, background: "#e9f2ee" }}
      >
        <Chip label="Iteration 1 · Foundation" size="small" sx={{ mb: 3 }} />
        <Typography component="h2" variant="h2">
          Your workspace starts here
        </Typography>
        <Typography color="text.secondary" sx={{ my: 2 }}>
          Explore the project workspace and prepare a draft name for your next
          pipeline. Saving projects and editing graphs arrive in later
          iterations.
        </Typography>
        <Button component={Link} to="/projects" variant="contained">
          Explore projects →
        </Button>
      </Paper>
      <HealthStatus />
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
          gap: 2,
        }}
      >
        {[
          [
            "01",
            "Organize your work",
            "A dedicated space for projects and pipeline definitions.",
          ],
          [
            "02",
            "Build with clarity",
            "A reserved builder workspace for the upcoming visual editor.",
          ],
        ].map(([number, title, description]) => (
          <Paper key={number} variant="outlined" sx={{ p: 3 }}>
            <Typography variant="overline" color="primary">
              {number}
            </Typography>
            <Typography component="h2" variant="h2" sx={{ mt: 1 }}>
              {title}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              {description}
            </Typography>
          </Paper>
        ))}
      </Box>
    </Stack>
  );
}

function Projects() {
  return (
    <Stack spacing={3}>
      <Box>
        <Typography component="h1" variant="h1">
          Projects
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>
          A home for your pipeline work.
        </Typography>
      </Box>
      <Paper
        variant="outlined"
        sx={{ p: { xs: 3, md: 6 }, textAlign: "center" }}
      >
        <Typography component="h2" variant="h2">
          Project storage is coming next
        </Typography>
        <Typography color="text.secondary" sx={{ my: 2 }}>
          This foundation does not load or save projects yet. You can explore
          the builder workspace and prepare an unsaved draft.
        </Typography>
        <Button component={Link} to="/builder" variant="contained">
          Open builder workspace
        </Button>
      </Paper>
    </Stack>
  );
}

function Builder() {
  const draftName = useEditorStore((state) => state.draftName);
  const setDraftName = useEditorStore((state) => state.setDraftName);
  const reset = useEditorStore((state) => state.reset);
  return (
    <Stack spacing={3}>
      <Box>
        <Typography component="h1" variant="h1">
          Pipeline builder
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>
          Prepare your workspace.
        </Typography>
      </Box>
      <Alert severity="info">
        The visual graph editor is planned for a later iteration. This draft
        stays in this tab and is lost when you refresh.
      </Alert>
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Stack spacing={3} sx={{ alignItems: "flex-start" }}>
          <TextField
            label="Draft pipeline name"
            value={draftName}
            onChange={(event) => setDraftName(event.target.value)}
            fullWidth
            helperText="Unsaved draft · up to 120 characters"
            slotProps={{ htmlInput: { maxLength: 120 } }}
          />
          <Button variant="outlined" onClick={reset} disabled={!draftName}>
            Clear draft
          </Button>
        </Stack>
      </Paper>
      <Paper
        variant="outlined"
        sx={{ p: 6, textAlign: "center", borderStyle: "dashed" }}
      >
        <Typography component="h2" variant="h2">
          Your future canvas
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>
          Nodes, connections and validation will appear here when the graph
          editor is available.
        </Typography>
      </Paper>
    </Stack>
  );
}

export function App() {
  const { pathname } = useLocation();
  const main = useRef<HTMLElement>(null);
  const previousPath = useRef(pathname);
  useEffect(() => {
    const title =
      (
        {
          "/": "Overview",
          "/projects": "Projects",
          "/builder": "Pipeline builder",
        } as Record<string, string>
      )[pathname] ?? "Page not found";
    document.title = `${title} | Local Pipeline Studio`;
    if (previousPath.current !== pathname) main.current?.focus();
    previousPath.current = pathname;
  }, [pathname]);
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box
        component="a"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault();
          main.current?.focus();
        }}
        sx={{
          position: "fixed",
          top: 8,
          left: 8,
          zIndex: 10,
          p: 2,
          bgcolor: "white",
          clipPath: "inset(50%)",
          width: 1,
          height: 1,
          overflow: "hidden",
          whiteSpace: "nowrap",
          "&:focus": {
            clipPath: "none",
            width: "auto",
            height: "auto",
            overflow: "visible",
          },
        }}
      >
        Skip to main content
      </Box>
      <Box
        sx={{
          display: { md: "grid" },
          gridTemplateColumns: "248px minmax(0, 1fr)",
          minHeight: "100vh",
        }}
      >
        <Box
          component="aside"
          sx={{
            bgcolor: "#102d32",
            color: "#f1f7f6",
            p: 3,
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Typography sx={{ fontWeight: 700, fontSize: 20 }}>
            ◈ Local Pipeline
          </Typography>
          <Typography
            variant="caption"
            sx={{ color: "#b7cdca", letterSpacing: "0.18em", mb: 5 }}
          >
            STUDIO
          </Typography>
          <Typography variant="overline" sx={{ color: "#b7cdca", mb: 1 }}>
            WORKSPACE
          </Typography>
          <Stack
            component="nav"
            aria-label="Main navigation"
            spacing={1}
            direction={{ xs: "row", md: "column" }}
            sx={{ flexWrap: "wrap" }}
          >
            {[
              ["/", "Overview"],
              ["/projects", "Projects"],
              ["/builder", "Builder"],
            ].map(([to, label]) => (
              <Button
                key={to}
                component={NavLink}
                to={to}
                end
                sx={{
                  color: "#d6e4e2",
                  justifyContent: "flex-start",
                  px: 2,
                  py: 1.4,
                  "&.active": { bgcolor: "#285047", color: "#fff" },
                  "&:hover": { bgcolor: "#20434a" },
                  "&:focus-visible": {
                    outline: "2px solid #b5e9da",
                    outlineOffset: 2,
                  },
                }}
              >
                {label}
              </Button>
            ))}
          </Stack>
          <Box sx={{ mt: "auto", pt: 5, display: { xs: "none", md: "block" } }}>
            <Divider sx={{ borderColor: "#385358", mb: 2 }} />
            <Typography variant="body2">Local by design</Typography>
            <Typography variant="caption" sx={{ color: "#b7cdca" }}>
              Workbench foundation · Release 1
            </Typography>
          </Box>
        </Box>
        <Box>
          <Box
            component="header"
            sx={{
              px: { xs: 3, md: 5 },
              py: 2.5,
              borderBottom: "1px solid #dfe7e4",
              bgcolor: "white",
              display: "flex",
              justifyContent: "space-between",
              gap: 2,
            }}
          >
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              Industrial Data Pipeline Platform
            </Typography>
            <Chip label="Local workspace" size="small" variant="outlined" />
          </Box>
          <Box
            component="main"
            id="main-content"
            ref={main}
            tabIndex={-1}
            sx={{
              p: { xs: 3, md: 5 },
              maxWidth: 1200,
              mx: "auto",
              outline: "none",
            }}
          >
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/builder" element={<Builder />} />
              <Route
                path="*"
                element={
                  <Stack spacing={2}>
                    <Typography component="h1" variant="h1">
                      Page not found
                    </Typography>
                    <Typography>This workspace page does not exist.</Typography>
                    <Button component={Link} to="/">
                      Return to overview
                    </Button>
                  </Stack>
                }
              />
            </Routes>
          </Box>
        </Box>
      </Box>
    </ThemeProvider>
  );
}
