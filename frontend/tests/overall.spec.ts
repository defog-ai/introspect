import { test, expect } from '@playwright/test';

test('test', async ({ page }) => {
  // TEST LOGIN
  await page.goto('http://localhost/');
  await page.goto('http://localhost/log-in');
  await page.getByLabel('Username').click();
  await page.getByLabel('Username').fill('admin');
  await page.getByLabel('Username').press('Tab');
  await page.getByLabel('Password').fill('admin');
  await page.getByRole('button', { name: 'Sign in' }).click();

  // TEST ADD DB CREDENTIALS
  await page.getByText('PostgreSQL').click();
  await page.getByText('PostgreSQL').nth(1).click();
  await page.getByPlaceholder('host.docker.internal').click();
  await page.getByPlaceholder('host.docker.internal').press('ControlOrMeta+a');
  await page.getByPlaceholder('host.docker.internal').fill('host.docker.internal');
  await page.getByPlaceholder('5432').click();
  await page.getByPlaceholder('5432').press('ControlOrMeta+a');
  await page.getByPlaceholder('5432').fill('5432');
  await page.getByPlaceholder('Database User').click();
  await page.getByPlaceholder('Database User').press('ControlOrMeta+a');
  await page.getByPlaceholder('Database User').fill('postgres');
  await page.getByPlaceholder('Enter password').click();
  await page.getByPlaceholder('Enter password').press('ControlOrMeta+a');
  await page.getByPlaceholder('Enter password').fill('postgres');
  await page.getByPlaceholder('Database Name').click();
  await page.getByPlaceholder('Database Name').press('ControlOrMeta+a');
  await page.getByPlaceholder('Database Name').fill('restaurants');
  await page.getByRole('button', { name: 'Update' }).click();

  // TEST UPDATE METADATA
  await page.getByLabel('Tabs').locator('div').nth(2).click();
  await page.getByRole('button', { name: 'Extract Table Metadata' }).click();
  await page.getByRole('button', { name: 'Save Changes' }).click();
  await page.getByRole('link', { name: 'Query Data' }).click();
  // wait for 1 second

  // TEST INITIAL QUERYING
  await page.waitForTimeout(1000);
  await page.getByText('Restaurants').click();
  await page.getByPlaceholder('Type your question here').click();
  await page.getByPlaceholder('Type your question here').fill('what is the average rating by city?');
  await page.getByRole('button', { name: 'Ask' }).click();
  // see if a clarifying question is asked after 3 seconds
  await page.waitForTimeout(3000);
  const buttonFirstTry = page.getByRole('button', { name: 'Click here or press enter to' });
  if (await buttonFirstTry.count() > 0) {
    await buttonFirstTry.click();
  }

  // TEST POSITIVE FEEDBACK
  await page.getByText('👍').nth(1).click();

  // TEST ADDING POSITIVE FEEDBACK TO GOLDEN QUERIES
  await page.getByRole('link', { name: 'View Feedback' }).click();
  await page.getByRole('button', { name: 'Add to Golden Queries' }).click();
  
  // TEST UPDATING GLOSSARY
  await page.getByRole('link', { name: 'Align Model' }).click();
  await page.getByRole('textbox').first().click();
  await page.getByRole('textbox').first().fill('- this is a compulsory instruction');
  await page.getByRole('textbox').nth(1).click();
  await page.getByRole('textbox').nth(1).fill('- this is a supplementary instruction');
  await page.getByRole('button', { name: 'Update Glossary' }).click();
  
  // TEST QUERYING AGAIN
  await page.getByRole('link', { name: 'Query Data' }).click();
  // wait for 1 second
  await page.waitForTimeout(1000);
  await page.getByText('Restaurants').click();
  await page.getByPlaceholder('Type your question here').click();
  await page.getByPlaceholder('Type your question here').fill('what is the average rating by city?');
  await page.getByRole('button', { name: 'Ask' }).click();
  // see if a clarifying question is asked after 3 seconds
  await page.waitForTimeout(3000);
  const buttonSecondTry = page.getByRole('button', { name: 'Click here or press enter to' });
  if (await buttonSecondTry.count() > 0) {
    await buttonSecondTry.click();
  }
});