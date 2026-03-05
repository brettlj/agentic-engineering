import { useState, type FormEvent } from "react";

const initialFormState = { title: "", details: "" };

type NewCardFormProps = {
  onAdd: (title: string, details: string) => void;
};

export const NewCardForm = ({ onAdd }: NewCardFormProps) => {
  const [isOpen, setIsOpen] = useState(false);
  const [formState, setFormState] = useState(initialFormState);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!formState.title.trim()) {
      return;
    }
    onAdd(formState.title.trim(), formState.details.trim());
    setFormState(initialFormState);
    setIsOpen(false);
  };

  return (
    <div className="mt-3">
      {isOpen ? (
        <form onSubmit={handleSubmit} className="space-y-2.5 rounded-xl bg-[var(--bg-raised)] p-3 shadow-[var(--shadow-sm)]">
          <input
            value={formState.title}
            onChange={(event) =>
              setFormState((prev) => ({ ...prev, title: event.target.value }))
            }
            placeholder="Card title"
            className="w-full rounded-lg border border-[var(--border-strong)] bg-[var(--bg)] px-3 py-2 text-[13px] font-medium text-[var(--text)] outline-none transition-all focus:border-[var(--coral)] focus:ring-2 focus:ring-[var(--coral-soft)]"
            required
          />
          <textarea
            value={formState.details}
            onChange={(event) =>
              setFormState((prev) => ({ ...prev, details: event.target.value }))
            }
            placeholder="Details"
            rows={2}
            className="w-full resize-none rounded-lg border border-[var(--border-strong)] bg-[var(--bg)] px-3 py-2 text-[13px] text-[var(--text-secondary)] outline-none transition-all focus:border-[var(--coral)] focus:ring-2 focus:ring-[var(--coral-soft)]"
          />
          <div className="flex items-center gap-2">
            <button
              type="submit"
              className="rounded-lg bg-[var(--coral)] px-3.5 py-1.5 text-[12px] font-bold text-white transition-all hover:bg-[var(--coral-hover)] active:scale-[0.97]"
            >
              Add card
            </button>
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                setFormState(initialFormState);
              }}
              className="rounded-lg px-3 py-1.5 text-[12px] font-semibold text-[var(--text-muted)] transition-colors hover:text-[var(--text)]"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="flex w-full items-center justify-center gap-1.5 rounded-xl border-2 border-dashed border-white/50 px-3 py-2 text-[12px] font-semibold text-[var(--text-muted)] transition-all hover:border-[var(--coral)]/30 hover:text-[var(--coral)]"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Add a card
        </button>
      )}
    </div>
  );
};
