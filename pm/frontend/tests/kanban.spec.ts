import { expect, test, type Page } from "@playwright/test";

const login = async (page: Page) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("password");
  await page.getByRole("button", { name: /^sign in$/i }).click();
  await expect(page).toHaveURL(/\/board$/);
};

test("requires sign in before accessing board", async ({ page }) => {
  await page.goto("/board");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});

test("rejects invalid credentials", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Username").fill("user");
  await page.getByLabel("Password").fill("wrong-password");
  await page.getByRole("button", { name: /^sign in$/i }).click();
  await expect(page.getByText("Invalid username or password.")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});

test("loads the kanban board after login", async ({ page }) => {
  await login(page);
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]')).toHaveCount(5);
});

test("adds a card to a column", async ({ page }) => {
  await login(page);
  const cardTitle = `Playwright card ${Date.now()}`;
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill(cardTitle);
  await firstColumn.getByPlaceholder("Details").fill("Added via e2e.");
  await firstColumn.getByRole("button", { name: /add card/i }).click();
  await expect(firstColumn.getByText(cardTitle)).toBeVisible();

  await page.reload();
  await expect(page).toHaveURL(/\/board$/);
  await expect(page.getByRole("heading", { name: "Kanban Studio" })).toBeVisible();
  await expect(page.locator('[data-testid^="column-"]').first().getByText(cardTitle)).toBeVisible();
});

test("moves a card between columns", async ({ page }) => {
  await login(page);
  const firstColumn = page.locator('[data-testid^="column-"]').first();
  const cardTitle = `Move me ${Date.now()}`;
  await firstColumn.getByRole("button", { name: /add a card/i }).click();
  await firstColumn.getByPlaceholder("Card title").fill(cardTitle);
  await firstColumn.getByPlaceholder("Details").fill("Drag target card");
  await firstColumn.getByRole("button", { name: /add card/i }).click();

  const card = page.getByText(cardTitle).locator("xpath=ancestor::article[1]");
  const targetColumn = page.getByTestId("column-col-review");
  const cardBox = await card.boundingBox();
  const columnBox = await targetColumn.boundingBox();
  if (!cardBox || !columnBox) {
    throw new Error("Unable to resolve drag coordinates.");
  }

  await page.mouse.move(
    cardBox.x + cardBox.width / 2,
    cardBox.y + cardBox.height / 2
  );
  await page.mouse.down();
  await page.mouse.move(
    columnBox.x + columnBox.width / 2,
    columnBox.y + 120,
    { steps: 12 }
  );
  await page.mouse.up();
  await expect(targetColumn.getByText(cardTitle)).toBeVisible();

  await page.reload();
  await expect(page).toHaveURL(/\/board$/);
  await expect(page.getByTestId("column-col-review").getByText(cardTitle)).toBeVisible();
});

test("logs out and returns to sign in", async ({ page }) => {
  await login(page);
  await page.getByRole("button", { name: /log out/i }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Sign in" })).toBeVisible();
});

test("supports sidebar AI chat and applies board updates", async ({ page }) => {
  await login(page);

  const initialBoardResponse = await page.request.get("/api/board");
  expect(initialBoardResponse.ok()).toBeTruthy();
  const initialBoardPayload = (await initialBoardResponse.json()) as {
    board: {
      columns: Array<{ id: string; title: string; cardIds: string[] }>;
      cards: Record<string, { id: string; title: string; details: string }>;
    };
    version: number;
  };

  let persistedBoard = JSON.parse(
    JSON.stringify(initialBoardPayload.board)
  ) as typeof initialBoardPayload.board;
  let persistedVersion = initialBoardPayload.version;
  let serveMockBoard = false;
  let releaseAiResponse: (() => void) | null = null;
  const aiResponseGate = new Promise<void>((resolve) => {
    releaseAiResponse = resolve;
  });

  await page.route("**/api/board", async (route) => {
    if (
      serveMockBoard &&
      route.request().method() === "GET" &&
      route.request().url().endsWith("/api/board")
    ) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ board: persistedBoard, version: persistedVersion }),
      });
      return;
    }
    await route.continue();
  });

  await page.route("**/api/ai/chat", async (route) => {
    const body = route.request().postDataJSON() as {
      question: string;
      conversation_history: Array<{ role: "user" | "assistant"; content: string }>;
    };
    expect(body.conversation_history).toBeTruthy();
    await aiResponseGate;

    persistedBoard = {
      ...persistedBoard,
      columns: persistedBoard.columns.map((column, index) =>
        index === 0 ? { ...column, title: "AI Updated Column" } : column
      ),
    };
    persistedVersion += 1;
    serveMockBoard = true;

    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        assistant_message: "Updated your board.",
        should_update_board: true,
        board: persistedBoard,
        version: persistedVersion,
      }),
    });
  });

  const input = page.getByLabel("Ask AI assistant");
  await input.fill("Please update the first column title.");
  const sendButton = page.getByRole("button", { name: /send to ai/i });
  await sendButton.click();

  await expect(page.getByRole("button", { name: /sending/i })).toBeDisabled();
  releaseAiResponse?.();

  await expect(page.getByText("Updated your board.")).toBeVisible();
  await expect(page.locator('input[value="AI Updated Column"]').first()).toBeVisible();

  await page.reload();
  await expect(page).toHaveURL(/\/board$/);
  await expect(page.locator('input[value="AI Updated Column"]').first()).toBeVisible();
});
