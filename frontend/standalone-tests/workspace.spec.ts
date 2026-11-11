import { expect, test } from "@playwright/test";
import { rmdir, writeFile } from "node:fs/promises";
import { join } from "node:path";

test("workspace setup repairs preview and preserves the unsaved draft", async ({
  page,
}) => {
  const api =
    process.env.LPS_STANDALONE_API_URL || "http://127.0.0.1:8000/api/v1";
  const root = process.env.LPS_WORKSPACE_ROOT!;
  const created = await page.request.post(`${api}/projects`, {
    data: { name: "Workspace setup" },
  });
  expect(created.status()).toBe(201);
  const project = await created.json();
  // Remove only the empty directories created for this synthetic project.
  // Nonrecursive rmdir fails safely if anything has been placed in them.
  await rmdir(join(root, project.id, "inputs"));
  await rmdir(join(root, project.id));
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
    page.getByRole("heading", { name: "Workspace settings" }),
  ).toBeVisible();
  const rootField = page.getByRole("textbox", {
    name: "Workspace root folder",
  });
  await expect(rootField).toHaveValue(root);
  await rootField.fill(join(root, "does-not-exist"));
  await page.getByRole("button", { name: "Save workspace" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Choose an existing folder",
  );
  await rootField.fill(root);
  await page.getByRole("button", { name: "Save workspace" }).click();
  await expect(page.getByRole("alert")).toContainText("Workspace saved");
  await expect(page.getByText(/Using the saved app setting/)).toBeVisible();
  await writeFile(
    join(root, project.id, "inputs", "workspace.json"),
    '[{"value":42}]',
  );
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
  await expect(page.getByText(/Using the saved app setting/)).toBeVisible();
  await page.getByRole("button", { name: "Use environment setting" }).click();
  await expect(
    page.getByText(/Using LPS_WORKSPACE_ROOT from the API environment/),
  ).toBeVisible();
});
