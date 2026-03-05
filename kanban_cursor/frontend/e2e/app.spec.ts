import { test, expect } from "@playwright/test";

test.describe("Kanban Board", () => {
  test("loads with dummy data - 5 columns with cards", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Kanban Board" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Backlog" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "To Do" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "In Progress" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Review" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Done" })).toBeVisible();
    await expect(page.getByText("Set up project")).toBeVisible();
    await expect(page.getByText("Deploy MVP")).toBeVisible();
  });

  test("add card flow", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("heading", { name: "Backlog" }).scrollIntoViewIfNeeded();
    await page.getByRole("button", { name: "Add card" }).first().click();
    await page.getByPlaceholder("Card title").fill("E2E Test Card");
    await page.getByPlaceholder("Card details").fill("Added by E2E test");
    await page.getByRole("button", { name: "Add card" }).last().click();
    await expect(page.getByText("E2E Test Card")).toBeVisible();
    await expect(page.getByText("Added by E2E test")).toBeVisible();
  });

  test("delete card flow", async ({ page }) => {
    await page.goto("/");
    const card = page.getByText("Set up project").first();
    await card.scrollIntoViewIfNeeded();
    await card.hover();
    await page.getByLabel("Delete Set up project").click();
    await expect(page.getByText("Set up project")).not.toBeVisible();
  });

  test("rename column flow", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("heading", { name: "Backlog" }).click();
    const input = page.getByRole("textbox");
    await input.fill("New Backlog");
    await input.press("Enter");
    await expect(page.getByText("New Backlog")).toBeVisible();
  });

  test("drag card to another column", async ({ page }) => {
    await page.goto("/");
    const card = page.getByText("Set up project").first();
    const targetCard = page.getByText("Build board layout").first();
    await card.scrollIntoViewIfNeeded();
    const cardBox = await card.boundingBox();
    const targetBox = await targetCard.boundingBox();
    if (!cardBox || !targetBox) throw new Error("Elements not found");
    await page.mouse.move(cardBox.x + cardBox.width / 2, cardBox.y + cardBox.height / 2);
    await page.mouse.down();
    await page.mouse.move(targetBox.x + targetBox.width / 2, targetBox.y + targetBox.height / 2, { steps: 10 });
    await page.mouse.up();
    await expect(page.getByTestId("column-col-2").getByText("Set up project")).toBeVisible();
  });

  test("reorder cards within column", async ({ page }) => {
    await page.goto("/");
    const backlogColumn = page.getByTestId("column-col-1");
    const cards = backlogColumn.getByText("Set up project");
    await expect(cards.first()).toBeVisible();
    const firstCard = cards.first();
    const secondCard = backlogColumn.getByText("Design mockups").first();
    await firstCard.scrollIntoViewIfNeeded();
    const box1 = await firstCard.boundingBox();
    const box2 = await secondCard.boundingBox();
    if (!box1 || !box2) throw new Error("Elements not found");
    await page.mouse.move(box1.x + box1.width / 2, box1.y + box1.height / 2);
    await page.mouse.down();
    await page.mouse.move(box2.x + box2.width / 2, box2.y + box2.height / 2, { steps: 5 });
    await page.mouse.up();
    await expect(backlogColumn.getByText("Set up project")).toBeVisible();
  });
});
