"use client";

import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Card as CardType, Column as ColumnType } from "@/data/board";
import { Card } from "./Card";

type ColumnProps = {
  column: ColumnType;
  cards: CardType[];
  onDeleteCard: (id: string) => void;
  onRenameColumn: (id: string, title: string) => void;
  onAddCard: (columnId: string) => void;
};

export function Column({
  column,
  cards,
  onDeleteCard,
  onRenameColumn,
  onAddCard,
}: ColumnProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(column.title);

  const handleBlur = () => {
    setIsEditing(false);
    const trimmed = editTitle.trim();
    if (trimmed && trimmed !== column.title) {
      onRenameColumn(column.id, trimmed);
    } else {
      setEditTitle(column.title);
    }
  };

  return (
    <div className="flex min-w-[280px] max-w-[280px] flex-col rounded-lg border border-[var(--blue-primary)]/20 bg-white/80 shadow-sm transition-shadow hover:shadow-md">
      <div className="border-b-2 border-[var(--accent-yellow)]/30 bg-[var(--blue-primary)]/5 px-4 py-3">
        {isEditing ? (
          <input
            type="text"
            value={editTitle}
            onChange={(e) => setEditTitle(e.target.value)}
            onBlur={handleBlur}
            onKeyDown={(e) => e.key === "Enter" && (e.target as HTMLInputElement).blur()}
            className="w-full rounded border border-[var(--blue-primary)]/40 bg-white px-2 py-1 text-[var(--dark-navy)] focus:outline-none focus:ring-2 focus:ring-[var(--blue-primary)]"
            autoFocus
          />
        ) : (
          <h2
            onClick={() => setIsEditing(true)}
            className="cursor-pointer font-semibold text-[var(--dark-navy)] hover:text-[var(--blue-primary)]"
          >
            {column.title}
          </h2>
        )}
      </div>
      <SortableContext items={cards.map((c) => c.id)} strategy={verticalListSortingStrategy}>
        <div className="flex flex-1 flex-col gap-2 overflow-y-auto p-3">
          {cards.map((card) => (
            <SortableCard key={card.id} card={card} onDelete={onDeleteCard} />
          ))}
        </div>
      </SortableContext>
      <button
        type="button"
        onClick={() => onAddCard(column.id)}
        className="m-3 rounded-lg border-2 border-dashed border-[var(--gray-text)]/40 py-2 text-sm text-[var(--gray-text)] transition-colors hover:border-[var(--blue-primary)] hover:text-[var(--blue-primary)]"
      >
        Add card
      </button>
    </div>
  );
}

function SortableCard({
  card,
  onDelete,
}: {
  card: CardType;
  onDelete: (id: string) => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: card.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <Card
      card={card}
      onDelete={onDelete}
      isDragging={isDragging}
      attributes={attributes as unknown as Record<string, unknown>}
      listeners={listeners as unknown as Record<string, unknown>}
      setNodeRef={setNodeRef}
      style={style}
    />
  );
}
