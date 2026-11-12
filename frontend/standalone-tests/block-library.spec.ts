import { expect, test } from "@playwright/test";

test("the example is hidden but existing saved nodes remain editable", async ({
  page,
}) => {
  const api =
    process.env.LPS_STANDALONE_API_URL || "http://127.0.0.1:8000/api/v1";
  const projectResponse = await page.request.post(`${api}/projects`, {
    data: { name: `Existing example ${Date.now()}` },
  });
  expect(projectResponse.status()).toBe(201);
  const project = await projectResponse.json();
  const definition = {
    schema_version: 1,
    nodes: ["a", "b"].map((id) => ({
      id,
      block_id: "synthetic.add_constant",
      block_version: "1.0.0",
      config: { amount: 3 },
    })),
    edges: [
      {
        id: "ab",
        source: { node_id: "a", port: "table" },
        target: { node_id: "b", port: "table" },
      },
    ],
    layout: { positions: { a: { x: 0, y: 0 }, b: { x: 350, y: 0 } } },
  };
  const saved = await page.request.post(
    `${api}/projects/${project.id}/pipelines`,
    {
      data: { name: "Existing example", definition },
    },
  );
  expect(saved.status()).toBe(201);
  await page.goto(`/#/projects/${project.id}/builder`);
  await expect(
    page.getByRole("button", { name: "Add Row Count" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Add Synthetic Add Constant" }),
  ).toHaveCount(0);
  const search = page.getByRole("textbox", { name: "Search blocks" });
  await search.fill("synthetic");
  await expect(page.locator('[draggable="true"]')).toHaveCount(0);
  await search.clear();

  await page
    .getByRole("button", { name: "Open Existing example (revision 1)" })
    .click();
  const nodes = page.locator(".react-flow__node");
  await expect(nodes).toHaveCount(2);
  await expect(nodes.first()).toContainText("Synthetic Add Constant");
  await expect(page.locator(".react-flow__edge")).toHaveCount(1);
  await nodes.first().click({ position: { x: 10, y: 10 } });
  const amount = page.getByRole("spinbutton", { name: "Amount" });
  await expect(amount).toHaveValue("3");
  await amount.fill("4");
  // Validation still knows the hidden block and reports only its missing input.
  await expect(
    page.getByRole("status").filter({ hasText: /problem|Ready/ }),
  ).toHaveText("1 problem must be fixed before running.");
  const update = page.waitForResponse(
    (response) =>
      response.request().method() === "PUT" &&
      response.url().includes("/pipelines/"),
  );
  await page
    .getByRole("button", { name: "Save pipeline", exact: true })
    .click();
  const result = await (await update).json();
  expect(result.definition.nodes[0].config).toEqual({ amount: 4 });
  expect(result.definition.edges).toEqual(definition.edges);
  await expect(
    page.getByRole("button", { name: "Add Synthetic Add Constant" }),
  ).toHaveCount(0);
});
