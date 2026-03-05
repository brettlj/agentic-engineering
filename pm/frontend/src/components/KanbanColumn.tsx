import { memo } from "react";
import clsx from "clsx";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { Card, Column } from "@/lib/kanban";
import { KanbanCard } from "@/components/KanbanCard";
import { NewCardForm } from "@/components/NewCardForm";

type KanbanColumnProps = {
  column: Column;
  cards: Card[];
  onRename: (columnId: string, title: string) => void;
  onAddCard: (columnId: string, title: string, details: string) => void;
  onDeleteCard: (columnId: string, cardId: string) => void;
  activeCardId: string | null;
  overCardId: string | null;
};

const DropIndicator = () => (
  <div className="flex items-center gap-2 px-1">
    <div className="h-2 w-2 rounded-full bg-[var(--primary-blue)]" />
    <div className="h-0.5 flex-1 rounded-full bg-[var(--primary-blue)]" />
    <div className="h-2 w-2 rounded-full bg-[var(--primary-blue)]" />
  </div>
);

export const KanbanColumn = memo(function KanbanColumn({
  column,
  cards,
  onRename,
  onAddCard,
  onDeleteCard,
  activeCardId,
  overCardId,
}: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });

  const isDragging = activeCardId !== null;
  const isOverCardInThisColumn = overCardId !== null && column.cardIds.includes(overCardId);
  const isHighlighted = isDragging && (isOver || isOverCardInThisColumn);

  return (
    <section
      ref={setNodeRef}
      className={clsx(
        "flex min-h-[520px] flex-col rounded-2xl border border-[var(--stroke)] bg-[var(--surface-strong)] p-3 shadow-[var(--shadow)] transition-all duration-200",
        isHighlighted && "border-[var(--primary-blue)]/40 bg-[var(--primary-blue)]/[0.03]"
      )}
      data-testid={`column-${column.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="w-full">
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-8 rounded-full bg-[var(--accent-yellow)]" />
            <span className="text-[11px] font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)]">
              {cards.length} cards
            </span>
          </div>
          <input
            value={column.title}
            onChange={(event) => onRename(column.id, event.target.value)}
            className="mt-2 w-full bg-transparent font-display text-base font-semibold text-[var(--navy-dark)] outline-none"
            aria-label="Column title"
          />
        </div>
      </div>
      <div className="mt-3 flex flex-1 flex-col gap-2">
        <SortableContext items={column.cardIds} strategy={verticalListSortingStrategy}>
          {cards.map((card) => (
            <div key={card.id}>
              {overCardId === card.id && activeCardId !== card.id && (
                <div className="mb-2">
                  <DropIndicator />
                </div>
              )}
              <KanbanCard
                card={card}
                onDelete={(cardId) => onDeleteCard(column.id, cardId)}
              />
            </div>
          ))}
        </SortableContext>
        {isOver && isDragging && !isOverCardInThisColumn && (
          <div className="mt-1">
            <DropIndicator />
          </div>
        )}
        {cards.length === 0 && (
          <div className={clsx(
            "flex flex-1 items-center justify-center rounded-2xl border border-dashed px-3 py-6 text-center text-xs font-semibold uppercase tracking-[0.2em]",
            isHighlighted
              ? "border-[var(--primary-blue)]/40 text-[var(--primary-blue)]"
              : "border-[var(--stroke)] text-[var(--gray-text)]"
          )}>
            Drop a card here
          </div>
        )}
      </div>
      <NewCardForm
        onAdd={(title, details) => onAddCard(column.id, title, details)}
      />
    </section>
  );
});
