import type { Card } from "@/lib/kanban";

type KanbanCardPreviewProps = {
  card: Card;
};

export const KanbanCardPreview = ({ card }: KanbanCardPreviewProps) => (
  <article className="rounded-2xl border-2 border-[var(--primary-blue)]/40 bg-white px-4 py-4 shadow-[0_20px_40px_rgba(3,33,71,0.2)] rotate-[2deg] scale-105">
    <div className="flex items-start justify-between gap-3">
      <div>
        <h4 className="font-display text-base font-semibold text-[var(--navy-dark)]">
          {card.title}
        </h4>
        <p className="mt-2 text-sm leading-6 text-[var(--gray-text)]">
          {card.details}
        </p>
      </div>
    </div>
  </article>
);
