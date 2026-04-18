# Handover Spec Template

Copy and adapt this template when creating a new ticket-driven handover test.

```typescript
import { test } from '../../fixtures/base';
import { getAuthFilePath } from '../../helpers/env-config';
import { {Feature}Page } from '../../poms/{feature}.page';

const authFile = getAuthFilePath();

test.describe('{TICKET}: {Short Description}', () => {
    // One-time setup: clean stale data from previous failed runs
    test.beforeAll(async ({ browser }) => {
        const context = await browser.newContext({
            storageState: authFile,
        });
        const page = await context.newPage();
        const pom = new {Feature}Page(page);
        await pom.setUp();
        await page.close();
        await context.close();
    });

    // Test each acceptance criterion from the ticket

    test('should {first acceptance criterion}', async ({ page, testData }) => {
        const pom = new {Feature}Page(page);
        const data = testData.{feature};

        await pom.navigateToPage();
        // ... validate criterion
    });

    test('should {second acceptance criterion}', async ({ page, testData }) => {
        const pom = new {Feature}Page(page);
        const data = testData.{feature};

        await pom.navigateToPage();
        // ... validate criterion
    });

    // Include edge cases and error scenarios from the ticket

    test('should handle {error scenario}', async ({ page }) => {
        const pom = new {Feature}Page(page);

        await pom.navigateToPage();
        // ... validate error handling
    });
});
```

## Placeholders

| Placeholder | Example |
| ----------- | ------- |
| `{TICKET}` | `PROJ-456` (exact ticket key) |
| `{Short Description}` | `Bulk Export` (human-readable) |
| `{Feature}` | `Vault` (PascalCase) |
| `{feature}` | `vault` (lowercase) |

## Filename

```
e2e/tests/handover/{TICKET}-{short-description}.spec.ts
```

Example: `e2e/tests/handover/PROJ-456-bulk-export.spec.ts`

## Promotion Reminder

When this ticket is Done, this test must be:
1. **Promoted** to `tests/regression/` or `tests/smoke/` (rename to drop ticket prefix)
2. **Deleted** if already covered by existing tests

Use `/promote-handover-test {TICKET}` when ready.
