import { expect, test } from "@playwright/test";

test("real SDK config survives selection, failed copy, export and API save/reopen", async ({
  page,
}) => {
  await page.goto("/#/projects");
  await page
    .getByRole("textbox", { name: "Project name" })
    .fill(`Config check ${Date.now()}`);
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Pipeline builder" }),
  ).toBeVisible();
  await page
    .getByRole("textbox", { name: "Draft pipeline name" })
    .fill("Configuration roundtrip");
  const add = page.getByRole("button", { name: "Add Synthetic Add Constant" });
  const amount = page.getByRole("spinbutton", { name: "Amount" });
  const nodes = page.locator(".react-flow__node");
  await add.click();
  await amount.fill("42");
  await add.click();
  await amount.fill("7");
  // Keep both real canvas nodes selectable after save/reopen. The builder's
  // initial positions deliberately overlap; use its keyboard movement controls.
  await nodes.last().focus();
  for (let step = 0; step < 20; step++)
    await page.keyboard.press("Shift+ArrowRight");
  await page.getByRole("button", { name: "Fit View", exact: true }).click();
  await nodes.first().click({ position: { x: 10, y: 10 } });
  await expect(amount).toHaveValue("42");
  const validation = page.waitForResponse(
    (r) =>
      r.url().endsWith("/pipelines/validate") &&
      r.request().method() === "POST" &&
      r
        .request()
        .postDataJSON()
        ?.definition.nodes.some(
          (n: { config: { amount?: number } }) => n.config.amount === 1001,
        ),
  );
  await amount.fill("1001");
  expect((await (await validation).json()).diagnostics).toEqual(
    expect.arrayContaining([
      expect.objectContaining({ code: "invalid_config", field: "amount" }),
    ]),
  );
  await expect(amount).toHaveAttribute("aria-invalid", "true");
  await expect(page.getByText(/Use a value of at most 1000/)).toBeVisible();
  await amount.fill("42");
  const save = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/pipelines"),
  );
  await page
    .getByRole("button", { name: "Save pipeline", exact: true })
    .click();
  const saved = await (await save).json();
  expect(
    saved.definition.nodes.map((n: { config: unknown }) => n.config),
  ).toEqual([{ amount: 42 }, { amount: 7 }]);
  await expect(page.getByText("Pipeline saved.")).toBeVisible();
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export JSON", exact: true }).click();
  const exported = await download;
  const file = await exported.path();
  const fs = await import("node:fs/promises");
  expect(JSON.parse(await fs.readFile(file!, "utf8"))).toEqual(
    saved.definition,
  );
  await page.reload();
  await page
    .getByRole("button", { name: "Open Configuration roundtrip (revision 1)" })
    .click();
  await nodes.first().click({ position: { x: 10, y: 10 } });
  await expect(amount).toHaveValue("42");
  await amount.fill("43");
  const conflict = page.waitForResponse(
    (r) => r.request().method() === "POST" && r.url().endsWith("/pipelines"),
  );
  await page.getByRole("button", { name: "Save a copy", exact: true }).click();
  expect((await conflict).status()).toBe(409);
  await expect(amount).toHaveValue("43");
  await nodes.last().click({ position: { x: 10, y: 10 } });
  await expect(amount).toHaveValue("7");

  // A column flex layout must retain the canvas height on narrow screens.
  await page.setViewportSize({ width: 390, height: 844 });
  const canvas = page.getByLabel("Pipeline canvas", { exact: true });
  expect((await canvas.boundingBox())?.height).toBeGreaterThanOrEqual(560);
  await page.getByRole("button", { name: "Fit View", exact: true }).click();
  await nodes.first().click({ position: { x: 10, y: 10 } });
  await expect(amount).toHaveValue("43");
  await amount.fill("44");
  await nodes.last().click({ position: { x: 10, y: 10 } });
  await expect(amount).toHaveValue("7");
  await nodes.first().click({ position: { x: 10, y: 10 } });
  await expect(amount).toHaveValue("44");
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
