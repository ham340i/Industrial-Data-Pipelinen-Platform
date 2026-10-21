import { expect, test } from "@playwright/test";

test("production shell supports keyboard navigation, drafts and direct links", async ({
  page,
}) => {
  await page.route("http://127.0.0.1:8000/api/v1/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  await page.goto("/");
  await expect(page.getByText("Local API is connected.")).toBeVisible();
  await page.keyboard.press("Tab");
  await expect(
    page.getByRole("link", { name: "Skip to main content" }),
  ).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("main")).toBeFocused();
  await page.getByRole("link", { name: "Builder", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Draft pipeline name" })
    .fill("Synthetic browser draft");
  await page.getByRole("link", { name: "Projects", exact: true }).click();
  await page.goBack();
  await expect(
    page.getByRole("textbox", { name: "Draft pipeline name" }),
  ).toHaveValue("Synthetic browser draft");
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Pipeline builder" }),
  ).toBeVisible();
  await expect(
    page.getByRole("textbox", { name: "Draft pipeline name" }),
  ).toHaveValue("");
});

test("offline health recovers and mobile shell does not overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.route("http://127.0.0.1:8000/api/v1/health", (route) =>
    route.abort(),
  );
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText(
    "Cannot reach the local API",
  );
  await page.unroute("http://127.0.0.1:8000/api/v1/health");
  await page.route("http://127.0.0.1:8000/api/v1/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByText("Local API is connected.")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "test-results/workbench-mobile.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.screenshot({
    path: "test-results/workbench-desktop.png",
    fullPage: true,
  });
});

test("real browser enforces the transport timeout", async ({ page }) => {
  await page.route("http://127.0.0.1:8000/api/v1/health", () => {
    /* Deliberately leave the synthetic request pending. */
  });
  await page.goto("/");
  await expect(page.getByRole("alert")).toContainText("took too long", {
    timeout: 15000,
  });
});

test("canvas supports keyboard add, move and delete", async ({ page }) => {
  await page.route("**/api/v1/health", (route) =>
    route.fulfill({ json: { status: "ok" } }),
  );
  await page.route("**/api/v1/blocks", (route) =>
    route.fulfill({
      json: [
        {
          sdk_version: 1,
          block_id: "synthetic.example",
          version: "1.0.0",
          name: "Example",
          category: "synthetic",
          inputs: [],
          outputs: [],
          config_schema: {},
        },
      ],
    }),
  );
  await page.goto("/#/builder");
  const add = page.getByRole("button", { name: "Add Example" });
  await add.focus();
  await page.keyboard.press("Enter");
  const node = page.locator(".react-flow__node");
  await expect(node).toHaveCount(1);
  await node.focus();
  const before = await node.getAttribute("style");
  await page.keyboard.press("ArrowRight");
  await expect(node).not.toHaveAttribute("style", before!);
  await page.keyboard.press("Delete");
  await expect(node).toHaveCount(0);
});
