import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '.',
  testMatch: 'a11y.spec.mjs',
  timeout: 60000,
  use: {
    headless: true,
  },
});
