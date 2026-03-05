import { expect, test } from "@playwright/test";

test.describe("kanban MVP", () => {
  test("renders board with five columns and seed cards", async ({ page }) => {
    await page.goto("/");

    await expect(page.getByRole("heading", { name: "Launch Control Kanban" })).toBeVisible();
    await expect(page.locator('[data-testid^="column-col-"]')).toHaveCount(5);
    await expect(page.getByText("Finalize pricing page")).toBeVisible();
  });

  test("renames a column", async ({ page }) => {
    await page.goto("/");

    const firstColumnInput = page.getByLabel("col-1-name");
    await firstColumnInput.fill("Intake");
    await firstColumnInput.blur();

    await expect(firstColumnInput).toHaveValue("Intake");
  });

  test("adds and deletes a card", async ({ page }) => {
    await page.goto("/");

    const reviewColumn = page.getByTestId("column-col-4");
    await reviewColumn.getByRole("button", { name: "Add card" }).click();

    await page.getByPlaceholder("Card title").fill("Regression sweep");
    await page
      .getByPlaceholder("Card details")
      .fill("Confirm all core cards are flowing correctly.");
    await page.getByRole("button", { name: "Save Card" }).click();

    await expect(page.getByText("Regression sweep")).toBeVisible();

    await page.getByRole("button", { name: "Delete Regression sweep" }).click();
    await expect(page.getByText("Regression sweep")).toHaveCount(0);
  });

  test("moves a card between columns by drag and drop", async ({ page }) => {
    await page.goto("/");

    const sourceCard = page.getByTestId("card-card-1");
    const targetColumn = page.getByTestId("column-col-3");
    const sourceColumn = page.getByTestId("column-col-1");

    await sourceCard.dragTo(targetColumn);

    await expect(targetColumn.getByText("Finalize pricing page")).toBeVisible();
    await expect(sourceColumn.getByText("Finalize pricing page")).toHaveCount(0);
  });

  test("reorders cards within a column by drag and drop", async ({ page }) => {
    await page.goto("/");

    const backlogColumn = page.getByTestId("column-col-1");
    const sourceCard = backlogColumn.getByTestId("card-card-2");
    const targetCard = backlogColumn.getByTestId("card-card-1");
    const targetBox = await targetCard.boundingBox();

    await sourceCard.dragTo(targetCard, {
      targetPosition: {
        x: targetBox ? Math.min(24, targetBox.width / 2) : 12,
        y: 4,
      },
    });

    await expect(backlogColumn.locator("h2").first()).toHaveText(
      "Collect launch screenshots",
    );
    await expect(backlogColumn.locator("h2").nth(1)).toHaveText(
      "Finalize pricing page",
    );
  });

  test("reorders cards downward within a column by drag and drop", async ({ page }) => {
    await page.goto("/");

    const backlogColumn = page.getByTestId("column-col-1");
    const sourceCard = backlogColumn.getByTestId("card-card-1");
    const targetCard = backlogColumn.getByTestId("card-card-2");
    const targetBox = await targetCard.boundingBox();

    await sourceCard.dragTo(targetCard, {
      targetPosition: {
        x: targetBox ? Math.min(24, targetBox.width / 2) : 12,
        y: targetBox ? Math.max(6, targetBox.height - 6) : 32,
      },
    });

    await expect(backlogColumn.locator("h2").first()).toHaveText(
      "Collect launch screenshots",
    );
    await expect(backlogColumn.locator("h2").nth(1)).toHaveText(
      "Finalize pricing page",
    );
  });
});
