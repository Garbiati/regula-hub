import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  // Mock API calls so we don't need a real backend
  await page.route("**/health", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok" }),
    }),
  );
  await page.route("**/api/admin/**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [], total: 0 }),
    }),
  );
});

test("sidebar renders main nav items", async ({ page }) => {
  await page.goto("/");
  await page.waitForLoadState("networkidle");

  const sidebar = page.locator("aside");
  await expect(sidebar.getByText("Dashboard")).toBeVisible();
  await expect(sidebar.getByText("Settings")).toBeVisible();
});

test("navigate to Settings page", async ({ page }) => {
  await page.goto("/");
  await page.waitForLoadState("networkidle");

  await page.locator("aside").getByText("Settings").click();
  await expect(page).toHaveURL("/settings");
  await expect(page.getByRole("heading", { name: /Settings|Configurações/ })).toBeVisible();
});
