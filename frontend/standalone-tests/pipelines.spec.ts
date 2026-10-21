import { expect, test } from "@playwright/test";

test("real API saves and reloads the canvas, then renames the pipeline", async ({
  page,
}) => {
  await page.goto("/#/projects");
  await page
    .getByRole("textbox", { name: "Project name" })
    .fill(`Pipeline roundtrip ${Date.now()}`);
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Pipeline builder" }),
  ).toBeVisible();
  const name = page.getByRole("textbox", { name: "Draft pipeline name" });
  await name.fill("Synthetic pipeline");
  await page
    .getByRole("button", { name: "Add Synthetic Add Constant" })
    .click();
  const nodes = page.locator(".react-flow__node");
  const node = nodes.first();
  await expect(node).toHaveCount(1);
  const originalId = await node.getAttribute("data-id");
  await node.focus();
  await page.keyboard.press("ArrowRight");
  const canvas = page.getByLabel("Pipeline canvas");
  await canvas.scrollIntoViewIfNeeded();
  // Fit/measurements and font metrics vary across browsers. Drop relative to
  // the rendered node, not fixed canvas coordinates that can overlap a handle.
  await page.getByRole("button", { name: "Zoom Out", exact: true }).click();
  await page.getByRole("button", { name: "Zoom Out", exact: true }).click();
  await node.locator(".source").click({ trial: true });
  const firstBox = await node.boundingBox();
  const canvasBox = await canvas.boundingBox();
  const dropX = firstBox!.x + firstBox!.width + 40;
  expect(dropX).toBeLessThan(canvasBox!.x + canvasBox!.width);

  const dragData = await page.evaluateHandle(() => new DataTransfer());
  const entry = page.locator('[draggable="true"]').filter({
    has: page.getByRole("button", { name: "Add Synthetic Add Constant" }),
  });
  await entry.dispatchEvent("dragstart", { dataTransfer: dragData });
  await canvas.dispatchEvent("drop", {
    dataTransfer: dragData,
    clientX: dropX,
    clientY: firstBox!.y,
  });
  await expect(nodes).toHaveCount(2);
  await page.getByRole("button", { name: "Fit View", exact: true }).click();
  await node.locator(".source").click();
  await nodes.last().locator(".target").click();
  await expect(page.locator(".react-flow__edge")).toHaveCount(1);
  const saveResponse = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/pipelines"),
  );
  await page
    .getByRole("button", { name: "Save pipeline", exact: true })
    .click();
  const saved = await (await saveResponse).json();
  await expect(page.getByText("Pipeline saved.")).toBeVisible();
  expect(saved.definition.edges).toHaveLength(1);
  expect(saved.definition.nodes[0].config).toEqual({ amount: 1 });
  await page.reload();
  await expect(nodes).toHaveCount(0);
  await page
    .getByRole("button", { name: "Open Synthetic pipeline (revision 1)" })
    .click();
  await expect(node).toHaveAttribute("data-id", originalId!);
  await name.fill("Renamed pipeline");
  const updateResponse = page.waitForResponse(
    (r) => r.request().method() === "PUT" && r.url().includes("/pipelines/"),
  );
  await page
    .getByRole("button", { name: "Save pipeline", exact: true })
    .click();
  const updated = await (await updateResponse).json();
  expect(updated.definition).toEqual(saved.definition);
  await expect(page.getByText("Revision 2 · Saved")).toBeVisible();
  await page.reload();
  await page
    .getByRole("button", { name: "Open Renamed pipeline (revision 2)" })
    .click();
  await expect(name).toHaveValue("Renamed pipeline");
  await expect(nodes).toHaveCount(2);
  await expect(page.locator(".react-flow__edge")).toHaveCount(1);
  await expect(node).toHaveAttribute("data-id", originalId!);
});
