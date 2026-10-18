import { expect, test, type Page } from "@playwright/test";

// Test-Zugangsdaten nur für die frische E2E-Datenbank
const USER = "e2e-admin";
const PASS = `e2e-${Date.now()}`;

test.describe.configure({ mode: "serial" });

async function login(page: Page) {
  await page.goto("/login/");
  await page.getByLabel("Benutzername").fill(USER);
  await page.getByLabel("Passwort").fill(PASS);
  await page.getByRole("button", { name: /Anmelden|Konto anlegen/ }).click();
  await expect(page).toHaveURL(/\/$/);
}

test("Ersteinrichtung: Admin anlegen, Leerzustand mit Demo-Button", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login\/$/);
  await expect(page.getByRole("heading", { name: "Willkommen bei SolarPilot" })).toBeVisible();
  await page.getByLabel("Benutzername").fill(USER);
  await page.getByLabel("Passwort").fill(PASS);
  await page.getByRole("button", { name: "Konto anlegen" }).click();
  await expect(page.getByRole("heading", { name: "Noch keine Anlage?" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Demo starten" })).toBeVisible();
});

test("Demo starten zeigt Energiefluss, Kennzahlen und Verlauf", async ({ page }) => {
  await login(page);
  await page.getByRole("button", { name: "Demo starten" }).click();
  await expect(page.getByText("Solarleistung jetzt")).toBeVisible({ timeout: 30_000 });
  await expect(page.getByRole("img", { name: /Energiefluss/ })).toBeVisible();
  await expect(page.getByText("Eigenverbrauch").first()).toBeVisible();
  await expect(page.getByText("Autarkie").first()).toBeVisible();
  await expect(page.getByRole("tab", { name: "Woche" })).toBeVisible();
  // Live-Verbindung per WebSocket
  await expect(page.getByText("Live", { exact: true })).toBeVisible({ timeout: 20_000 });
  // Gerätestatus
  await expect(page.getByText("Demo-Wechselrichter")).toBeVisible();
});

test("Verlauf: Monats- und Jahresansicht", async ({ page }) => {
  await login(page);
  await page.getByRole("tab", { name: "Monat" }).click();
  await expect(page.getByRole("img", { name: /Wie war heute/ })).toBeVisible();
  await page.getByRole("tab", { name: "Jahr" }).click();
  await expect(page.getByRole("img", { name: /Wie war heute/ })).toBeVisible();
});

test("Sprache wechseln", async ({ page }) => {
  await login(page);
  await page.getByRole("button", { name: "Sprache wechseln" }).click();
  await expect(page.getByText("Solar power now")).toBeVisible();
  await page.getByRole("button", { name: "Change language" }).click();
  await expect(page.getByText("Solarleistung jetzt")).toBeVisible();
});

test("Prognose- und Berichtsseite laden", async ({ page }) => {
  await login(page);
  await page.getByRole("link", { name: "Prognose" }).first().click();
  await expect(page.getByRole("heading", { name: "Prognose", exact: true })).toBeVisible();
  await page.getByRole("link", { name: "Berichte" }).first().click();
  await expect(page.getByRole("heading", { name: "Monatsbericht" })).toBeVisible();
  const pdf = page.getByRole("link", { name: "Als PDF" });
  const href = await pdf.getAttribute("href");
  const res = await page.request.get(href!);
  expect(res.ok()).toBeTruthy();
  expect((await res.body()).subarray(0, 4).toString()).toBe("%PDF");
});

test("Einstellungen: Tarif speichern", async ({ page }) => {
  await login(page);
  await page.goto("/settings/#tariff");
  const buy = page.getByLabel("Strompreis (€/kWh)");
  await buy.fill("0.35");
  await page.getByRole("button", { name: "Speichern" }).click();
  await expect(page.getByRole("status")).toHaveText("Gespeichert");
  const res = await page.request.get("/api/settings/tariff");
  expect((await res.json()).buy_eur_kwh).toBe(0.35);
});

test("Assistent: Hersteller wählen und Verbindung testen", async ({ page }) => {
  await login(page);
  await page.goto("/setup/");
  await page.getByLabel("Name der Anlage").fill("Testhaus");
  await page.getByRole("button", { name: "Weiter" }).click();
  await page.getByPlaceholder("Hersteller filtern").fill("Demo");
  await page.getByRole("button", { name: /Demo-Simulator/ }).click();
  await page.getByRole("button", { name: "Verbindung testen" }).click();
  await expect(page.getByText("Verbindung erfolgreich")).toBeVisible({ timeout: 20_000 });
  await page.getByRole("button", { name: "Weiter" }).click();
  await page.getByRole("button", { name: "Anlage speichern" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("tab", { name: "Alle Anlagen" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Testhaus" })).toBeVisible();
});

test("API ist ohne Login geschützt", async ({ request }) => {
  const res = await request.get("/api/sites", { headers: { cookie: "" } });
  expect(res.status()).toBe(401);
});
