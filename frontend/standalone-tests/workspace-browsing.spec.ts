// AI contribution: 50% or more AI-generated
import { expect, test } from "@playwright/test";
import { mkdir, readFile, unlink, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";

const api = () =>
  process.env.LPS_STANDALONE_API_URL || "http://127.0.0.1:8000/api/v1";

// Only the Windows dialog is stubbed. Workspace and run APIs are real.
test("autosaves folder confirmation, reloads projects, and restores each workspace's draft", async ({
  page,
}) => {
  const root = process.env.LPS_WORKSPACE_ROOT!;
  const selected = join(dirname(root), `Other workspace ${Date.now()}`);
  await mkdir(selected, { recursive: true });
  const name = `Workspace A ${Date.now()}`;
  const project = await (
    await page.request.post(`${api()}/projects`, { data: { name } })
  ).json();
  const saved = await page.request.post(
    `${api()}/projects/${project.id}/pipelines`,
    {
      data: {
        name: "Readings",
        definition: { schema_version: 1, nodes: [], edges: [] },
      },
    },
  );
  expect(saved.status()).toBe(201);
  let choices = 0;
  await page.route("**/settings/workspace/pick-folder", async (route) => {
    choices += 1;
    await route.fulfill({ json: { path: choices === 1 ? null : selected } });
  });
  await page.goto(`/#/projects/${project.id}/builder`);
  await page
    .getByRole("button", { name: "Open Readings (revision 1)" })
    .click();
  const draft = page.getByRole("textbox", { name: "Draft pipeline name" });
  await draft.fill("Unsaved A");
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  const field = page.getByRole("textbox", { name: "Workspace root folder" });
  const browse = page.getByRole("button", { name: /Browse/ });
  await expect(field).toHaveValue(root);
  await expect(
    page.getByRole("button", { name: "Save workspace", exact: true }),
  ).toHaveCount(0);
  await browse.click();
  await expect(browse).toBeEnabled();
  await expect(field).toHaveValue(root);
  await browse.click();
  await expect(page.getByRole("alert")).toContainText("Workspace saved");
  await expect(field).toHaveValue(selected);
  expect(
    (await (await page.request.get(`${api()}/settings/workspace`)).json())
      .root_path,
  ).toBe(selected);
  await page.getByRole("link", { name: "Projects", exact: true }).click();
  await expect(
    page.getByText("No projects yet. Create your first project above."),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: `Open ${name}`, exact: true }),
  ).toHaveCount(0);
  await page
    .getByRole("textbox", { name: "Project name" })
    .fill("Workspace B project");
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await draft.fill("Unsaved B");
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await field.fill(root);
  await field.press("Enter");
  await expect(page.getByRole("alert")).toContainText("Workspace saved");
  await page.getByRole("link", { name: "Return to project builder" }).click();
  await expect(draft).toHaveValue("Unsaved A");
  await expect(
    page.getByRole("button", { name: "Open Readings (revision 1)" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await field.fill(selected);
  await field.press("Enter");
  await expect(page.getByRole("alert")).toContainText("Workspace saved");
  await page.getByRole("link", { name: "Return to project builder" }).click();
  await expect(draft).toHaveValue("Unsaved B");
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await field.fill(root);
  await field.press("Enter");
  await expect(page.getByRole("alert")).toContainText("Workspace saved");
  await page.reload();
  await expect(field).toHaveValue(root);
  await page.screenshot({
    path: test.info().outputPath("workspace-desktop.png"),
    fullPage: true,
    animations: "disabled",
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: test.info().outputPath("workspace-mobile.png"),
    fullPage: true,
    animations: "disabled",
  });
});

test("shows only failed blocks and downloads the selected historical run's complete log", async ({
  page,
}) => {
  const root = process.env.LPS_WORKSPACE_ROOT!;
  const name = `Run logs ${Date.now()}`;
  const project = await (
    await page.request.post(`${api()}/projects`, { data: { name } })
  ).json();
  const definition = {
    schema_version: 1,
    nodes: [
      {
        id: "source",
        block_id: "source.json",
        block_version: "1.0.0",
        config: { resource_ref: "inputs/readings.json" },
      },
      {
        id: "sink",
        block_id: "sink.parquet",
        block_version: "1.0.0",
        config: { resource_ref: "outputs/result.parquet" },
      },
    ],
    edges: [
      {
        id: "link",
        source: { node_id: "source", port: "table" },
        target: { node_id: "sink", port: "table" },
      },
    ],
  };
  const response = await page.request.post(
    `${api()}/projects/${project.id}/pipelines`,
    { data: { name: "Readings", definition } },
  );
  expect(response.status()).toBe(201);
  const pipeline = await response.json();
  const input = join(root, name, "Readings", "inputs", "readings.json");
  await writeFile(input, '[{"value": 4}]');
  const execute = `${api()}/projects/${project.id}/pipelines/${pipeline.id}/execute`;
  const success = await (await page.request.post(execute)).json();
  expect(success.state).toBe("succeeded");
  await unlink(input);
  const failed = await (await page.request.post(execute)).json();
  expect(failed.state).toBe("failed");
  await page.goto(`/#/projects/${project.id}/builder`);
  await page
    .getByRole("button", { name: "Open Readings (revision 1)" })
    .click();
  const monitor = page.getByRole("region", {
    name: "Run monitoring",
    exact: true,
  });
  await expect(
    monitor.getByText(`Failed \u00b7 Run ${failed.run_id}`, { exact: true }),
  ).toBeVisible();
  await expect(
    monitor.getByRole("heading", { name: "Failed blocks" }),
  ).toBeVisible();
  await expect(
    monitor.getByRole("region", { name: "Block source" }),
  ).toBeVisible();
  await expect(monitor.getByRole("region", { name: "Block sink" })).toHaveCount(
    0,
  );
  await expect(
    monitor.getByRole("list", { name: "Run log events" }),
  ).toHaveCount(0);
  await monitor.getByLabel("Selected run").selectOption(success.run_id);
  await expect(
    monitor.getByText(`Completed \u00b7 Run ${success.run_id}`, {
      exact: true,
    }),
  ).toBeVisible();
  await expect(
    monitor.getByRole("heading", { name: "Failed blocks" }),
  ).toHaveCount(0);
  const downloadEvent = page.waitForEvent("download");
  await monitor
    .getByRole("button", { name: "Download log", exact: true })
    .click();
  const download = await downloadEvent;
  expect(download.suggestedFilename()).toBe(`run-${success.run_id}.log`);
  const log = await readFile((await download.path())!, "utf8");
  expect(log).toContain(`Run ${success.run_id}`);
  expect(log).toContain("Result: succeeded");
  expect(log).toContain("Events (credentials and machine paths redacted)");
  await page.screenshot({
    path: test.info().outputPath("run-results-desktop.png"),
    fullPage: true,
    animations: "disabled",
  });
});
