import { defineConfig } from "@playwright/test";

if (!process.env.COMPOSE_BASE_URL) {
  throw new Error("Run this test through scripts/smoke_workspace.py --browser");
}

export default defineConfig({
  testDir: "./compose-tests",
  use: {
    baseURL: process.env.COMPOSE_BASE_URL,
    launchOptions: process.env.PLAYWRIGHT_CHROME_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROME_PATH }
      : {},
  },
});
