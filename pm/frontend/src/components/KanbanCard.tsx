import { useState } from "react";
import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import clsx from "clsx";
import type { Card } from "@/lib/kanban";

type KanbanCardProps = {
  card: Card;
  onDelete: (cardId: string) => void;
};

export const KanbanCard = ({ card, onDelete }: KanbanCardProps) => {
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
        "group rounded-xl border border-[var(--border)] bg-[var(--bg-raised)] px-3.5 py-3 shadow-[var(--shadow-sm)]",
        "transition-all duration-150 hover:shadow-[var(--shadow-md)] hover:-translate-y-0.5",
        isDragging && "opacity-30 ring-2 ring-[var(--coral)]/20"
      )}
      {...attributes}
      {...listeners}
      data-testid={`card-${card.id}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <h4 className="text-[13px] font-semibold leading-snug text-[var(--text)]">
            {card.title}
          </h4>
          <p className="mt-1 text-[12px] leading-relaxed text-[var(--text-muted)]">
            {card.details}
          </p>
        </div>
        {confirmingDelete ? (
          <div className="flex gap-1">
            <button
              type="button"
              onClick={() => onDelete(card.id)}
              className="rounded-lg bg-red-50 px-2 py-1 text-[11px] font-bold text-red-500 transition hover:bg-red-100"
              aria-label={`Confirm delete ${card.title}`}
            >
              Yes
            </button>
            <button
              type="button"
              onClick={() => setConfirmingDelete(false)}
              className="rounded-lg bg-[var(--bg)] px-2 py-1 text-[11px] font-bold text-[var(--text-muted)] transition hover:text-[var(--text)]"
            >
              No
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setConfirmingDelete(true)}
            className="flex-shrink-0 rounded-lg p-1 text-[var(--text-muted)] opacity-0 transition group-hover:opacity-100 hover:bg-red-50 hover:text-red-400"
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
