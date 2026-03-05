import { describe, it, expect } from "vitest";
import { initialBoard } from "./board";

describe("board data", () => {
  it("has 5 columns", () => {
    expect(initialBoard.columns).toHaveLength(5);
  });

  it("columns have id and title", () => {
    for (const col of initialBoard.columns) {
      expect(col).toHaveProperty("id");
      expect(col).toHaveProperty("title");
      expect(typeof col.id).toBe("string");
      expect(typeof col.title).toBe("string");
    }
  });

  it("cards have id, title, details, columnId", () => {
    for (const card of initialBoard.cards) {
      expect(card).toHaveProperty("id");
      expect(card).toHaveProperty("title");
      expect(card).toHaveProperty("details");
      expect(card).toHaveProperty("columnId");
    }
  });

  it("all card columnIds reference existing columns", () => {
    const columnIds = new Set(initialBoard.columns.map((c) => c.id));
    for (const card of initialBoard.cards) {
      expect(columnIds.has(card.columnId)).toBe(true);
    }
  });
});
