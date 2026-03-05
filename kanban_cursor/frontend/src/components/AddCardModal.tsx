"use client";

import { useState, useCallback } from "react";

type AddCardModalProps = {
  columnId: string;
  columnTitle: string;
  onAdd: (columnId: string, title: string, details: string) => void;
  onClose: () => void;
};

export function AddCardModal({
  columnId,
  columnTitle,
  onAdd,
  onClose,
}: AddCardModalProps) {
  const [title, setTitle] = useState("");
  const [details, setDetails] = useState("");

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      const trimmedTitle = title.trim();
      if (trimmedTitle) {
        onAdd(columnId, trimmedTitle, details.trim());
      }
    },
    [columnId, title, details, onAdd]
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-[var(--dark-navy)]">
          Add card to {columnTitle}
        </h3>
        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label htmlFor="title" className="block text-sm text-[var(--gray-text)]">
              Title
            </label>
            <input
              id="title"
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="mt-1 w-full rounded border border-[var(--gray-text)]/30 px-3 py-2 text-[var(--dark-navy)] focus:border-[var(--blue-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--blue-primary)]"
              placeholder="Card title"
              autoFocus
              required
            />
          </div>
          <div>
            <label htmlFor="details" className="block text-sm text-[var(--gray-text)]">
              Details
            </label>
            <textarea
              id="details"
              value={details}
              onChange={(e) => setDetails(e.target.value)}
              rows={3}
              className="mt-1 w-full rounded border border-[var(--gray-text)]/30 px-3 py-2 text-[var(--dark-navy)] focus:border-[var(--blue-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--blue-primary)]"
              placeholder="Card details"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-4 py-2 text-[var(--gray-text)] hover:bg-gray-100"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="rounded-lg bg-[var(--purple-secondary)] px-4 py-2 text-white hover:opacity-90"
            >
              Add card
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
