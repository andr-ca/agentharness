---
name: playwright-ui-testing
description: Mandatory Playwright testing for all web UI work with screenshot verification
complexity: medium
frameworks: web, react, vue, angular, next, nuxt, svelte
languages: typescript, javascript
---

# Playwright UI Testing

This applies at the **Production** rigor tier — see
`.github/CODING_GUIDELINES.md#rigor-tiers`. Internal tools and prototypes
can skip this; manual verification is fine there.

## 🚨 CRITICAL REQUIREMENT (Production tier)

**ALL PRODUCTION-TIER WEB UI WORK IS MANDATORY PLAYWRIGHT + SCREENSHOT VERIFICATION**

This means:
- ✅ UI work STARTS with Playwright setup (not added later)
- ✅ Every UI component MUST have Playwright tests
- ✅ EVERY test MUST include screenshot verification
- ✅ Screenshots MUST be reviewed by agent/human before approval
- ✅ Visual regressions are caught during development, not production

**At Production tier, UI work WITHOUT Playwright tests and screenshot verification WILL NOT MERGE.**

### What "Screenshot Approval" Actually Means

"Agent MUST review and approve screenshots" is meaningless without a
concrete mechanism. Here's the mechanism:

1. Playwright writes screenshots to `test-results/screenshots/` (or your
   configured path) as part of the normal test run.
2. Before marking the task complete, the agent (or human) opens each new
   or changed screenshot and states, in the PR description or commit
   message, what was checked and what was seen — e.g. "Reviewed
   `login-success.png`: form renders correctly, no layout shift, matches
   the design spec." A screenshot that was generated but never looked at
   does not count as reviewed.
3. If comparing against a baseline (`--update-snapshots` workflow), the
   diff output itself (pass/fail per snapshot) is the evidence — link or
   paste it.
4. CI enforces the mechanical part: the Playwright test suite (including
   snapshot comparison) must pass. CI cannot enforce that a human actually
   looked at a screenshot; that's why step 2's written statement exists —
   it's the audit trail for the part CI can't check.

If you can't produce that written statement, the screenshots weren't
reviewed — go review them.

---

## Why Playwright is Mandatory

### The Problem Without UI Testing

- ❌ UI breaks and nobody notices until production
- ❌ Components work locally but fail in CI (browser differences)
- ❌ Cross-browser testing done manually (error-prone)
- ❌ Responsive design breaks with small changes
- ❌ Accessibility regressions go undetected
- ❌ Visual regressions happen silently

### What Playwright Solves

- ✅ Test actual browser engines (Chromium, Firefox, WebKit — the engine behind Safari)
- ✅ Catch visual regressions automatically
- ✅ Verify responsiveness across screen sizes
- ✅ Test user workflows end-to-end
- ✅ Screenshot comparison detects visual bugs
- ✅ Document expected behavior with screenshots

---

## Playwright Project Setup

### Installation

```bash
# Install Playwright
npm install --save-dev @playwright/test

# Install browser binaries (Chromium, Firefox, WebKit)
npx playwright install

# Scaffold playwright.config.ts, example tests, and CI workflow
npm init playwright@latest
```

### Project Structure

```
your-project/
├── src/
│   ├── components/
│   ├── pages/
│   └── ...
├── tests/
│   ├── ui/                           # Playwright tests
│   │   ├── auth.spec.ts             # Authentication flow
│   │   ├── dashboard.spec.ts        # Dashboard page
│   │   ├── components/              # Component tests
│   │   │   ├── button.spec.ts
│   │   │   ├── modal.spec.ts
│   │   │   └── form.spec.ts
│   │   └── fixtures/                # Shared test data
│   │       └── users.ts
│   └── unit/                        # Unit tests (non-UI)
├── tests-results/                   # Test artifacts
│   ├── screenshots/                 # Screenshots from tests
│   ├── videos/                      # Test videos (on failure)
│   └── reports/                     # HTML reports
├── playwright.config.ts             # Playwright configuration
└── package.json
```

### Configuration (playwright.config.ts)

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  // Test configuration
  testDir: './tests/ui',
  testMatch: '**/*.spec.ts',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,  // Fail on .only in CI
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  
  // Global timeout
  timeout: 30000,
  expect: { timeout: 5000 },
  
  // Base URL for all tests
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',  // Or 'on' for all
    video: 'retain-on-failure',
  },
  
  // Web server (start before tests)
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
  
  // Test against multiple browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
    },
  ],
});
```

---

## Writing UI Tests with Screenshots

### Test Structure (AAA Pattern)

```typescript
import { test, expect } from '@playwright/test';

test('user can login with valid credentials', async ({ page }) => {
  // ARRANGE: Navigate to login page
  await page.goto('/login');
  
  // ACT: Fill form and submit
  await page.fill('input[name="email"]', 'user@example.com');
  await page.fill('input[name="password"]', 'correct_password');
  await page.click('button[type="submit"]');
  
  // ASSERT: Verify navigation and take screenshot
  await expect(page).toHaveURL('/dashboard');
  
  // MANDATORY: Screenshot verification
  await page.screenshot({ path: 'screenshots/login-success.png' });
  await expect(page).toHaveScreenshot('login-success.png');
});
```

### Taking Screenshots

#### Full Page Screenshot
```typescript
// Screenshot of entire page
await page.screenshot({ path: 'full-page.png' });
await expect(page).toHaveScreenshot('full-page.png');
```

#### Component Screenshot
```typescript
// Screenshot of specific component
const button = page.locator('button.primary');
await button.screenshot({ path: 'button.png' });
await expect(button).toHaveScreenshot('button.png');
```

#### With Options
```typescript
// Screenshot with specific settings
await page.screenshot({
  path: 'screenshot.png',
  fullPage: true,        // Full page or viewport
  mask: [page.locator('timestamp')],  // Mask dynamic content
});
```

### Visual Regression Testing

**First run creates baseline:**
```bash
npx playwright test --update-snapshots
# Creates: tests/ui/auth.spec.ts-snapshots/
```

**Subsequent runs compare:**
```bash
npx playwright test
# Compares screenshots against baseline
# Fails if visual changes detected
```

**Review and approve changes:**
```bash
# If changes are intentional
npx playwright test --update-snapshots
# Commit the updated screenshots
```

---

## Complete UI Test Examples

### Example 1: Login Flow with Screenshots

```typescript
import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('user can login with valid credentials', async ({ page }) => {
    // Navigate
    await page.goto('/login');
    
    // Take initial screenshot (verify form)
    await page.screenshot({ path: 'login-page.png' });
    await expect(page).toHaveScreenshot('login-page.png');
    
    // Fill and submit
    await page.fill('input[name="email"]', 'user@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    // Wait for navigation
    await page.waitForURL('/dashboard');
    
    // Take success screenshot
    await page.screenshot({ path: 'login-success.png' });
    await expect(page).toHaveScreenshot('login-success.png');
  });

  test('shows error on invalid password', async ({ page }) => {
    await page.goto('/login');
    
    // Submit with wrong password
    await page.fill('input[name="email"]', 'user@example.com');
    await page.fill('input[name="password"]', 'wrong_password');
    await page.click('button[type="submit"]');
    
    // Verify error message
    const errorMessage = page.locator('[role="alert"]');
    await expect(errorMessage).toBeVisible();
    
    // Screenshot showing error
    await page.screenshot({ path: 'login-error.png' });
    await expect(page).toHaveScreenshot('login-error.png');
  });

  test('handles empty form submission', async ({ page }) => {
    await page.goto('/login');
    
    // Try to submit empty form
    await page.click('button[type="submit"]');
    
    // Verify validation errors
    await expect(page.locator('input[name="email"]')).toHaveAttribute('aria-invalid', 'true');
    
    // Screenshot of validation state
    await page.screenshot({ path: 'login-validation.png' });
    await expect(page).toHaveScreenshot('login-validation.png');
  });
});
```

### Example 2: Component Testing

```typescript
import { test, expect } from '@playwright/test';

test.describe('Button Component', () => {
  test('renders default state', async ({ page }) => {
    await page.goto('/components/button');
    
    const button = page.locator('button.primary');
    await expect(button).toBeVisible();
    
    // Component screenshot
    await button.screenshot({ path: 'button-default.png' });
    await expect(button).toHaveScreenshot('button-default.png');
  });

  test('renders hover state', async ({ page }) => {
    await page.goto('/components/button');
    
    const button = page.locator('button.primary');
    await button.hover();
    
    // Screenshot of hover state
    await button.screenshot({ path: 'button-hover.png' });
    await expect(button).toHaveScreenshot('button-hover.png');
  });

  test('renders disabled state', async ({ page }) => {
    await page.goto('/components/button?disabled=true');
    
    const button = page.locator('button.primary');
    
    // Screenshot of disabled state
    await button.screenshot({ path: 'button-disabled.png' });
    await expect(button).toHaveScreenshot('button-disabled.png');
  });
});
```

### Example 3: Responsive Design Testing

```typescript
import { test, expect, devices } from '@playwright/test';

// Test on multiple viewports
const VIEWPORTS = [
  { name: 'Mobile', viewport: { width: 375, height: 667 } },
  { name: 'Tablet', viewport: { width: 768, height: 1024 } },
  { name: 'Desktop', viewport: { width: 1920, height: 1080 } },
];

test.describe('Dashboard - Responsive', () => {
  VIEWPORTS.forEach(({ name, viewport }) => {
    test(`displays correctly on ${name}`, async ({ page }) => {
      page.setViewportSize(viewport);
      await page.goto('/dashboard');
      
      // Wait for content to load
      await page.waitForLoadState('networkidle');
      
      // Screenshot at this viewport
      await page.screenshot({ path: `dashboard-${name.toLowerCase()}.png` });
      await expect(page).toHaveScreenshot(`dashboard-${name.toLowerCase()}.png`);
      
      // Verify key elements are visible
      await expect(page.locator('main')).toBeVisible();
      await expect(page.locator('nav')).toBeVisible();
    });
  });
});
```

### Example 4: Accessibility + Visual Testing

```typescript
import { test, expect } from '@playwright/test';

test('modal dialog is accessible and visually correct', async ({ page }) => {
  await page.goto('/components/modal');
  
  // Open modal
  await page.click('button[aria-label="Open dialog"]');
  
  // Wait for modal
  const modal = page.locator('[role="dialog"]');
  await expect(modal).toBeVisible();
  
  // Verify accessibility
  await expect(modal).toHaveAttribute('aria-modal', 'true');
  await expect(page.locator('[role="heading"]')).toHaveAttribute('id');
  
  // Screenshot of modal state
  await modal.screenshot({ path: 'modal-open.png' });
  await expect(modal).toHaveScreenshot('modal-open.png');
  
  // Close modal
  await page.click('button[aria-label="Close"]');
  await expect(modal).not.toBeVisible();
  
  // Screenshot after close
  await page.screenshot({ path: 'modal-closed.png' });
  await expect(page).toHaveScreenshot('modal-closed.png');
});
```

---

## Running Tests

### Development Mode

```bash
# Run all tests
npx playwright test

# Run specific file
npx playwright test tests/ui/login.spec.ts

# Run specific test
npx playwright test -g "user can login"

# Watch mode (re-run on file changes)
npx playwright test --watch

# Debug mode (interactive)
npx playwright test --debug
```

### With Screenshots

```bash
# Run and update screenshots
npx playwright test --update-snapshots

# Run and compare against baseline
npx playwright test

# View test report with screenshots
npx playwright show-report
```

### CI/CD Pipeline

```bash
# Run all tests (fail on visual changes)
CI=true npx playwright test

# Generate HTML report
npx playwright test --reporter=html

# Upload screenshots to artifact storage
```

---

## Screenshot Verification Workflow

### Step 1: Agent/Developer Runs Tests

```bash
npx playwright test
```

### Step 2: Review Test Results

```
✓ tests/ui/login.spec.ts (3 tests)
  ✓ user can login with valid credentials (2s)
  ✓ shows error on invalid password (2s)
  ✓ handles empty form submission (1s)
```

### Step 3: View Screenshots

```bash
# Open HTML report with screenshots
npx playwright show-report

# Or view screenshots directory
ls tests-results/screenshots/
```

### Step 4: Verify Screenshots Visually

**Agent/human must verify:**
- ✅ Layout looks correct
- ✅ Colors are correct
- ✅ Text is readable
- ✅ Components render properly
- ✅ No visual glitches
- ✅ Responsive at different sizes
- ✅ Mobile version looks good

### Step 5: Approve or Fix

**If screenshots look wrong:**
1. Check the test
2. Check the component code
3. Fix the issue
4. Re-run tests
5. Verify new screenshots

**If screenshots look right:**
1. Commit updated screenshots
2. Mark UI work complete
3. Create PR for review

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: UI Tests with Screenshots

on: [push, pull_request]

jobs:
  ui-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Install Playwright browsers
        run: npx playwright install --with-deps
      
      - name: Run UI tests
        run: npx playwright test
      
      - name: Upload screenshots
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-screenshots
          path: tests-results/
          retention-days: 30
      
      - name: Upload HTML report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 30
```

### Fail on Visual Regression

```yaml
- name: Run UI tests (fail on regression)
  run: npx playwright test
  
# Test will fail if:
# - Screenshot differs from baseline
# - Any test fails
# - Browser not available
```

---

## Screenshot Comparison

### Baseline Screenshots (First Run)

```
tests/ui/login.spec.ts-snapshots/
├── login-page.png                    # Initial form
├── login-success.png                 # After successful login
└── login-error.png                   # Error state
```

### Comparison (Subsequent Runs)

```bash
# If screenshot matches baseline
✓ expects to have screenshot 'login-success.png'

# If screenshot differs
✗ expects to have screenshot 'login-success.png'
  1) Snapshot comparison failed:
  - tests/ui/login.spec.ts-snapshots/login-success.png
  + tests-results/login-success-1.png
```

### Review Differences

```bash
# View side-by-side comparison
npx playwright show-report

# Then approve or reject changes
```

---

## Testing Checklist for UI Work

✅ **Before Starting UI Work:**
- [ ] Playwright is set up in project
- [ ] playwright.config.ts is configured
- [ ] Browser support list defined (Chromium, Firefox, WebKit, mobile viewports)
- [ ] Screenshot directory configured

✅ **During UI Development:**
- [ ] Write test FIRST (before building UI)
- [ ] Screenshot verification included in every test
- [ ] Test happy path
- [ ] Test error states
- [ ] Test edge cases
- [ ] Test responsive design
- [ ] Test accessibility

✅ **Before Marking Complete:**
- [ ] All tests PASS
- [ ] All screenshots reviewed and approved
- [ ] No visual regressions
- [ ] Mobile responsiveness verified
- [ ] Cross-browser tested (Chromium, Firefox, WebKit)
- [ ] Baseline screenshots committed
- [ ] Test coverage >= 80%
- [ ] HTML report shows all tests passing

✅ **In Code Review:**
- [ ] Review test code (coverage, scenarios)
- [ ] Review screenshots (visual correctness)
- [ ] Verify responsive design
- [ ] Check accessibility
- [ ] Verify no regressions

---

## Common Issues & Solutions

### Issue: Screenshots Keep Failing

**Cause:** Dynamic content (timestamps, IDs, random data)

**Solution:** Mask dynamic elements
```typescript
await page.screenshot({
  path: 'screenshot.png',
  mask: [
    page.locator('[data-testid="timestamp"]'),
    page.locator('[data-testid="random-id"]'),
  ],
});
```

### Issue: Tests Pass Locally, Fail in CI

**Cause:** Browser differences, font rendering, timing

**Solution:** Use consistent environment
```typescript
// playwright.config.ts
use: {
  locale: 'en-US',
  timezone: 'UTC',
  colorScheme: 'light',
}
```

### Issue: Mobile Screenshots Don't Match

**Cause:** Device-specific rendering

**Solution:** Test specific devices
```typescript
projects: [
  { name: 'iPhone 12', use: { ...devices['iPhone 12'] } },
  { name: 'Pixel 5', use: { ...devices['Pixel 5'] } },
]
```

### Issue: Slow Tests

**Cause:** Tests waiting too long, browser overhead

**Solution:** Optimize waits
```typescript
// Instead of
await page.waitForTimeout(5000);

// Use
await page.waitForSelector('data-loaded', { timeout: 5000 });
```

---

## Best Practices

### DO ✅
- ✅ Write tests BEFORE building UI
- ✅ Screenshot every test
- ✅ Test on multiple browsers
- ✅ Test responsive design
- ✅ Test accessibility
- ✅ Review all screenshots
- ✅ Use data-testid for reliable selectors
- ✅ Mask dynamic content

### DON'T ❌
- ❌ Skip screenshot verification
- ❌ Assume UI works without testing
- ❌ Test only on one browser
- ❌ Ignore responsive design
- ❌ Use brittle selectors (class names)
- ❌ Accept screenshots without reviewing
- ❌ Deploy without visual verification
- ❌ Claim UI work done without Playwright

---

## Resources

- [Playwright Documentation](https://playwright.dev/)
- [Playwright Visual Comparisons](https://playwright.dev/docs/test-snapshots)
- [Playwright Debugging](https://playwright.dev/docs/debug)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Accessibility Testing](https://playwright.dev/docs/accessibility-testing)

---

## Summary

**At Production tier, web UI work must:**
1. ✅ Use Playwright (mandatory)
2. ✅ Include screenshot verification (every test)
3. ✅ Test on multiple browsers
4. ✅ Have visual verification by agent/human
5. ✅ Have >= 80% test coverage
6. ✅ Pass all tests before marking complete

Prototype/Internal-tier UI work can use manual verification instead — see
`.github/CODING_GUIDELINES.md#rigor-tiers`.

**See Also:** TDD.md, COMPLETION_CHECKLIST.md
