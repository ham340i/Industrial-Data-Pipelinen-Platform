// AI contribution: below 50% AI-generated
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { port: 3000, strictPort: true },
  preview: { port: 3000, strictPort: true },
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: "ui", test: /node_modules\/(?:@mui|@emotion)\// },
            {
              name: "react",
              test: /node_modules\/(?:react|react-dom|scheduler)\//,
            },
          ],
        },
      },
    },
  },
  test: {
    environment: "jsdom",
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["./src/test/setup.ts"],
    restoreMocks: true,
    clearMocks: true,
    // CI uploads the JUnit file as a workflow artifact (#37); local runs
    // keep the console reporter only.
    reporters: process.env.CI ? ["default", "junit"] : ["default"],
    outputFile: { junit: "test-results/vitest.xml" },
  },
});
