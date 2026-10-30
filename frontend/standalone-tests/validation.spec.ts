import { expect, test } from "@playwright/test";

// Real API, no mocks (#21). Use the synthetic transform's required input to
// exercise invalid graphs. File-source catalog coverage is in file-blocks.spec.
test("real API diagnoses the draft, maps problems to nodes and gates running", async ({
  page,
}) => {
  await page.goto("/#/builder");
  const run = page.getByRole("button", { name: "Run pipeline" });
  const status = page.getByRole("status").filter({ hasText: /problem|Ready/ });
  await expect(status).toHaveText("1 problem must be fixed before running.");
  await expect(
    page.getByText("Add at least one block before running the pipeline."),
  ).toBeVisible();
  await expect(run).toBeDisabled();

  const add = page.getByRole("button", { name: "Add Synthetic Add Constant" });
  await add.click();
  await add.click();
  const nodes = page.locator(".react-flow__node");
  await expect(nodes).toHaveCount(2);
  const missing = "Connect an upstream output to the required input 'table'.";
  await expect(status).toHaveText("2 problems must be fixed before running.");
  await expect(nodes.first().getByText(missing)).toBeVisible();
  await expect(nodes.last().getByText(missing)).toBeVisible();
  await expect(run).toBeDisabled();
  const ids = await nodes.evaluateAll((all) =>
    all.map((n) => n.getAttribute("data-id")),
  );

  // Keyboard movement is independent of page scroll and the expanded library.
  // The old page-coordinate drag could leave the two nodes overlapping.
  await nodes.last().focus();
  for (let step = 0; step < 20; step++)
    await page.keyboard.press("Shift+ArrowRight");
  await page.getByRole("button", { name: "Fit View", exact: true }).click();

  // Fix the second node's input; only the first node still needs one.
  await nodes.first().locator(".source").click();
  await nodes.last().locator(".target").click();
  await expect(page.locator(".react-flow__edge")).toHaveCount(1);
  await expect(status).toHaveText("1 problem must be fixed before running.");
  await expect(nodes.first().getByText(missing)).toBeVisible();
  await expect(nodes.last().getByText(missing)).toHaveCount(0);
  await expect(run).toBeDisabled();
  // Showing diagnostics never replaced or reset the draft.
  expect(
    await nodes.evaluateAll((all) => all.map((n) => n.getAttribute("data-id"))),
  ).toEqual(ids);
});
