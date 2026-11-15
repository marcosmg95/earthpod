import { defineConfig, devices } from "@playwright/test";

const CI = !!process.env.CI;

/** Builds the app, serves it like production and runs the end-to-end tests against it. */
export default defineConfig({
  testDir: "e2e",
  timeout: 30_000,
  retries: CI ? 1 : 0,
  reporter: CI ? [["github"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: "http://localhost:4173",
    // the app follows the system setting: no animations to wait for, and the reduced-motion path gets tested
    reducedMotion: "reduce",
    trace: "retain-on-failure",
    launchOptions: { args: ["--autoplay-policy=no-user-gesture-required"] },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    command: "npm run build && npm run preview -- --port 4173 --strictPort",
    url: "http://localhost:4173",
    reuseExistingServer: !CI,
    timeout: 120_000,
  },
});
