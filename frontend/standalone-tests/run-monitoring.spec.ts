// AI contribution: 50% or more AI-generated
import { expect, test } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

test("real execute/status/detail evidence stays isolated and preserves the draft", async ({
  page,
  request,
}) => {
  const base =
    process.env.LPS_STANDALONE_API_URL || "http://127.0.0.1:8000/api/v1";
  const projectResponse = await request.post(`${base}/projects`, {
    data: { name: `Run monitor ${Date.now()}` },
  });
  expect(projectResponse.status()).toBe(201);
  const project = await projectResponse.json();
  const path = `${base}/projects/${project.id}/pipelines`;
  const definition = {
    schema_version: 1,
    nodes: [
      {
        id: "manual",
        block_id: "trigger.manual",
        block_version: "1.0.0",
        config: {},
      },
    ],
    edges: [],
  };
  const savedResponse = await request.post(path, {
    data: { name: "Monitor success", definition },
  });
  expect(savedResponse.status()).toBe(201);
  const saved = await savedResponse.json();
  await page.goto(`/#/projects/${project.id}/builder`);
  await page
    .getByRole("button", { name: "Open Monitor success (revision 1)" })
    .click();
  const monitor = page.getByRole("region", {
    name: "Run monitoring",
    exact: true,
  });
  await expect(monitor.getByText(/No runs yet/)).toBeVisible();
  const execution = await request.post(`${path}/${saved.id}/execute`);
  expect(execution.status()).toBe(201);
  const success = await execution.json();
  expect(success.state).toBe("succeeded");
  await expect(
    monitor.getByText(`Completed · Run ${success.run_id}`),
  ).toBeVisible();
  await expect(
    monitor.getByRole("region", { name: "Block manual" }),
  ).toHaveCount(0);
  await page
    .getByRole("textbox", { name: "Draft pipeline name" })
    .fill("Keep my unsaved edit");
  await expect(
    monitor.getByRole("button", { name: "Download log", exact: true }),
  ).toHaveCount(1);
  await expect(
    page.getByRole("textbox", { name: "Draft pipeline name" }),
  ).toHaveValue("Keep my unsaved edit");
  const failedResponse = await request.post(path, {
    data: {
      name: "Monitor failure",
      definition: {
        schema_version: 1,
        nodes: [
          {
            id: "source",
            block_id: "source.csv",
            block_version: "1.0.0",
            config: { resource_ref: "missing-monitor-input.csv" },
          },
          {
            id: "select",
            block_id: "transform.select",
            block_version: "1.0.0",
            config: { columns: ["sensor", "reading"] },
          },
          {
            id: "sink",
            block_id: "sink.parquet",
            block_version: "1.0.0",
            config: { resource_ref: "result.parquet", overwrite: "replace" },
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
      },
    },
  });
  expect(failedResponse.status()).toBe(201);
  const failedPipeline = await failedResponse.json();
  const failureExecution = await request.post(
    `${path}/${failedPipeline.id}/execute`,
  );
  expect(failureExecution.status()).toBe(201);
  const failure = await failureExecution.json();
  expect(failure.state).toBe("failed");
  await page.reload();
  await page
    .getByRole("button", { name: "Open Monitor failure (revision 1)" })
    .click();
  await expect(
    monitor.getByText(`Failed · Run ${failure.run_id}`),
  ).toBeVisible();
  await expect(
    monitor.getByText(`Completed · Run ${success.run_id}`),
  ).toHaveCount(0);
  await expect(
    monitor.getByRole("region", { name: "Block select" }),
  ).toHaveCount(0);
  await expect(monitor.getByRole("region", { name: "Block sink" })).toHaveCount(
    0,
  );
  const failedDetail = await request.get(`${base}/runs/${failure.run_id}`);
  expect((await failedDetail.json()).outputs).toEqual([]);
  await page
    .getByRole("textbox", { name: "Draft pipeline name" })
    .fill("Recovered pipeline");
  await monitor
    .getByRole("button", { name: "Configure failed block source", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("region", { name: "Configure CSV Source" }),
  ).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Resource Ref" })).toHaveValue(
    "missing-monitor-input.csv",
  );
  await expect(
    page.getByRole("textbox", { name: "Draft pipeline name" }),
  ).toHaveValue("Recovered pipeline");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/run-monitor-failure.png",
    fullPage: true,
  });
  const inputs = join(
    process.env.LPS_WORKSPACE_ROOT!,
    project.name,
    "Monitor failure",
    "inputs",
  );
  mkdirSync(inputs, { recursive: true });
  writeFileSync(join(inputs, "recovered.csv"), "sensor,reading\nA,10\nB,20\n");
  await page
    .getByRole("textbox", { name: "Resource Ref", exact: true })
    .fill("inputs/recovered.csv");
  await page
    .getByRole("button", { name: "Save pipeline", exact: true })
    .click();
  await expect(
    page.getByText("Pipeline saved.", { exact: true }),
  ).toBeVisible();
  const recoveredRequest = page.waitForResponse(
    (response) =>
      response.request().method() === "POST" &&
      response.url().endsWith("/execute"),
  );
  await page
    .getByRole("button", { name: "Run saved pipeline", exact: true })
    .click();
  const recovered = await (await recoveredRequest).json();
  expect(recovered.state).toBe("succeeded");
  expect(recovered.run_id).not.toBe(failure.run_id);
  await expect(
    page
      .getByLabel("Pipeline execution", { exact: true })
      .getByText("artifact · 2 rows · result.parquet", { exact: true }),
  ).toBeVisible();
  const recoveredDetail = await request.get(`${base}/runs/${recovered.run_id}`);
  const evidence = await recoveredDetail.json();
  expect(evidence.revision).toBe(2);
  expect(
    evidence.blocks.every(
      (block: { state: string }) => block.state === "completed",
    ),
  ).toBe(true);
  expect(evidence.outputs).toHaveLength(1);
  await monitor
    .getByRole("button", { name: "Refresh runs", exact: true })
    .click();
  await monitor.getByLabel("Selected run").selectOption(failure.run_id);
  await expect(
    monitor.getByText(`Failed · Run ${failure.run_id}`),
  ).toBeVisible();
});
