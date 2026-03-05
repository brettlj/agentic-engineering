import { memo } from "react";
import clsx from "clsx";
import { useDroppable } from "@dnd-kit/core";
import { SortableContext, verticalListSortingStrategy } from "@dnd-kit/sortable";
import type { Card, Column } from "@/lib/kanban";
import { KanbanCard } from "@/components/KanbanCard";
import { NewCardForm } from "@/components/NewCardForm";

type ColumnTint = {
  bg: string;
  dot: string;
};

type KanbanColumnProps = {
  column: Column;
  cards: Card[];
  onRename: (columnId: string, title: string) => void;
  onAddCard: (columnId: string, title: string, details: string) => void;
  onDeleteCard: (columnId: string, cardId: string) => void;
  activeCardId: string | null;
  overCardId: string | null;
  tint: ColumnTint;
};

const DropIndicator = ({ color }: { color: string }) => (
  <div className="flex items-center gap-2 px-2">
    <div className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
    <div className="h-[2px] flex-1 rounded-full" style={{ backgroundColor: color }} />
    <div className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
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
  tint,
}: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });

  const isDragging = activeCardId !== null;
  const isOverCardInThisColumn = overCardId !== null && column.cardIds.includes(overCardId);
  const isHighlighted = isDragging && (isOver || isOverCardInThisColumn);

  return (
    <section
      ref={setNodeRef}
      className={clsx(
        "flex min-h-[520px] flex-col rounded-2xl p-3.5 transition-all duration-200",
        isHighlighted && "ring-2 ring-[var(--coral)]/30"
      )}
      style={{ backgroundColor: tint.bg }}
      data-testid={`column-${column.id}`}
    >
      <div className="flex items-center gap-2 px-1">
        <span
          className="h-2.5 w-2.5 rounded-full"
          style={{ backgroundColor: tint.dot }}
        />
        <input
          value={column.title}
          onChange={(event) => onRename(column.id, event.target.value)}
          className="flex-1 bg-transparent font-display text-[15px] font-bold text-[var(--text)] outline-none"
          aria-label="Column title"
        />
        <span className="rounded-full bg-white/60 px-2 py-0.5 text-[11px] font-bold text-[var(--text-secondary)]">
          {cards.length}
        </span>
      </div>
      <div className="mt-3 flex flex-1 flex-col gap-2">
        <SortableContext items={column.cardIds} strategy={verticalListSortingStrategy}>
          {cards.map((card) => (
            <div key={card.id}>
              {overCardId === card.id && activeCardId !== card.id && (
                <div className="mb-2">
                  <DropIndicator color={tint.dot} />
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
            <DropIndicator color={tint.dot} />
          </div>
        )}
        {cards.length === 0 && (
          <div className={clsx(
            "flex flex-1 items-center justify-center rounded-xl border-2 border-dashed px-3 py-6 text-center text-[12px] font-semibold",
            isHighlighted
              ? "border-[var(--coral)]/40 text-[var(--coral)]"
              : "border-white/40 text-[var(--text-muted)]"
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
