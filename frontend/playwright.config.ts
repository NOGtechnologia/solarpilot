import { existsSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";

import { defineConfig, devices } from "@playwright/test";

const PORT = Number(process.env.E2E_PORT ?? 8799);
const backend = resolve(__dirname, "..", "backend");
const venvPy = [join(backend, ".venv", "Scripts", "python.exe"), join(backend, ".venv", "bin", "python")].find(existsSync);
const python = process.env.SP_PYTHON ?? venvPy ?? "python";
const dataDir = mkdtempSync(join(tmpdir(), "solarpilot-e2e-"));

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: "retain-on-failure",
    locale: "de-DE",
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] }, testMatch: /mobile\.spec\.ts/ },
  ],
  webServer: {
    command: `"${python}" -m uvicorn app.main:app --host 127.0.0.1 --port ${PORT}`,
    cwd: backend,
    url: `http://127.0.0.1:${PORT}/api/health`,
    reuseExistingServer: false,
    timeout: 60_000,
    env: {
      SOLARPILOT_DATA_DIR: dataDir,
      SOLARPILOT_STATIC_DIR: resolve(__dirname, "out"),
      SOLARPILOT_CONFIG_DIR: resolve(__dirname, "..", "config"),
      SOLARPILOT_SECRET_KEY: "e2e-test-secret",
      SOLARPILOT_POLL_INTERVAL_S: "2",
    },
  },
});
