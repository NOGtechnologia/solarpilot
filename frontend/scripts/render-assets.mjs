// Erzeugt PWA-Icons, Screenshots und das GitHub-Social-Preview-Bild mit Playwright.
//   node scripts/render-assets.mjs icons
//   SP_URL=http://localhost:8000 SP_USER=admin SP_PASS=... node scripts/render-assets.mjs screenshots
import { readFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const repo = join(root, "..");
const svg = readFileSync(join(root, "public", "favicon.svg"), "utf8");
const mode = process.argv[2] ?? "icons";

const browser = await chromium.launch();

async function renderSvg(file, size, padding = 0, bg = "transparent") {
  const page = await browser.newPage({ viewport: { width: size, height: size } });
  const inner = size - padding * 2;
  await page.setContent(
    `<html><body style="margin:0;background:${bg};display:flex;align-items:center;justify-content:center;width:${size}px;height:${size}px">
     <div style="width:${inner}px;height:${inner}px">${svg.replace("<svg ", `<svg width="${inner}" height="${inner}" `)}</div></body></html>`,
  );
  await page.screenshot({ path: file, omitBackground: bg === "transparent" });
  await page.close();
}

if (mode === "icons") {
  const dir = join(root, "public", "icons");
  mkdirSync(dir, { recursive: true });
  await renderSvg(join(dir, "icon-192.png"), 192);
  await renderSvg(join(dir, "icon-512.png"), 512);
  await renderSvg(join(dir, "icon-maskable-512.png"), 512, 64, "#0B0F14");
  await renderSvg(join(dir, "apple-touch-icon.png"), 180, 0, "#0B0F14");
  console.log("Icons erzeugt in", dir);
}

if (mode === "screenshots") {
  const url = process.env.SP_URL ?? "http://localhost:8000";
  const out = join(repo, "docs", "images");
  mkdirSync(out, { recursive: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1, colorScheme: "dark" });
  const res = await ctx.request.post(`${url}/api/auth/login`, {
    data: { username: process.env.SP_USER, password: process.env.SP_PASS },
  });
  if (!res.ok()) throw new Error(`Login fehlgeschlagen: ${res.status()}`);
  await ctx.addInitScript(() => {
    localStorage.setItem("sp_lang", "de");
    localStorage.setItem("theme", "dark");
  });
  const page = await ctx.newPage();
  const shot = async (path, name, opts = {}) => {
    await page.goto(`${url}${path}`);
    await page.waitForTimeout(6000);
    await page.screenshot({ path: join(out, name), ...opts });
  };
  await shot("/", "dashboard-dark.png");
  await shot("/forecast/", "forecast-dark.png");
  await shot("/reports/", "reports-dark.png");
  await ctx.addInitScript(() => localStorage.setItem("theme", "light"));
  await page.setViewportSize({ width: 390, height: 844 });
  await shot("/", "dashboard-mobile-light.png");
  await page.setViewportSize({ width: 1440, height: 1000 });
  await shot("/", "dashboard-light.png");

  // Social Preview 1280×640
  const hero = readFileSync(join(out, "dashboard-dark.png")).toString("base64");
  const sp = await browser.newPage({ viewport: { width: 1280, height: 640 } });
  await sp.setContent(`<html><body style="margin:0;width:1280px;height:640px;overflow:hidden;background:#0B0F14;font-family:Inter,Segoe UI,system-ui,sans-serif;color:#EEF2F7">
    <div style="position:absolute;inset:0;background:radial-gradient(80% 90% at 10% 0%,rgba(245,165,36,.35),transparent 60%),radial-gradient(70% 80% at 100% 100%,rgba(139,92,246,.25),transparent 60%)"></div>
    <div style="position:absolute;left:64px;top:72px;width:470px">
      <div style="width:84px;height:84px">${svg.replace("<svg ", '<svg width="84" height="84" ')}</div>
      <h1 style="font-size:64px;margin:28px 0 8px;letter-spacing:-.03em">SolarPilot</h1>
      <p style="font-size:26px;line-height:1.35;color:#C9D2DE;margin:0">Open-Source-Dashboard für PV-Anlagen aller Hersteller</p>
      <p style="font-size:19px;line-height:1.5;color:#95A1B2;margin-top:26px">Live-Energiefluss · PV-Prognose · Strompreise · Tipps<br/>SMA · Fronius · SolarEdge · Huawei · Victron · OpenDTU</p>
      <p style="font-size:18px;color:#F5A524;margin-top:30px;font-family:ui-monospace,Consolas,monospace">$ docker compose up</p>
    </div>
    <img src="data:image/png;base64,${hero}" style="position:absolute;left:580px;top:70px;width:900px;border-radius:18px;border:1px solid #222C39;box-shadow:0 30px 80px rgba(0,0,0,.5)"/>
  </body></html>`);
  await sp.screenshot({ path: join(out, "social-preview.png") });
  console.log("Screenshots erzeugt in", out);
}

await browser.close();
