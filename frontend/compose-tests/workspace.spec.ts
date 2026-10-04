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
