import { test, expect } from '@playwright/test';

test('homepage and mobile layout preserve original artwork and usable navigation', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Intelligence behind every trade/ })).toBeVisible();
  await expect(page.getByAltText(/GNK ALGO bull and bear artwork/)).toBeVisible();
  await page.screenshot({ path: 'test-results/home-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('link', { name: /Open your workspace/ })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.screenshot({ path: 'test-results/home-mobile.png', fullPage: true });
});

test('login password visibility and recovery links work', async ({ page }) => {
  await page.goto('/login');
  const password = page.getByLabel('Password', { exact: true });
  await expect(password).toHaveAttribute('type', 'password');
  await page.getByRole('button', { name: 'Show Password' }).click();
  await expect(password).toHaveAttribute('type', 'text');
  await page.getByRole('link', { name: 'Forgot password?' }).click();
  await expect(page).toHaveURL(/forgot-password/);
});

async function mockSession(page) {
  // UI fixtures only. This is not evidence of real account or broker access.
  await page.route('**/api/v1/**', async route => {
    const path = new URL(route.request().url()).pathname;
    const user = { id: 1, name: 'Cloud Test', email: 'test@example.test', roles: ['user'], authorities: [] };
    const body = path.endsWith('/auth/refresh') ? { access_token: 'test-fixture-token' }
      : path.endsWith('/users/me') ? user
      : path.endsWith('/workspace/status') ? { mode: 'PAPER_READ_ONLY', liveExecutionEnabled: false, brokerVerified: true, lastChecked: '2026-10-08T12:00:00Z', ai: { available: false, status: 'SETUP_REQUIRED' } }
      : [];
    await route.fulfill({ json: body });
  });
}

test('workspace keeps unavailable data distinct and calculates user risk inputs', async ({ page }) => {
  await mockSession(page);
  await page.goto('/dashboard');
  await expect(page.getByText('Available margin', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: /Generate research brief/ })).toBeDisabled();
  await page.getByLabel('Capital (₹)').fill('100000');
  await page.getByLabel('Entry price (₹)').fill('100');
  await page.getByLabel('Stop price (₹)').fill('95');
  await expect(page.getByText('200 units', { exact: true })).toBeVisible();
  await page.getByLabel('Lot size (units)').fill('75');
  await expect(page.getByText('150 units', { exact: true })).toBeVisible();
  await page.screenshot({ path: 'test-results/workspace-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
  await page.screenshot({ path: 'test-results/workspace-mobile.png', fullPage: true });
});

test('broker selection stays unavailable and appearance persists', async ({ page }) => {
  await mockSession(page);
  await page.goto('/broker');
  await page.getByLabel('Broker', { exact: true }).selectOption('Dhan');
  await expect(page.getByText(/Dhan is a requested integration/)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Broker authentication unavailable' })).toBeDisabled();
  await page.goto('/profile/appearance');
  await page.getByLabel('Theme', { exact: true }).selectOption('classic-light');
  await page.getByLabel('Accent color').selectOption('cyan');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'classic-light');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-accent', 'cyan');
});

test('broker credentials redirect only after verification and clear secrets on failure', async ({ page }) => {
  await mockSession(page);
  const broker = { broker: 'xts', name: 'XTS', status: 'DISCONNECTED', marketDataStatus: 'NOT_CONFIGURED', tradingStatus: 'NOT_CONFIGURED', connectionAvailable: true, adminCredentialsAvailable: false };
  await page.route('**/api/v1/brokers', route => route.fulfill({ json: [broker] }));
  let accepted = false;
  await page.route('**/api/v1/brokers/xts/connect', async route => {
    expect(route.request().postDataJSON().api_secret).toBe('fixture-secret');
    await route.fulfill(accepted ? { json: { ...broker, status: 'VERIFIED' } } : { status: 502, json: { detail: 'Broker rejected credentials' } });
  });
  await page.goto('/broker');
  await page.getByLabel('API Key', { exact: true }).fill('fixture-key');
  await page.getByLabel('API Secret', { exact: true }).fill('fixture-secret');
  await page.getByRole('button', { name: /Verify connection/ }).click();
  await expect(page.getByRole('alert')).toHaveText('Broker rejected credentials');
  await expect(page).toHaveURL(/broker/);
  await expect(page.getByLabel('API Secret', { exact: true })).toHaveValue('');
  accepted = true;
  await page.getByLabel('API Secret', { exact: true }).fill('fixture-secret');
  await page.getByRole('button', { name: /Verify connection/ }).click();
  await expect(page).toHaveURL(/dashboard/);
  await expect(page.getByText('Available margin', { exact: true })).toBeVisible();
});

test('dashboard without broker verification returns to step three', async ({ page }) => {
  await mockSession(page);
  await page.route('**/api/v1/workspace/status', route => route.fulfill({ json: { brokerVerified: false, lastChecked: '2026-10-08T12:00:00Z', ai: { available: false } } }));
  await page.goto('/dashboard');
  await expect(page).toHaveURL(/broker/);
});
