// AI contribution: 50% or more AI-generated
import { expect, test, type Page } from "@playwright/test";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";

const api =
  process.env.LPS_STANDALONE_API_URL || "http://127.0.0.1:8000/api/v1";

async function seed(page: Page, missing = true) {
  const response = await page.request.post(`${api}/projects`, {
    data: { name: `Recovery ${test.info().title} ${Date.now()}` },
  });
  expect(response.status()).toBe(201);
  const project = await response.json();
  const root = join(process.env.LPS_WORKSPACE_ROOT!, project.id);
  await mkdir(root, { recursive: true });
  await writeFile(join(root, "input.csv"), "id,value\n1,10\n2,20\n");
  const definition = {
    schema_version: 1,
    nodes: [
      {
        id: "source",
        block_id: "source.csv",
        block_version: "1.0.0",
        config: { resource_ref: missing ? "missing.csv" : "input.csv" },
      },
      {
        id: "select",
        block_id: "transform.select",
        block_version: "1.0.0",
        config: { columns: ["value"] },
      },
      {
        id: "sink",
        block_id: "sink.csv",
        block_version: "1.0.0",
        config: { resource_ref: "output.csv" },
      },
    ],
    edges: [
      {
        id: "source-select",
        source: { node_id: "source", port: "table" },
        target: { node_id: "select", port: "table" },
      },
      {
        id: "select-sink",
        source: { node_id: "select", port: "table" },
        target: { node_id: "sink", port: "table" },
      },
    ],
    layout: {
      positions: {
        source: { x: 0, y: 0 },
        select: { x: 350, y: 0 },
        sink: { x: 700, y: 0 },
      },
    },
  };
  const saved = await page.request.post(
    `${api}/projects/${project.id}/pipelines`,
    {
      data: { name: "Recovery path", definition },
    },
  );
  expect(saved.status()).toBe(201);
  const pipeline = await saved.json();
  const url = `${api}/projects/${project.id}/pipelines/${pipeline.id}`;
  await page.goto(`/#/projects/${project.id}/builder`);
  await page
    .getByRole("button", { name: "Open Recovery path (revision 1)" })
    .click();
  return { project, pipeline, root, url, definition };
}

async function selectNode(page: Page, id: string) {
  await page
    .locator(`.react-flow__node[data-id="${id}"]`)
    .click({ position: { x: 10, y: 10 } });
}

async function exportGraph(page: Page) {
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export JSON", exact: true }).click();
  return JSON.parse(await readFile((await (await download).path())!, "utf8"));
}

async function runCount(page: Page, projectId: string) {
  const response = await page.request.get(
    `${api}/runs?project_id=${projectId}`,
  );
  expect(response.status()).toBe(200);
  return (await response.json()).total;
}

test("missing CSV preview recovers by keyboard without losing unsaved config or saving/running", async ({
  page,
}) => {
  const { project, url, root } = await seed(page);
  await selectNode(page, "select");
  await page
    .getByRole("textbox", { name: "Columns", exact: true })
    .fill('["id"]');
  const panel = page.getByRole("region", { name: "Selected-node preview" });
  const failed = page.waitForResponse((r) =>
    r.url().endsWith("/pipelines/preview"),
  );
  await panel.getByRole("button", { name: "Preview selected node" }).click();
  expect((await failed).status()).toBe(422);
  await expect(panel.getByRole("alert")).toContainText(
    "Input file is missing or unreadable.",
  );
  const configure = panel.getByRole("button", {
    name: "Configure node",
    exact: true,
  });
  await configure.focus();
  await page.keyboard.press("Enter");
  const resource = page
    .getByRole("region", { name: "Configure CSV Source" })
    .getByRole("textbox", { name: "Resource Ref", exact: true });
  await expect(resource).toBeFocused();
  await expect(resource).toHaveValue("missing.csv");
  await resource.fill("input.csv");
  await selectNode(page, "select");
  await expect(
    page.getByRole("textbox", { name: "Columns", exact: true }),
  ).toHaveValue('["id"]');
  const retry = page.waitForResponse((r) =>
    r.url().endsWith("/pipelines/preview"),
  );
  await panel.getByRole("button", { name: "Preview selected node" }).click();
  expect((await retry).status()).toBe(200);
  await expect(
    panel
      .getByRole("table", { name: "Preview sample" })
      .getByRole("columnheader", { name: "id", exact: true }),
  ).toBeVisible();
  expect((await (await page.request.get(url)).json()).revision).toBe(1);
  expect(await runCount(page, project.id)).toBe(0);
  await expect(readFile(join(root, "output.csv"))).rejects.toMatchObject({
    code: "ENOENT",
  });
  await expect(
    page.getByRole("button", { name: "Run saved pipeline" }),
  ).toBeDisabled();
});

test("failed saved run focuses its block, retains edits and runs a corrected revision", async ({
  page,
}) => {
  const { project, url, root } = await seed(page);
  const run = page.getByRole("button", { name: "Run saved pipeline" });
  await expect(run).toBeEnabled();
  const execution = page.waitForResponse((r) => r.url().endsWith("/execute"));
  await run.click();
  expect((await execution).status()).toBe(201);
  await expect(
    page.getByRole("status", { name: "Execution status" }),
  ).toContainText("Run failed");
  const name = page.getByRole("textbox", { name: "Draft pipeline name" });
  await name.fill("Recovered unsaved name");
  const configure = page.getByRole("button", {
    name: "Configure failed block source",
    exact: true,
  });
  await configure.focus();
  await page.keyboard.press("Enter");
  const form = page.getByRole("region", { name: "Configure CSV Source" });
  await expect(form).toBeFocused();
  await selectNode(page, "select");
  await page
    .getByRole("textbox", { name: "Columns", exact: true })
    .fill('["id"]');
  await expect(configure).toHaveCount(0);
  await expect(
    page.getByText(/configuration links are disabled/),
  ).toBeVisible();
  await selectNode(page, "source");
  await form
    .getByRole("textbox", { name: "Resource Ref", exact: true })
    .fill("input.csv");
  await expect(name).toHaveValue("Recovered unsaved name");
  await expect(run).toBeDisabled();
  await selectNode(page, "select");
  await expect(
    page.getByRole("textbox", { name: "Columns", exact: true }),
  ).toHaveValue('["id"]');
  expect((await (await page.request.get(url)).json()).revision).toBe(1);
  expect(await runCount(page, project.id)).toBe(1);
  const save = page.waitForResponse(
    (r) => r.url() === url && r.request().method() === "PUT",
  );
  await page
    .getByRole("button", { name: "Save pipeline", exact: true })
    .click();
  const saved = await (await save).json();
  expect(saved.revision).toBe(2);
  expect(saved.name).toBe("Recovered unsaved name");
  expect(
    saved.definition.nodes.find((n: { id: string }) => n.id === "select").config
      .columns,
  ).toEqual(["id"]);
  await expect(run).toBeEnabled();
  await run.click();
  await expect(
    page.getByRole("status", { name: "Execution status" }),
  ).toContainText("Run succeeded");
  await expect(
    page.getByRole("status", { name: "Execution status" }),
  ).toContainText("revision 2");
  expect(await runCount(page, project.id)).toBe(2);
  expect(
    (await readFile(join(root, "output.csv"), "utf8")).trim().split(/\r?\n/),
  ).toEqual(["id", "1", "2"]);
});

test("peer save before Run refuses stale revision without creating a run or replacing the local graph", async ({
  page,
}) => {
  const { project, url, definition } = await seed(page, false);
  const before = await exportGraph(page);
  const peer = structuredClone(definition);
  peer.nodes[1].config = { columns: ["id"] };
  const update = await page.request.put(url, {
    data: { name: "Peer revision", definition: peer, expected_revision: 1 },
  });
  expect(update.status()).toBe(200);
  expect((await update.json()).revision).toBe(2);
  const execution = page.waitForResponse((r) => r.url().endsWith("/execute"));
  await page.getByRole("button", { name: "Run saved pipeline" }).click();
  const refusal = await execution;
  expect(refusal.request().postDataJSON()).toEqual({ expected_revision: 1 });
  expect(refusal.status()).toBe(409);
  expect((await refusal.json()).error.code).toBe("revision_conflict");
  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: "This pipeline changed since it was opened" }),
  ).toContainText("Your saved pipeline is retained");
  expect(await runCount(page, project.id)).toBe(0);
  expect(await exportGraph(page)).toEqual(before);
  await expect(
    page.getByRole("textbox", { name: "Draft pipeline name" }),
  ).toHaveValue("Recovery path");
  expect((await (await page.request.get(url)).json()).revision).toBe(2);
});
