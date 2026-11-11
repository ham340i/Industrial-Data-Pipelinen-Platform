import { expect, test } from "@playwright/test";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

for (const format of ["json", "parquet"] as const) {
  test(`real ${format} source and projection show scoped schema and counts`, async ({
    page,
  }) => {
    const api =
      process.env.LPS_STANDALONE_API_URL || "http://127.0.0.1:8000/api/v1";
    const created = await page.request.post(`${api}/projects`, {
      data: { name: `${format} preview ${Date.now()}` },
    });
    expect(created.status()).toBe(201);
    const project = await created.json();
    const root = join(process.env.LPS_WORKSPACE_ROOT!, project.id);
    await mkdir(root, { recursive: true });
    const rows = [
      { id: 1, value: 10 },
      { id: 2, value: null },
      { id: 3, value: 30 },
    ];
    await writeFile(join(root, "input.json"), JSON.stringify(rows));
    if (format === "parquet") {
      await promisify(execFile)(process.env.LPS_PYTHON || "python", [
        "-c",
        "import json,sys; from pathlib import Path; import pyarrow as pa; import pyarrow.parquet as pq; root=Path(sys.argv[1]); pq.write_table(pa.Table.from_pylist(json.loads((root/'input.json').read_text())),root/'input.parquet',row_group_size=1)",
        root,
      ]);
    }
    await writeFile(join(root, `invalid.${format}`), "invalid input");
    const definition = {
      schema_version: 1,
      nodes: [
        {
          id: "source",
          block_id: `source.${format}`,
          block_version: "1.0.0",
          config: { resource_ref: `input.${format}` },
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
      { data: { name: `${format} preview`, definition } },
    );
    expect(saved.status()).toBe(201);
    const pipeline = await saved.json();
    await page.goto(`/#/projects/${project.id}/builder`);
    await page
      .getByRole("button", { name: `Open ${format} preview (revision 1)` })
      .click();
    const panel = page.getByRole("region", { name: "Selected-node preview" });
    for (const node of ["source", "select"]) {
      await page
        .locator(`.react-flow__node[data-id="${node}"]`)
        .click({ position: { x: 10, y: 10 } });
      await expect(panel.getByRole("table")).toHaveCount(0);
      await panel.getByRole("spinbutton", { name: "Preview rows" }).fill("2");
      await panel
        .getByRole("button", { name: "Preview selected node" })
        .click();
      await expect(panel.getByRole("status")).toContainText("2 sampled rows");
      await expect(panel.getByRole("status")).toContainText(
        format === "json"
          ? "Full row count unknown"
          : "3 total rows reported by file metadata",
      );
      await expect(
        panel.getByText(
          format === "json"
            ? /Schema inferred from sampled rows/
            : /Schema reported by file metadata/,
        ),
      ).toBeVisible();
      await panel.getByRole("tab", { name: "Schema", exact: true }).click();
      await expect(
        panel.getByRole("table", { name: "Preview schema" }),
      ).toContainText("integer");
      await panel.getByRole("tab", { name: "Null summary" }).click();
      await expect(
        panel.getByRole("table", { name: "Preview nulls" }),
      ).toContainText("value");
    }
    await page.setViewportSize({ width: 390, height: 844 });
    await panel.scrollIntoViewIfNeeded();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: test.info().outputPath(`${format}-preview-mobile.png`),
      fullPage: true,
    });
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.getByRole("button", { name: "Fit View", exact: true }).click();
    await page
      .locator('.react-flow__node[data-id="source"]')
      .click({ position: { x: 10, y: 10 } });
    await page
      .getByRole("region", {
        name: `Configure ${format === "json" ? "JSON" : "Parquet"} Source`,
      })
      .getByRole("textbox", { name: "Resource Ref", exact: true })
      .fill(`invalid.${format}`);
    await panel.getByRole("button", { name: "Preview selected node" }).click();
    await expect(
      panel.getByText(
        format === "json"
          ? /JSON must be an array/
          : /Parquet metadata or sampled data is invalid/,
      ),
    ).toBeVisible();
    await expect(readFile(join(root, "output.csv"))).rejects.toMatchObject({
      code: "ENOENT",
    });
    const unchanged = await page.request.get(
      `${api}/projects/${project.id}/pipelines/${pipeline.id}`,
    );
    expect((await unchanged.json()).revision).toBe(1);
    const runs = await page.request.get(`${api}/runs?project_id=${project.id}`);
    expect((await runs.json()).total).toBe(0);
  });
}

test("real CSV and Select previews are bounded, editable and side-effect free", async ({
  page,
}) => {
  const api =
    process.env.LPS_STANDALONE_API_URL || "http://127.0.0.1:8000/api/v1";
  const created = await page.request.post(`${api}/projects`, {
    data: { name: `Preview ${Date.now()}` },
  });
  expect(created.status()).toBe(201);
  const project = await created.json();
  expect(project.id).toMatch(/^[a-f0-9-]{36}$/);
  const root = join(process.env.LPS_WORKSPACE_ROOT!, project.id);
  await mkdir(root, { recursive: true });
  await writeFile(join(root, "input.csv"), "id,value\n1,10\n2,NULL\n3,30\n");
  await writeFile(join(root, "empty.csv"), "id,value\n");
  const definition = {
    schema_version: 1,
    nodes: [
      {
        id: "csv",
        block_id: "source.csv",
        block_version: "1.0.0",
        config: { resource_ref: "input.csv" },
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
        id: "csv-select",
        source: { node_id: "csv", port: "table" },
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
        csv: { x: 0, y: 0 },
        select: { x: 350, y: 0 },
        sink: { x: 700, y: 0 },
      },
    },
  };
  const saved = await page.request.post(
    `${api}/projects/${project.id}/pipelines`,
    { data: { name: "Preview path", definition } },
  );
  expect(saved.status()).toBe(201);
  const pipeline = await saved.json();
  await page.goto(`/#/projects/${project.id}/builder`);
  await page
    .getByRole("button", { name: "Open Preview path (revision 1)" })
    .click();
  const panel = page.getByRole("region", { name: "Selected-node preview" });
  const select = (id: string) =>
    page
      .locator(`.react-flow__node[data-id="${id}"]`)
      .click({ position: { x: 10, y: 10 } });
  await select("csv");
  await panel.getByRole("spinbutton", { name: "Preview rows" }).fill("2");
  const response = page.waitForResponse((r) =>
    r.url().endsWith("/pipelines/preview"),
  );
  await panel.getByRole("button", { name: "Preview selected node" }).click();
  const result = await response;
  expect(result.status()).toBe(200);
  expect(result.headers()["cache-control"]).toBe("no-store");
  expect((await result.json()).full_row_count).toBeNull();
  await expect(panel.getByRole("status")).toContainText("2 sampled rows");
  await panel.getByRole("tab", { name: "Null summary" }).click();
  await expect(
    panel.getByRole("table", { name: "Preview nulls" }),
  ).toContainText("value");
  await panel.getByRole("tab", { name: "Schema", exact: true }).click();
  await expect(
    panel.getByRole("table", { name: "Preview schema" }),
  ).toContainText("string");
  await select("select");
  await expect(panel.getByRole("table")).toHaveCount(0);
  await panel.getByRole("spinbutton", { name: "Preview rows" }).fill("2");
  await panel.getByRole("button", { name: "Preview selected node" }).click();
  await expect(
    panel.getByRole("table", { name: "Preview sample" }),
  ).toContainText("10");
  await page
    .getByRole("region", { name: "Configure Select Columns" })
    .getByRole("textbox", { name: "Columns", exact: true })
    .fill('["id"]');
  await expect(panel.getByRole("table")).toHaveCount(0);
  await panel.getByRole("button", { name: "Preview selected node" }).click();
  await expect(
    panel
      .getByRole("table")
      .getByRole("columnheader", { name: "id", exact: true }),
  ).toBeVisible();
  await panel.scrollIntoViewIfNeeded();
  await page.screenshot({
    path: test.info().outputPath("preview-desktop.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: test.info().outputPath("preview-mobile.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.getByRole("button", { name: "Fit View", exact: true }).click();
  await select("sink");
  await expect(
    panel.getByText("Preview is not supported by this block."),
  ).toBeVisible();
  await expect(
    panel.getByRole("button", { name: "Preview selected node" }),
  ).toHaveCount(0);
  await expect(readFile(join(root, "output.csv"))).rejects.toMatchObject({
    code: "ENOENT",
  });
  await select("csv");
  await page
    .getByRole("region", { name: "Configure CSV Source" })
    .getByRole("textbox", { name: "Resource Ref", exact: true })
    .fill("missing.csv");
  await panel.getByRole("button", { name: "Preview selected node" }).click();
  await expect(
    panel.getByText("Input file is missing or unreadable."),
  ).toBeVisible();
  await expect(panel.getByText(/Field: resource_ref/)).toBeVisible();
  await page
    .getByRole("region", { name: "Configure CSV Source" })
    .getByRole("textbox", { name: "Resource Ref", exact: true })
    .fill("empty.csv");
  await panel.getByRole("button", { name: "Preview selected node" }).click();
  await expect(panel.getByText(/No rows in this input/)).toBeVisible();
  const unchanged = await page.request.get(
    `${api}/projects/${project.id}/pipelines/${pipeline.id}`,
  );
  expect((await unchanged.json()).revision).toBe(1);
  const runs = await page.request.get(`${api}/runs?project_id=${project.id}`);
  expect((await runs.json()).total).toBe(0);
});
