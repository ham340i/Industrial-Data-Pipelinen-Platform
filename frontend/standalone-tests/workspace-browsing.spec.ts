// AI contribution: 50% or more AI-generated
import { expect, test } from "@playwright/test";
import { mkdir, stat } from "node:fs/promises";
import { dirname, join } from "node:path";

// Stub only the OS dialog boundary; workspace saving uses the real API.
// Native Windows dialog behavior is verified separately on the desktop.
test("uses native picker results, preserves cancellation, and persists the saved workspace", async ({
  page,
}) => {
  const api =
    process.env.LPS_STANDALONE_API_URL || "http://127.0.0.1:8000/api/v1";
  const root = process.env.LPS_WORKSPACE_ROOT!;
  const selected = join(dirname(root), `Native workspace ${Date.now()}`);
  await mkdir(selected, { recursive: true });
  const projectResponse = await page.request.post(`${api}/projects`, {
    data: { name: "Native folder selection verification" },
  });
  expect(projectResponse.status()).toBe(201);
  const project = await projectResponse.json();
  let pickerCalls = 0;
  await page.route("**/settings/workspace/pick-folder", async (route) => {
    expect(route.request().method()).toBe("POST");
    expect(route.request().postDataJSON()).toEqual({ initial_path: root });
    pickerCalls += 1;
    await route.fulfill({
      json: { path: pickerCalls === 1 ? null : selected },
    });
  });
  await page.goto("/#/settings/workspace");
  const field = page.getByRole("textbox", { name: "Workspace root folder" });
  const browse = page.getByRole("button", { name: /Browse/ });
  await expect(field).toHaveValue(root);
  await browse.click();
  await expect(browse).toBeEnabled();
  await expect(field).toHaveValue(root);
  await browse.click();
  await expect(field).toHaveValue(selected);
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(
    (await (await page.request.get(`${api}/settings/workspace`)).json())
      .root_path,
  ).toBe(root);
  await page
    .getByRole("button", { name: "Save workspace", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("Workspace saved");
  expect((await stat(join(selected, project.id, "inputs"))).isDirectory()).toBe(
    true,
  );
  await page.reload();
  await expect(field).toHaveValue(selected);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
