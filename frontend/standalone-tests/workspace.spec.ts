// AI contribution: 50% or more AI-generated
import { expect, test } from "@playwright/test";
import { randomUUID } from "node:crypto";
import { realpath, rm, writeFile } from "node:fs/promises";
import { isAbsolute, join, relative, sep } from "node:path";

test("workspace setup repairs preview and preserves the unsaved draft", async ({
  page,
}) => {
  const api =
    process.env.LPS_STANDALONE_API_URL || "http://127.0.0.1:8000/api/v1";
  const root = process.env.LPS_WORKSPACE_ROOT!;
  const created = await page.request.post(`${api}/projects`, {
    data: { name: `Workspace setup ${randomUUID().slice(0, 12)}` },
  });
  expect(created.status()).toBe(201);
  const project = await created.json();
  const saved = await page.request.post(
    `${api}/projects/${project.id}/pipelines`,
    {
      data: {
        name: "Workspace setup",
        definition: {
          schema_version: 1,
          nodes: [
            {
              id: "source",
              block_id: "source.json",
              block_version: "1.0.0",
              config: { resource_ref: "inputs/original.json" },
            },
          ],
          edges: [],
        },
      },
    },
  );
  expect(saved.status()).toBe(201);
  const folder = await realpath(join(root, project.name, "Workspace setup"));
  const relativeFolder = relative(await realpath(root), folder);
  expect(relativeFolder).not.toBe("");
  expect(isAbsolute(relativeFolder)).toBe(false);
  expect(relativeFolder.split(sep)).not.toContain("..");
  // Exercise repair of a nonempty folder belonging only to this test run.
  await writeFile(
    join(folder, "inputs", "stale-fixture.json"),
    '[{"value":0}]',
  );
  await rm(folder, { recursive: true, force: true });
  await page.goto(`/#/projects/${project.id}/builder`);
  await page
    .getByRole("button", { name: "Open Workspace setup (revision 1)" })
    .click();
  await page
    .locator('.react-flow__node[data-id="source"]')
    .click({ position: { x: 10, y: 10 } });
  const field = page.getByRole("textbox", {
    name: "Resource Ref",
    exact: true,
  });
  await field.fill("inputs/workspace.json");
  await page.getByRole("button", { name: "Preview selected node" }).click();
  await page.getByRole("link", { name: "Configure workspace" }).click();
  await expect(
    page.getByRole("heading", { name: "Settings", exact: true }),
  ).toBeVisible();
  const rootField = page.getByRole("textbox", {
    name: "Workspace root folder",
  });
  await expect(rootField).toHaveValue(root);
  await rootField.fill(join(root, "does-not-exist"));
  await rootField.press("Enter");
  await expect(page.getByRole("alert")).toContainText(
    "Choose an existing folder",
  );
  await rootField.fill(root);
  await rootField.press("Enter");
  await expect(page.getByRole("alert")).toContainText("Workspace saved");
  expect(
    (await (await page.request.get(`${api}/settings/workspace`)).json()).source,
  ).toBe("application");
  await writeFile(join(folder, "inputs", "workspace.json"), '[{"value":42}]');
  await page.screenshot({
    path: test.info().outputPath("workspace-desktop.png"),
    fullPage: true,
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
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole("link", { name: "Return to project builder" }).click();
  await expect(field).toHaveValue("inputs/workspace.json");
  await page.getByRole("button", { name: "Preview selected node" }).click();
  await expect(
    page.getByRole("table", { name: "Preview sample" }),
  ).toContainText("42");
  await page.getByRole("link", { name: "Settings", exact: true }).click();
  await page.reload();
  await expect(rootField).toHaveValue(root);
  expect(
    (await (await page.request.get(`${api}/settings/workspace`)).json()).source,
  ).toBe("application");
  await page.getByRole("button", { name: "Use environment setting" }).click();
  await expect(
    page.getByRole("button", { name: "Use environment setting" }),
  ).toHaveCount(0);
  expect(
    (await (await page.request.get(`${api}/settings/workspace`)).json()).source,
  ).toBe("environment");
});
