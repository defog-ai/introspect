import { test, expect } from '@playwright/test';

test.describe('Notebooks page', () => {
  test('Notebook Creation and Basic Analysis', async ({ page }) => {
    await page.goto('http://localhost:1234/');
    // set the auth variables in localStorage so that we don't get redirected to /login
    await page.evaluate(() => {
        localStorage.setItem('defogUser', 'admin');
        localStorage.setItem('defogToken', 'bdbe4d376e6c8a53a791a86470b924c0715854bd353483523e3ab016eb55bcd0');
        localStorage.setItem('defogUserType', 'admin');
    });
    // get the url path of the new window
    const context = page.context();
    const page1 = await context.newPage();
    await page1.goto('http://localhost:1234/doc?docId=new');
    await page1.waitForLoadState();
    await page1.waitForSelector('#nav-other-docs');
    await expect(page1.getByText('New')).toBeVisible();
    await expect(page1.getByText('Open')).toBeVisible();
    await expect(page1.getByText('Past analyses')).toBeVisible();

    // test out markdown component (H1)
    // select the first empty block, type '/' to open the menu, select 'H1', and type in 'H1'
    await page1.locator('.tiptap').first().click();
    await page1.locator('.tiptap').first().press('/');
    // await page1.getByText('Headings', { exact: true }).waitFor({ state: 'visible' });
    await page1.getByRole('menuitem', { name: 'Heading Used for a top-level' }).click();
    await page1.locator('.bn-block').first().fill('H1');
    await page1.locator('.bn-block').first().press('Enter');
    await expect(page1.getByRole('heading', { name: 'H1' })).toContainText('H1');

    // test out markdown component (H2)
    // select the same block, type '/' to open the menu, select 'H2', and type in 'H2'
    await page1.locator('.bn-block-content').nth(1).press('/');
    await page1.getByRole('menuitem', { name: 'Heading 2 Used for key' }).click();
    await page1.locator('div:nth-child(1) > .bn-block > .bn-block-content').fill('H2');
    await expect(page1.getByRole('heading', { name: 'H2' })).toContainText('H2');
  });
});