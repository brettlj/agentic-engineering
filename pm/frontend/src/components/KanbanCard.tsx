import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";

type KanbanCardProps = {
  card: Card;
  onDelete: (cardId: string) => void;
  accentColor: string;
};

export const KanbanCard = ({ card, onDelete, accentColor }: KanbanCardProps) => {
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: card.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  return (
    <article
      ref={setNodeRef}
      style={style}
      className={clsx(
        "group relative bg-[var(--paper)] px-4 py-3.5 shadow-[0_1px_3px_rgba(28,25,23,0.06)]",
        "transition-all duration-150 hover:shadow-[var(--shadow-warm)]",
        isDragging && "opacity-30"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      {/* Left accent bar */}
      <div
        className="absolute left-0 top-2 bottom-2 w-[3px] rounded-r-full opacity-50 transition-opacity group-hover:opacity-100"
        style={{ backgroundColor: accentColor }}
      />

      <div className="flex items-start justify-between gap-3 pl-2">
        <div className="min-w-0 flex-1">
          <h4 className="text-sm font-medium text-[var(--ink)]">
            {card.title}
          </h4>
          <p className="mt-1.5 text-[13px] leading-relaxed text-[var(--ink-muted)]">
            {card.details}
          </p>
        </div>
        {confirmingDelete ? (
          <div className="flex gap-1">
            <button
              type="button"
              onClick={() => onDelete(card.id)}
              className="border border-[#B91C1C]/20 bg-[#B91C1C]/5 px-2 py-1 text-[10px] font-bold tracking-wider uppercase text-[#B91C1C] transition hover:bg-[#B91C1C]/10"
              aria-label={`Confirm delete ${card.title}`}
            >
              Yes
            </button>
            <button
              type="button"
              onClick={() => setConfirmingDelete(false)}
              className="border border-[var(--rule)] px-2 py-1 text-[10px] font-bold tracking-wider uppercase text-[var(--ink-muted)] transition hover:text-[var(--ink)]"
            >
              No
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setConfirmingDelete(true)}
            className="flex-shrink-0 p-1.5 text-[var(--ink-muted)] opacity-0 transition group-hover:opacity-100 hover:text-[#B91C1C]"
            aria-label={`Delete ${card.title}`}
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        )}
      </div>
    </article>
  );
};
