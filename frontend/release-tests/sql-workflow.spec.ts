// AI contribution: 50% or more AI-generated
import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { join } from "node:path";

test("author SQL source, validate, save, execute, reload, rerun and inspect a failure", async ({
  page,
}) => {
  await page.goto("/#/projects");
  await page
    .getByRole("textbox", { name: "Project name" })
    .fill("SQL acceptance");
  const created = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/projects"),
  );
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  const project = await (await created).json();
  const workspace = join(
    process.env.LPS_RELEASE_TEST_ROOT!,
    "workspaces",
    project.id,
  );
  mkdirSync(workspace, { recursive: true });
  execFileSync(process.env.LPS_PYTHON ?? "python", [
    "-c",
    "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.executescript(\"CREATE TABLE assets(asset_id INTEGER, label TEXT); INSERT INTO assets VALUES (1,'A'),(2,NULL);\"); c.close()",
    join(workspace, "data.sqlite3"),
  ]);
  await page
    .getByRole("textbox", { name: "Draft pipeline name" })
    .fill("SQL assets");
  await page
    .getByRole("button", { name: "Add SQL Source", exact: true })
    .click();
  const form = page.getByRole("region", {
    name: "Configure SQL Source",
    exact: true,
  });
  for (const [label, value] of Object.entries({
    "Resource Ref": "data.sqlite3",
    Query: "SELECT asset_id, label FROM assets ORDER BY asset_id",
    Columns: '["asset_id","label"]',
    Types: '["integer","string"]',
    Nullable: "[false,true]",
  }))
    await form.getByRole("textbox", { name: label, exact: true }).fill(value);
  const run = page.getByRole("button", { name: "Run saved pipeline" });
  await expect(run).toBeDisabled();
  await page
    .getByRole("button", { name: "Save pipeline", exact: true })
    .click();
  await expect(
    page.getByText("Pipeline saved.", { exact: true }),
  ).toBeVisible();
  await expect(run).toBeEnabled();
  await run.click();
  await expect(page.getByText("Run succeeded · revision 1")).toBeVisible();
  await expect(
    page.getByText(/Duration: \d+ ms · Output rows: 2/),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Run log" })).toBeVisible();
  await page.reload();
  await page
    .getByRole("button", { name: "Open SQL assets (revision 1)" })
    .click();
  await expect(run).toBeEnabled();
  await run.click();
  await expect(page.getByText("Run succeeded · revision 1")).toBeVisible();
  await expect(
    page.getByText(/Duration: \d+ ms · Output rows: 2/),
  ).toBeVisible();
  await page.locator(".react-flow__node").click();
  await form
    .getByRole("textbox", { name: "Query", exact: true })
    .fill("SELECT asset_id, label FROM missing_table");
  await expect(run).toBeDisabled();
  await page
    .getByRole("button", { name: "Save pipeline", exact: true })
    .click();
  await expect(run).toBeEnabled();
  await run.click();
  await expect(page.getByText("Run failed · revision 2")).toBeVisible();
  await expect(page.getByText(/sql_query_failed/).first()).toBeVisible();
});
