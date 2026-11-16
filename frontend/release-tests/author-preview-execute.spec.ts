// AI contribution: 50% or more AI-generated
import { expect, test } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

test.setTimeout(120_000);
test.use({ viewport: { width: 2560, height: 1440 } });

test("author the release graph, preview, validate, inspect Parquet, reopen, rerun and recover", async ({
  page,
}, testInfo) => {
  await page.goto("/#/projects");
  await page
    .getByRole("textbox", { name: "Project name" })
    .fill("Release acceptance");
  const creating = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/projects"),
  );
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  const project = await (await creating).json();
  const workspace = join(
    process.env.LPS_RELEASE_TEST_ROOT!,
    "workspaces",
    project.id,
  );
  mkdirSync(workspace, { recursive: true });
  writeFileSync(
    join(workspace, "readings.csv"),
    "asset_id,reading\n1,5\n1,12\n1,18\n2,20\n2,30\n3,40\n",
  );
  execFileSync(process.env.LPS_PYTHON ?? "python", [
    "-c",
    "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); c.executescript(\"CREATE TABLE assets(asset_id INTEGER, label TEXT); INSERT INTO assets VALUES (1,'A'),(2,'B'),(3,NULL);\"); c.close()",
    join(workspace, "data.sqlite3"),
  ]);
  await page
    .getByRole("textbox", { name: "Draft pipeline name" })
    .fill("Release CSV SQL aggregate");

  async function add(
    name: string,
    config: Record<string, string>,
    x: number,
    y: number,
  ) {
    const canvas = page.getByLabel("Pipeline canvas", { exact: true });
    await canvas.scrollIntoViewIfNeeded();
    const box = (await canvas.boundingBox())!;
    const dragData = await page.evaluateHandle(() => new DataTransfer());
    const button = page.getByRole("button", {
      name: `Add ${name}`,
      exact: true,
    });
    const entry = page.locator('[draggable="true"]').filter({ has: button });
    await entry.dispatchEvent("dragstart", { dataTransfer: dragData });
    await canvas.dispatchEvent("drop", {
      dataTransfer: dragData,
      clientX: box.x + x,
      clientY: box.y + y,
    });
    await dragData.dispose();
    const node = page.locator(".react-flow__node.selected");
    await expect(node).toHaveCount(1);
    const id = (await node.getAttribute("data-id"))!;
    const form = page.getByRole("region", {
      name: `Configure ${name}`,
      exact: true,
    });
    for (const [label, value] of Object.entries(config))
      await form.getByRole("textbox", { name: label, exact: true }).fill(value);
    return id;
  }
  const csv = await add(
    "CSV Source",
    {
      "Resource Ref": "readings.csv",
      Columns: '["asset_id","reading"]',
      Types: '["integer","integer"]',
      Nullable: "[false,false]",
    },
    40,
    40,
  );
  const preview = page.getByRole("region", {
    name: "Selected-node preview",
    exact: true,
  });
  await preview
    .getByRole("spinbutton", { name: "Preview rows", exact: true })
    .fill("3");
  await preview
    .getByRole("button", { name: "Preview selected node", exact: true })
    .click();
  await expect(preview.getByText(/3 sampled rows/)).toBeVisible();
  await expect(
    preview.getByRole("cell", { name: "12", exact: true }),
  ).toBeVisible();
  const validate = await add(
    "Validate Schema",
    {
      Columns:
        '[{"name":"asset_id","dtype":"integer","nullable":false},{"name":"reading","dtype":"integer","nullable":false}]',
    },
    360,
    40,
  );
  const filter = await add(
    "Filter",
    { Column: "reading", "Value Text": "10" },
    680,
    40,
  );
  await page
    .getByRole("region", { name: "Configure Filter", exact: true })
    .getByLabel("Operator", { exact: true })
    .selectOption('"gt"');
  const sql = await add(
    "SQL Source",
    {
      "Resource Ref": "data.sqlite3",
      Query:
        "SELECT asset_id, label FROM assets WHERE label IS NOT NULL ORDER BY asset_id",
      Columns: '["asset_id","label"]',
      Types: '["integer","string"]',
      Nullable: "[false,true]",
    },
    40,
    300,
  );
  const joinId = await add(
    "Join",
    { "Left On": '["asset_id"]', "Right On": '["asset_id"]' },
    360,
    300,
  );
  const aggregate = await add(
    "Aggregate",
    {
      "Group By": '["label"]',
      Operations:
        '[{"column":"reading","function":"sum","output_name":"total"}]',
    },
    680,
    300,
  );
  const sink = await add(
    "Parquet Sink",
    { "Resource Ref": "result.parquet" },
    1000,
    300,
  );
  await page
    .getByRole("region", { name: "Configure Parquet Sink", exact: true })
    .getByLabel("Overwrite", { exact: true })
    .selectOption('"replace"');

  async function connect(source: string, target: string, port = "table") {
    await page.getByRole("button", { name: "Fit View", exact: true }).click();
    await page
      .locator(`.react-flow__node[data-id="${source}"]`)
      .locator('.source[data-handleid="table"]')
      .click();
    await page
      .locator(`.react-flow__node[data-id="${target}"]`)
      .locator(`.target[data-handleid="${port}"]`)
      .click();
  }
  await connect(csv, validate);
  await connect(validate, filter);
  await connect(filter, joinId, "left");
  await connect(sql, joinId, "right");
  await connect(joinId, aggregate);
  await connect(aggregate, sink);
  await expect(page.locator(".react-flow__edge")).toHaveCount(6);
  await page
    .getByRole("button", { name: "Validate pipeline", exact: true })
    .click();
  await expect(
    page.getByText("Ready to run. No problems found.", { exact: true }),
  ).toBeVisible();
  const runButton = page.getByRole("button", {
    name: "Run saved pipeline",
    exact: true,
  });
  await expect(runButton).toBeDisabled();
  const saving = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/pipelines"),
  );
  await page
    .getByRole("button", { name: "Save pipeline", exact: true })
    .click();
  const saved = await (await saving).json();
  await expect(runButton).toBeEnabled();

  async function executeAndInspect() {
    const executing = page.waitForResponse(
      (r) => r.request().method() === "POST" && r.url().endsWith("/execute"),
    );
    await runButton.click();
    const execution = await (await executing).json();
    const controls = page.getByLabel("Pipeline execution", { exact: true });
    await expect(
      controls.getByText("Run succeeded · revision 1", { exact: true }),
    ).toBeVisible();
    await expect(
      controls.getByText(/Duration: \d+ ms · Output rows:/),
    ).toBeVisible();
    for (const [nodeId, rowsIn, rowsOut] of [
      [csv, 0, 6],
      [validate, 6, 6],
      [filter, 6, 5],
      [sql, 0, 2],
      [joinId, 7, 4],
      [aggregate, 4, 2],
      [sink, 2, 1],
    ])
      await expect(
        controls.getByText(
          new RegExp(
            `${nodeId}: completed · \\d+ ms · rows ${rowsIn} → ${rowsOut}`,
          ),
        ),
      ).toBeVisible();
    await expect(
      controls.getByText("Run succeeded", { exact: true }),
    ).toBeVisible();
    await expect(
      controls.getByRole("heading", { name: "Run log", exact: true }),
    ).toBeVisible();
    const outputs = controls.getByRole("region", {
      name: "Output inspection",
      exact: true,
    });
    await outputs.getByRole("button", { name: /Inspect output/ }).click();
    await expect(
      outputs.getByRole("table", { name: "Parquet output rows" }),
    ).toBeVisible();
    const rows = await outputs.getByRole("row").allTextContents();
    expect(rows).toEqual(["labeltotal", "A30", "B50"]);
    await expect(
      outputs.getByRole("button", { name: "Next output rows" }),
    ).toBeDisabled();
    await testInfo.attach(`run-${execution.run_id}.json`, {
      body: JSON.stringify({ saved, execution, rows }, null, 2),
      contentType: "application/json",
    });
    return rows;
  }
  const firstRows = await executeAndInspect();
  await page.reload();
  // Reopen the project via the UI, not an API-loaded graph.
  await page.goto("/#/projects");
  await page
    .getByRole("link", { name: "Open Release acceptance", exact: true })
    .click();
  await page
    .getByRole("button", {
      name: "Open Release CSV SQL aggregate (revision 1)",
      exact: true,
    })
    .click();
  await expect(page.locator(".react-flow__node")).toHaveCount(7);
  expect(await executeAndInspect()).toEqual(firstRows);
  const monitor = page.getByRole("region", {
    name: "Run monitoring",
    exact: true,
  });
  await monitor
    .getByRole("button", { name: "Refresh runs", exact: true })
    .click();
  await monitor.getByRole("button", { name: /Inspect output/ }).click();
  await expect(
    monitor.getByRole("table", { name: "Parquet output rows" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Fit View", exact: true }).click();
  await page.locator(`.react-flow__node[data-id="${sql}"]`).click();
  await page
    .getByRole("region", { name: "Configure SQL Source", exact: true })
    .getByRole("textbox", { name: "Query", exact: true })
    .fill("SELECT asset_id, label FROM missing_table");
  await expect(runButton).toBeDisabled();
  await page
    .getByRole("button", { name: "Save pipeline", exact: true })
    .click();
  await expect(runButton).toBeEnabled();
  await runButton.click();
  const controls = page.getByLabel("Pipeline execution", { exact: true });
  await expect(
    controls.getByText("Run failed · revision 2", { exact: true }),
  ).toBeVisible();
  await expect(controls.getByText(/sql_query_failed/).first()).toBeVisible();
  await controls
    .getByRole("button", { name: `Configure failed block ${sql}`, exact: true })
    .click();
  const query = page
    .getByRole("region", { name: "Configure SQL Source", exact: true })
    .getByRole("textbox", { name: "Query", exact: true });
  await expect(query).toBeFocused();
  await query.fill(
    "SELECT asset_id, label FROM assets WHERE label IS NOT NULL ORDER BY asset_id",
  );
  await page
    .getByRole("button", { name: "Save pipeline", exact: true })
    .click();
  await expect(runButton).toBeEnabled();
  await runButton.click();
  await expect(
    controls.getByText("Run succeeded · revision 3", { exact: true }),
  ).toBeVisible();
  await controls.getByRole("button", { name: /Inspect output/ }).click();
  expect(await controls.getByRole("row").allTextContents()).toEqual([
    "labeltotal",
    "A30",
    "B50",
  ]);
  await testInfo.attach("release-success.png", {
    body: await page.screenshot({ fullPage: true }),
    contentType: "image/png",
  });
});
