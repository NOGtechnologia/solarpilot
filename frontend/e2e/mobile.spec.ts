import { expect, test } from "@playwright/test";

test("Mobil: Login-Seite ohne horizontales Scrollen, Bedienelemente erreichbar", async ({ page }) => {
  await page.goto("/login/");
  await expect(page.getByRole("button", { name: /Anmelden|Konto anlegen/ })).toBeVisible();
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(0);
});
