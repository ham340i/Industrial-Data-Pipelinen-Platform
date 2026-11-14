import { expect, test } from "@playwright/test";

test("real execute/status/detail evidence stays isolated and preserves the draft", async ({
  page,
  request,
}) => {
  const base = "http://127.0.0.1:8000/api/v1";
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
  ).toContainText("Completed");
  await page
    .getByRole("textbox", { name: "Draft pipeline name" })
    .fill("Keep my unsaved edit");
  await monitor
    .getByRole("button", { name: "Inspect manual", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("region", { name: "Configure Manual Trigger" }),
  ).toBeVisible();
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
        ],
        edges: [],
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
  await monitor
    .getByRole("button", { name: "Inspect source", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("region", { name: "Configure CSV Source" }),
  ).toBeVisible();
  await expect(page.getByRole("textbox", { name: "Resource Ref" })).toHaveValue(
    "missing-monitor-input.csv",
  );
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
});
