// @vitest-environment node
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { afterEach, describe, expect, it } from "vitest";

// Controlled tests of the harness: each frontend check must fail on a broken
// synthetic fixture. A passing control proves the tool was able to run at all.

const require = createRequire(import.meta.url);
const temporaryDirectories: string[] = [];

function binPath(packageName: string, binName: string): string {
  const manifestPath = require.resolve(`${packageName}/package.json`);
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as {
    bin: string | Record<string, string>;
  };
  const relative =
    typeof manifest.bin === "string" ? manifest.bin : manifest.bin[binName];
  return join(dirname(manifestPath), relative);
}

function run(
  packageName: string,
  binName: string,
  args: string[],
  input?: string,
) {
  const env = Object.fromEntries(
    Object.entries(process.env).filter(([name]) => !name.startsWith("VITEST")),
  );
  const result = spawnSync(
    process.execPath,
    [binPath(packageName, binName), ...args],
    { encoding: "utf8", env, input, timeout: 60000 },
  );
  return { status: result.status, output: result.stdout + result.stderr };
}

function fixtureDirectory(files: Record<string, string>): string {
  const directory = mkdtempSync(join(tmpdir(), "lps-harness-"));
  temporaryDirectories.push(directory);
  for (const [name, content] of Object.entries(files)) {
    writeFileSync(join(directory, name), content);
  }
  return directory;
}

afterEach(() => {
  for (const directory of temporaryDirectories.splice(0)) {
    rmSync(directory, { recursive: true, force: true });
  }
});

describe("harness failure propagation", () => {
  // Each test launches a passing and broken subprocess (up to 60s each).
  it("ESLint fails on a lint violation", { timeout: 120000 }, () => {
    const args = ["--stdin", "--stdin-filename", "src/harness-fixture.ts"];

    const control = run("eslint", "eslint", args, "export const value = 1;\n");
    const broken = run("eslint", "eslint", args, "const unused = 1;\n");

    expect(control.status, control.output).toBe(0);
    expect(broken.status, broken.output).toBe(1);
    expect(broken.output).toContain("no-unused-vars");
  });

  it("Prettier check fails on unformatted source", { timeout: 120000 }, () => {
    const args = ["--check", "--stdin-filepath", "src/harness-fixture.ts"];

    const control = run("prettier", "prettier", args, "const value = 1;\n");
    const broken = run("prettier", "prettier", args, "const   value=1\n");

    expect(control.status, control.output).toBe(0);
    expect(broken.status, broken.output).toBe(1);
  });

  it("TypeScript fails on a type error", { timeout: 120000 }, () => {
    const directory = fixtureDirectory({
      "typed.ts": "export const value: number = 1;\n",
      "mistyped.ts": 'export const value: number = "not a number";\n',
    });
    const args = ["--noEmit", "--strict", "--ignoreConfig"];

    const control = run("typescript", "tsc", [
      ...args,
      join(directory, "typed.ts"),
    ]);
    const broken = run("typescript", "tsc", [
      ...args,
      join(directory, "mistyped.ts"),
    ]);

    expect(control.status, control.output).toBe(0);
    expect(broken.status, broken.output).not.toBe(0);
    expect(broken.output).toContain("TS2322");
  });

  it("Vitest fails on a failing test", { timeout: 120000 }, () => {
    const config = (name: string) =>
      `export default { test: { globals: true, include: ["${name}"] } };\n`;
    const directory = fixtureDirectory({
      "passing.config.mjs": config("passing.test.js"),
      "failing.config.mjs": config("failing.test.js"),
      "passing.test.js": 'test("control", () => expect(1 + 1).toBe(2));\n',
      "failing.test.js": 'test("broken", () => expect(1 + 1).toBe(3));\n',
    });
    const args = (name: string) => [
      "run",
      "--root",
      directory,
      "--config",
      join(directory, `${name}.config.mjs`),
    ];

    const control = run("vitest", "vitest", args("passing"));
    const broken = run("vitest", "vitest", args("failing"));

    expect(control.status, control.output).toBe(0);
    expect(broken.status, broken.output).toBe(1);
    expect(broken.output).toContain("1 failed");
  });
});
