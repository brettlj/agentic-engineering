import type { Card } from "@/lib/kanban";

type KanbanCardPreviewProps = {
  card: Card;
};

export const KanbanCardPreview = ({ card }: KanbanCardPreviewProps) => (
  <article className="rounded-xl border border-[var(--coral)]/30 bg-[var(--bg-raised)] px-3.5 py-3 shadow-[var(--shadow-lg)] rotate-[2deg] scale-105">
    <div>
      <h4 className="text-[13px] font-semibold leading-snug text-[var(--text)]">
        {card.title}
      </h4>
      <p className="mt-1 text-[12px] leading-relaxed text-[var(--text-muted)]">
        {card.details}
      </p>
    </div>
  </article>
);
