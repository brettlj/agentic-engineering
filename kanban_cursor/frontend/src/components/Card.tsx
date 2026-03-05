"use client";

import type { Card as CardType } from "@/data/board";

type CardProps = {
  card: CardType;
  onDelete: (id: string) => void;
  isDragging?: boolean;
  attributes?: Record<string, unknown>;
  listeners?: Record<string, unknown>;
  setNodeRef?: (node: HTMLElement | null) => void;
  style?: React.CSSProperties;
};

export function Card({
  card,
  onDelete,
  isDragging,
  attributes,
  listeners,
  setNodeRef,
  style,
}: CardProps) {
  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`
        group relative cursor-grab rounded-lg border-l-4 border-[var(--accent-yellow)] bg-white p-3 shadow-sm
        transition-all duration-150 hover:shadow-md active:cursor-grabbing
        ${isDragging ? "opacity-70 shadow-lg ring-2 ring-[var(--blue-primary)]" : ""}
      `}
    >
      <h3 className="font-semibold text-[var(--dark-navy)]">{card.title}</h3>
      {card.details && (
        <p className="mt-1 text-sm text-[var(--gray-text)]">{card.details}</p>
      )}
      <button
        type="button"
        onClick={() => onDelete(card.id)}
        className="absolute right-2 top-2 rounded p-1 text-[var(--gray-text)] opacity-0 transition-opacity hover:bg-red-100 hover:text-red-600 group-hover:opacity-100"
        aria-label={`Delete ${card.title}`}
      >
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M3 6h18" />
          <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
          <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
          <line x1="10" y1="11" x2="10" y2="17" />
          <line x1="14" y1="11" x2="14" y2="17" />
        </svg>
      </button>
    </div>
  );
}
