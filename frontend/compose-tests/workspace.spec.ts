import { expect, test } from "@playwright/test";

test("built shell connects to the real API and supports direct navigation", async ({
  page,
}) => {
  const response = await page.request.get("/api/v1/health");
  expect(response.ok()).toBe(true);
  expect(await response.json()).toMatchObject({
    status: "ok",
    service: "local-pipeline-studio",
  });
  await page.goto("/");
  await expect(page.getByText("Local API is connected.")).toBeVisible();
  await page.goto("/#/builder");
  await expect(
    page.getByRole("heading", { name: "Pipeline builder" }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Pipeline builder" }),
  ).toBeVisible();
});

test("create, reopen and restore a project through the real UI and API", async ({
  page,
  browser,
  baseURL,
}) => {
  const name = `Synthetic project ${Date.now()}`;
  await page.goto("/#/projects");
  await page.getByRole("textbox", { name: "Project name" }).fill(name);
  await page
    .getByRole("button", { name: "Create project", exact: true })
    .click();
  await expect(
    page.getByText(`Project: ${name}`, { exact: true }),
  ).toBeVisible();
  await expect(page).toHaveURL(/#\/projects\/[0-9a-f-]+\/builder$/);
  await page.screenshot({
    path: "test-results/project-workspace.png",
    fullPage: true,
  });
  await page
    .getByRole("textbox", { name: "Draft pipeline name" })
    .fill("Unsaved synthetic draft");
  await page.reload();
  await expect(
    page.getByText(`Project: ${name}`, { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("textbox")).toHaveValue("");
  await page.getByRole("link", { name: "Projects", exact: true }).click();
  const open = page.getByRole("link", { name: `Open ${name}`, exact: true });
  await expect(open).toBeVisible();
  await open.focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByText(`Project: ${name}`, { exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("main")).toBeFocused();
  await expect
    .poll(() =>
      page.evaluate(() =>
        Object.keys(localStorage).some((key) =>
          key.startsWith("lps.selected-project:"),
        ),
      ),
    )
    .toBe(true);
  const state = await page.context().storageState();
  const reopened = await browser.newContext({ baseURL, storageState: state });
  try {
    const restored = await reopened.newPage();
    await restored.goto("/#/builder");
    await expect(
      restored.getByText(`Project: ${name}`, { exact: true }),
    ).toBeVisible();
  } finally {
    await reopened.close();
  }
  const longName = "X".repeat(128);
  const response = await page.request.post("/api/v1/projects", {
    data: { name: longName },
  });
  expect(response.ok()).toBe(true);
  const longProject = (await response.json()) as { id: string };
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`/#/projects/${longProject.id}/builder`);
  await expect(
    page.getByText(`Project: ${longName}`, { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("link", { name: "Projects", exact: true }).click();
  await expect(
    page.getByRole("link", { name: `Open ${longName}`, exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
