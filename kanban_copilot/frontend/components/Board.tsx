"use client";

import { useState } from "react";
import { Board as BoardType, Column as ColumnType, Card as CardType } from "../lib/types";
import Column from "./Column";
import { v4 as uuidv4 } from "uuid";

const initialData: BoardType = {
  columns: Array.from({ length: 5 }).map((_, i) => ({
    id: uuidv4(),
    title: `Column ${i + 1}`,
    cards: [
      {
        id: uuidv4(),
        title: `Example card ${i + 1}-1`,
        details: "Details go here",
      },
    ],
  })),
};

export default function Board() {
  const [board, setBoard] = useState<BoardType>(initialData);

  const renameColumn = (id: string, newTitle: string) => {
    setBoard((b) => ({
      columns: b.columns.map((col) =>
        col.id === id ? { ...col, title: newTitle } : col
      ),
    }));
  };

  const addCard = (columnId: string, card: CardType) => {
    setBoard((b) => ({
      columns: b.columns.map((col) =>
        col.id === columnId
          ? { ...col, cards: [...col.cards, card] }
          : col
      ),
    }));
  };

  const deleteCard = (columnId: string, cardId: string) => {
    setBoard((b) => ({
      columns: b.columns.map((col) =>
        col.id === columnId
          ? { ...col, cards: col.cards.filter((c) => c.id !== cardId) }
          : col
      ),
    }));
  };

  return (
    <div className="flex space-x-4 overflow-x-auto p-4">
      {board.columns.map((col) => (
        <Column
          key={col.id}
          column={col}
          onRename={renameColumn}
          onAddCard={addCard}
          onDeleteCard={deleteCard}
        />
      ))}
    </div>
  );
}
