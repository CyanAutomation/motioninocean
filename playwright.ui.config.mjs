import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "tests/ui",
  timeout: 30_000,
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  retries: 0,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:8000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "webkit-desktop",
      use: {
        ...devices["Desktop Safari"],
        viewport: { width: 1440, height: 1024 },
      },
    },
  ],
  webServer: {
    command:
      "MOCK_CAMERA=true MIO_APP_MODE=webcam MOTION_IN_OCEAN_BIND_HOST=127.0.0.1 python3 -m pi_camera_in_docker.main",
    url: "http://127.0.0.1:8000/health",
    timeout: 120_000,
    reuseExistingServer: !process.env.CI,
  },
});
