import { defineConfig } from "@playwright/test";

// No HTTP mocks: exercise the default Vite origin against the actual API.
const frontendUrl = process.env.LPS_STANDALONE_URL || "http://127.0.0.1:3000";
const python = process.env.LPS_PYTHON || "python";
const frontendCommand =
  process.env.LPS_STANDALONE_MODE === "preview"
    ? "npm run preview"
    : "npm run dev";

export default defineConfig({
  testDir: "./standalone-tests",
  workers: 1,
  use: {
    baseURL: frontendUrl,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    launchOptions: process.env.PLAYWRIGHT_CHROME_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROME_PATH }
      : {},
  },
  webServer: [
    {
      command: `"${python}" -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: "..",
      url: "http://127.0.0.1:8000/api/v1/health",
      reuseExistingServer: false,
      timeout: 30000,
    },
    {
      command: frontendCommand,
      url: frontendUrl,
      reuseExistingServer: false,
      timeout: 30000,
    },
  ],
});
