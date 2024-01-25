const { test, expect } = require('@playwright/test');

test.describe('Login page', () => {
    test('redirects to /login if user, token, or userType is missing', async ({ page }) => {
        await page.goto('http://localhost:1234');
        await page.evaluate(() => {
            // remove user token userType from localStorage
            localStorage.removeItem('user');
            localStorage.removeItem('token');
            localStorage.removeItem('userType');
        });
        await page.waitForNavigation();

        // Check that we've been redirected to /login
        expect(page.url()).toBe('http://localhost:1234/login');
    });
    test('admin login', async ({ page }) => {
        await page.goto('http://localhost:1234/login');
        await page.getByLabel('Username').click();
        await page.getByLabel('Username').fill('admin');
        await page.getByLabel('Password').click();
        await page.getByLabel('Password').fill('admin');
        await page.getByRole('button', { name: 'Log In' }).click();
        await page.waitForNavigation();
        // Check that we've been redirected to /
        expect(page.url()).toBe('http://localhost:1234/');
        await page.waitForNavigation();
        // Check that we've been redirected to /extract-metadata (special case for 'admin' user)
        expect(page.url()).toBe('http://localhost:1234/extract-metadata');
        await expect(page.getByRole('heading')).toContainText(['Extract Metadata']);
      });
    });
