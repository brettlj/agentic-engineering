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
  accentColor: string;
};

const DropIndicator = ({ color }: { color: string }) => (
  <div className="flex items-center gap-2 px-1">
    <div className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
    <div className="h-px flex-1" style={{ backgroundColor: color }} />
    <div className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
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
  accentColor,
}: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: column.id });

  const isDragging = activeCardId !== null;
  const isOverCardInThisColumn = overCardId !== null && column.cardIds.includes(overCardId);
  const isHighlighted = isDragging && (isOver || isOverCardInThisColumn);

  return (
    <section
      ref={setNodeRef}
      className={clsx(
        "flex min-h-[520px] flex-col bg-[var(--cream-dark)]/60 p-4 transition-all duration-200",
        isHighlighted && "bg-[var(--copper-glow)]"
      )}
      style={{
        borderTop: `2px solid ${accentColor}`,
      }}
      data-testid={`column-${column.id}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="w-full">
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-[var(--ink-muted)]">
              {cards.length} {cards.length === 1 ? "card" : "cards"}
            </span>
          </div>
          <input
            value={column.title}
            onChange={(event) => onRename(column.id, event.target.value)}
            className="mt-1 w-full bg-transparent font-display text-xl text-[var(--ink)] outline-none"
            aria-label="Column title"
          />
        </div>
      </div>
      <div className="mt-4 flex flex-1 flex-col gap-2.5">
        <SortableContext items={column.cardIds} strategy={verticalListSortingStrategy}>
          {cards.map((card) => (
            <div key={card.id}>
              {overCardId === card.id && activeCardId !== card.id && (
                <div className="mb-2">
                  <DropIndicator color={accentColor} />
                </div>
              )}
              <KanbanCard
                card={card}
                onDelete={(cardId) => onDeleteCard(column.id, cardId)}
                accentColor={accentColor}
              />
            </div>
          ))}
        </SortableContext>
        {isOver && isDragging && !isOverCardInThisColumn && (
          <div className="mt-1">
            <DropIndicator color={accentColor} />
          </div>
        )}
        {cards.length === 0 && (
          <div className={clsx(
            "flex flex-1 items-center justify-center border border-dashed px-3 py-6 text-center text-[11px] font-medium tracking-[0.15em] uppercase",
            isHighlighted
              ? "border-[var(--copper)] text-[var(--copper)]"
              : "border-[var(--rule-strong)] text-[var(--ink-muted)]"
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
