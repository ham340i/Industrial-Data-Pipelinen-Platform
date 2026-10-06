import { expect, test, type Response } from "@playwright/test";

test("default standalone workbench connects to the real versioned API", async ({
  page,
  baseURL,
}) => {
  const healthUrl = "http://127.0.0.1:8000/api/v1/health";
  let healthResponse: Response | undefined;
  page.on("response", (response) => {
    if (response.url() === healthUrl) healthResponse = response;
  });
  await page.goto("/");
  await expect(page.getByText("Local API is connected.")).toBeVisible({
    timeout: 10000,
  });
  expect(healthResponse).toBeDefined();
  const response = healthResponse!;
  expect(response.status()).toBe(200);
  expect(await response.json()).toMatchObject({ status: "ok" });
  expect(response.headers()["access-control-allow-origin"]).toBe(
    new URL(baseURL!).origin,
  );
  await page.screenshot({
    path: "test-results/standalone-connected.png",
    fullPage: true,
  });
  await page.getByRole("link", { name: "Builder", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Pipeline builder" }),
  ).toBeVisible();
});
