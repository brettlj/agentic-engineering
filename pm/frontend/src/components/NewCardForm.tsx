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
    <div className="mt-4">
      {isOpen ? (
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            value={formState.title}
            onChange={(event) =>
              setFormState((prev) => ({ ...prev, title: event.target.value }))
            }
            placeholder="Card title"
            className="w-full border-b border-[var(--rule-strong)] bg-transparent px-0 py-2 text-sm font-medium text-[var(--ink)] outline-none transition-colors focus:border-[var(--copper)]"
            required
          />
          <textarea
            value={formState.details}
            onChange={(event) =>
              setFormState((prev) => ({ ...prev, details: event.target.value }))
            }
            placeholder="Details"
            rows={3}
            className="w-full resize-none border-b border-[var(--rule-strong)] bg-transparent px-0 py-2 text-sm text-[var(--ink-muted)] outline-none transition-colors focus:border-[var(--copper)]"
          />
          <div className="flex items-center gap-2">
            <button
              type="submit"
              className="bg-[var(--ink)] px-4 py-2 text-[10px] font-medium tracking-[0.2em] uppercase text-[var(--cream)] transition-colors hover:bg-[var(--ink-light)]"
            >
              Add card
            </button>
            <button
              type="button"
              onClick={() => {
                setIsOpen(false);
                setFormState(initialFormState);
              }}
              className="border border-[var(--rule-strong)] px-3 py-2 text-[10px] font-medium tracking-[0.2em] uppercase text-[var(--ink-muted)] transition-colors hover:text-[var(--ink)]"
            >
              Cancel
            </button>
          </div>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          className="w-full border border-dashed border-[var(--rule-strong)] px-3 py-2 text-[10px] font-medium tracking-[0.2em] uppercase text-[var(--ink-muted)] transition-colors hover:border-[var(--copper)] hover:text-[var(--copper)]"
        >
          Add a card
        </button>
      )}
    </div>
  );
};
