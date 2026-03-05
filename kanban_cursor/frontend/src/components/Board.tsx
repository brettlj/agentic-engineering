"use client";

import { useState, useCallback } from "react";
import {
  DndContext,
  DragEndEvent,
  DragOverEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  useDroppable,
} from "@dnd-kit/core";
import { arrayMove } from "@dnd-kit/sortable";
import type { Board as BoardType, Card as CardType, Column as ColumnType } from "@/data/board";
import { initialBoard } from "@/data/board";
import { Column } from "./Column";
import { AddCardModal } from "./AddCardModal";

function getCardsByColumn(board: BoardType): Record<string, CardType[]> {
  const byColumn: Record<string, CardType[]> = {};
  for (const col of board.columns) {
    byColumn[col.id] = board.cards
      .filter((c) => c.columnId === col.id)
      .sort((a, b) => {
        const aIdx = board.cards.indexOf(a);
        const bIdx = board.cards.indexOf(b);
        return aIdx - bIdx;
      });
  }
  return byColumn;
}

export function Board() {
  const [board, setBoard] = useState<BoardType>(initialBoard);
  const [addCardColumnId, setAddCardColumnId] = useState<string | null>(null);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 8 },
    })
  );

  const cardsByColumn = getCardsByColumn(board);

  const handleDragOver = useCallback(
    (event: DragOverEvent) => {
      const { active, over } = event;
      if (!over) return;

      const activeId = active.id as string;
      const overId = over.id as string;

      const activeCard = board.cards.find((c) => c.id === activeId);
      if (!activeCard) return;

      const overColumn = board.columns.find((c) => c.id === overId);
      const overCard = board.cards.find((c) => c.id === overId);

      if (overColumn) {
        if (activeCard.columnId !== overColumn.id) {
          setBoard((prev) => ({
            ...prev,
            cards: prev.cards.map((c) =>
              c.id === activeId ? { ...c, columnId: overColumn.id } : c
            ),
          }));
        }
      } else if (overCard) {
        if (activeCard.columnId === overCard.columnId && activeId !== overId) {
          const columnCards = board.cards
            .filter((c) => c.columnId === overCard.columnId)
            .sort((a, b) => board.cards.indexOf(a) - board.cards.indexOf(b));
          const oldIndex = columnCards.findIndex((c) => c.id === activeId);
          const newIndex = columnCards.findIndex((c) => c.id === overId);
          if (oldIndex !== -1 && newIndex !== -1 && oldIndex !== newIndex) {
            const reordered = arrayMove(columnCards, oldIndex, newIndex);
            setBoard((prev) => {
              const otherCards = prev.cards.filter(
                (c) => c.columnId !== overCard.columnId
              );
              const newCards = [...otherCards, ...reordered];
              return { ...prev, cards: newCards };
            });
          }
        } else if (activeCard.columnId !== overCard.columnId) {
          setBoard((prev) => ({
            ...prev,
            cards: prev.cards.map((c) =>
              c.id === activeId ? { ...c, columnId: overCard.columnId } : c
            ),
          }));
        }
      }
    },
    [board]
  );

  const handleDragEnd = useCallback((_event: DragEndEvent) => {
    // State updates handled in onDragOver
  }, []);

  const handleDeleteCard = useCallback((id: string) => {
    setBoard((prev) => ({
      ...prev,
      cards: prev.cards.filter((c) => c.id !== id),
    }));
  }, []);

  const handleRenameColumn = useCallback((id: string, title: string) => {
    setBoard((prev) => ({
      ...prev,
      columns: prev.columns.map((c) =>
        c.id === id ? { ...c, title } : c
      ),
    }));
  }, []);

  const handleAddCard = useCallback((columnId: string, title: string, details: string) => {
    const newCard: CardType = {
      id: `card-${Date.now()}`,
      title,
      details,
      columnId,
    };
    setBoard((prev) => ({
      ...prev,
      cards: [...prev.cards, newCard],
    }));
    setAddCardColumnId(null);
  }, []);

  return (
    <>
      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragOver={handleDragOver}
        onDragEnd={handleDragEnd}
      >
        <div className="flex gap-4 overflow-x-auto pb-4">
          {board.columns.map((column: ColumnType) => (
            <DroppableColumn
              key={column.id}
              column={column}
              cards={cardsByColumn[column.id] ?? []}
              onDeleteCard={handleDeleteCard}
              onRenameColumn={handleRenameColumn}
              onAddCard={() => setAddCardColumnId(column.id)}
            />
          ))}
        </div>
      </DndContext>

      {addCardColumnId && (
        <AddCardModal
          columnId={addCardColumnId}
          columnTitle={
            board.columns.find((c) => c.id === addCardColumnId)?.title ?? ""
          }
          onAdd={handleAddCard}
          onClose={() => setAddCardColumnId(null)}
        />
      )}
    </>
  );
}

function DroppableColumn({
  column,
  cards,
  onDeleteCard,
  onRenameColumn,
  onAddCard,
}: {
  column: ColumnType;
  cards: CardType[];
  onDeleteCard: (id: string) => void;
  onRenameColumn: (id: string, title: string) => void;
  onAddCard: () => void;
}) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });
  return (
    <div ref={setNodeRef} className={isOver ? "opacity-90" : ""} data-testid={`column-${column.id}`}>
      <Column
        column={column}
        cards={cards}
        onDeleteCard={onDeleteCard}
        onRenameColumn={onRenameColumn}
        onAddCard={onAddCard}
      />
    </div>
  );
}
