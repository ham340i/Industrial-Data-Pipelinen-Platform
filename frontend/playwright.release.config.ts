// AI contribution: 50% or more AI-generated
import { defineConfig } from "@playwright/test";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import standalone from "./playwright.standalone.config";

// Dedicated real services and metadata: never reuse a developer's workspace.
const root =
  process.env.LPS_RELEASE_TEST_ROOT ??
  mkdtempSync(join(tmpdir(), "lps-release-"));
process.env.LPS_RELEASE_TEST_ROOT = root;
const servers = standalone.webServer as {
  command: string;
  cwd?: string;
  url: string;
  reuseExistingServer: boolean;
  timeout: number;
}[];
export default defineConfig({
  ...standalone,
  testDir: "./release-tests",
  webServer: servers.map((server) => ({
    ...server,
    env: {
      LPS_METADATA_PATH: join(root, "metadata.sqlite3"),
      LPS_WORKSPACE_ROOT: join(root, "workspaces"),
    },
  })),
});
