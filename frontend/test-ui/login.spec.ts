import { test, expect } from "@playwright/test";

test.describe("Login page", () => {
  test("redirects to /log-in if user, token, or userType is missing", async ({
    page,
  }) => {
    await page.goto("http://localhost/");
    await page.evaluate(() => {
      // remove user token userType from localStorage
      localStorage.removeItem("defogUser");
      localStorage.removeItem("defogToken");
      localStorage.removeItem("defogUserType");
    });
    await page.waitForURL("http://localhost/log-in");

    // Check that we've been redirected to /log-in
    expect(page.url()).toBe("http://localhost/log-in");
  });
  test("admin login", async ({ page }) => {
    await page.goto("http://localhost/log-in");
    await page.getByLabel("Username").click();
    await page.getByLabel("Username").fill("admin");
    await page.getByLabel("Password").click();
    await page.getByLabel("Password").fill("admin");
    await page.getByRole("button", { name: "Log In" }).click();

    // Check that we've been redirected to /extract-metadata
    // if not admin, we redirect to /view-notebooks
    await page.waitForURL("http://localhost/extract-metadata");
    expect(page.url()).toBe("http://localhost/extract-metadata");

    // Check local storage for defogUser, defogToken, and defogUserType
    expect(await page.evaluate(() => localStorage.getItem("defogUser"))).toBe(
      "admin"
    );
    expect(
      await page.evaluate(() => localStorage.getItem("defogToken"))
    ).not.toBe(null);
    expect(
      await page.evaluate(() => localStorage.getItem("defogUserType"))
    ).toBe("admin");
    // Check that it redirects to the extract-metadata page
    await page.waitForURL("http://localhost/extract-metadata");
    expect(page.url()).toBe("http://localhost/extract-metadata");
    await expect(page.getByRole("heading")).toContainText(["Extract Metadata"]);
  });
});
