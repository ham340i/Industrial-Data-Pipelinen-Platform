import { expect, test } from "@playwright/test";

test("all nine real file/column block schemas configure and persist", async ({
  page,
}) => {
  await page.goto("/#/projects");
  await page
    .getByRole("textbox", { name: "Project name" })
    .fill(`File blocks ${Date.now()}`);
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Pipeline builder" }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Draft pipeline name" })
    .fill("Nine registered blocks");
  const cases = [
    {
      name: "CSV Source",
      id: "source.csv",
      fields: { "Resource Ref": "inputs/data.csv" },
    },
    {
      name: "JSON Source",
      id: "source.json",
      fields: { "Resource Ref": "inputs/data.json" },
    },
    {
      name: "Parquet Source",
      id: "source.parquet",
      fields: { "Resource Ref": "inputs/data.parquet" },
    },
    {
      name: "Select Columns",
      id: "transform.select",
      fields: { Columns: '["sensor","reading"]' },
    },
    {
      name: "Rename Columns",
      id: "transform.rename",
      fields: { Columns: '["reading"]', Names: '["value"]' },
    },
    {
      name: "Filter",
      id: "transform.filter",
      fields: { Column: "value", "Value Text": "0" },
    },
    { name: "Cast", id: "transform.cast", fields: { Column: "value" } },
    {
      name: "CSV Sink",
      id: "sink.csv",
      fields: { "Resource Ref": "outputs/result.csv" },
    },
    {
      name: "Parquet Sink",
      id: "sink.parquet",
      fields: { "Resource Ref": "outputs/result.parquet" },
    },
  ];
  for (const item of cases) {
    await page
      .getByRole("button", { name: `Add ${item.name}`, exact: true })
      .click();
    const form = page.getByRole("region", {
      name: `Configure ${item.name}`,
      exact: true,
    });
    await expect(form).toBeVisible();
    for (const [label, value] of Object.entries(item.fields))
      await form.getByRole("textbox", { name: label, exact: true }).fill(value);
    if (item.id === "transform.cast")
      await form
        .getByRole("combobox", { name: "Dtype", exact: true })
        .selectOption({ label: "number" });
    await expect(
      page.getByText(/unsupported or unsafe configuration schema/),
    ).toHaveCount(0);
  }
  const response = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/pipelines"),
  );
  await page
    .getByRole("button", { name: "Save pipeline", exact: true })
    .click();
  const saved = await (await response).json();
  const configs = Object.fromEntries(
    saved.definition.nodes.map(
      (node: { block_id: string; config: unknown }) => [
        node.block_id,
        node.config,
      ],
    ),
  );
  expect(Object.keys(configs).sort()).toEqual(
    cases.map((item) => item.id).sort(),
  );
  expect(configs["source.csv"]).toMatchObject({
    resource_ref: "inputs/data.csv",
    encoding: "utf-8",
  });
  expect(configs["transform.select"]).toEqual({
    columns: ["sensor", "reading"],
  });
  expect(configs["transform.rename"]).toEqual({
    columns: ["reading"],
    names: ["value"],
  });
  expect(configs["transform.cast"]).toMatchObject({
    column: "value",
    dtype: "number",
    on_error: "error",
  });
  expect(configs["sink.parquet"]).toMatchObject({
    resource_ref: "outputs/result.parquet",
    overwrite: "error",
  });
  await expect(page.getByText("Pipeline saved.")).toBeVisible();
  await page.reload();
  await page
    .getByRole("button", { name: "Open Nine registered blocks (revision 1)" })
    .click();
  await expect(page.locator(".react-flow__node")).toHaveCount(9);
});
