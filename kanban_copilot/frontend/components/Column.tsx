"use client";

import { Column as ColumnType, Card as CardType } from "../lib/types";
import Card from "./Card";
import { useState, FormEvent } from "react";
import { v4 as uuidv4 } from "uuid";

interface Props {
  column: ColumnType;
  onRename?: (id: string, newTitle: string) => void;
  onAddCard?: (columnId: string, card: CardType) => void;
  onDeleteCard?: (columnId: string, cardId: string) => void;
}

export default function Column({
  column,
  onRename,
  onAddCard,
  onDeleteCard,
}: Props) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(column.title);
  const [newCardTitle, setNewCardTitle] = useState("");

  const submitRename = () => {
    if (title.trim() && onRename) {
      onRename(column.id, title.trim());
    }
    setEditing(false);
  };

  const handleAddCard = (e: FormEvent) => {
    e.preventDefault();
    if (newCardTitle.trim() && onAddCard) {
      onAddCard(column.id, {
        id: uuidv4(),
        title: newCardTitle.trim(),
      });
    }
    setNewCardTitle("");
  };

  return (
    <div className="w-64 flex-shrink-0 rounded bg-gray-100 p-4">
      <div className="mb-2">
        {editing ? (
          <input
            className="w-full border-b bg-transparent pb-1 text-lg font-semibold"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onBlur={submitRename}
            onKeyDown={(e) => {
              if (e.key === "Enter") submitRename();
              if (e.key === "Escape") {
                setTitle(column.title);
                setEditing(false);
              }
            }}
            autoFocus
          />
        ) : (
          <h2
            className="cursor-pointer text-lg font-semibold text-gray-900"
            onClick={() => setEditing(true)}
          >
            {column.title}
          </h2>
        )}
      </div>
      <div>
        {column.cards.map((c) => (
          <Card
            key={c.id}
            card={c}
            onDelete={onDeleteCard ? () => onDeleteCard(column.id, c.id) : undefined}
          />
        ))}
      </div>
      {onAddCard && (
        <form onSubmit={handleAddCard} className="mt-2">
          <input
            className="w-full rounded border px-2 py-1 text-sm"
            placeholder="New card..."
            value={newCardTitle}
            onChange={(e) => setNewCardTitle(e.target.value)}
          />
        </form>
      )}
    </div>
  );
}
