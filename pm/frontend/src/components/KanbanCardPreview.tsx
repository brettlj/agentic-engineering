import type { Card } from "@/lib/kanban";

type KanbanCardPreviewProps = {
  card: Card;
};

export const KanbanCardPreview = ({ card }: KanbanCardPreviewProps) => (
  <article className="bg-[var(--paper)] px-4 py-3.5 shadow-[var(--shadow-lifted)] rotate-[1.5deg] scale-105 border-l-[3px] border-[var(--copper)]">
    <div className="flex items-start justify-between gap-3 pl-2">
      <div>
        <h4 className="text-sm font-medium text-[var(--ink)]">
          {card.title}
        </h4>
        <p className="mt-1.5 text-[13px] leading-relaxed text-[var(--ink-muted)]">
          {card.details}
        </p>
      </div>
    </div>
  </article>
);
