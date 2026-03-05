"use client";

import { FormEvent } from "react";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type AIChatSidebarProps = {
  messages: ChatMessage[];
  input: string;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
  isSubmitting: boolean;
  isBlocked: boolean;
  error: string | null;
};

export const AIChatSidebar = ({
  messages,
  input,
  onInputChange,
  onSubmit,
  isSubmitting,
  isBlocked,
  error,
}: AIChatSidebarProps) => {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  const canSubmit = !isSubmitting && !isBlocked && input.trim().length > 0;

  return (
    <aside
      data-testid="ai-chat-sidebar"
      className="rounded-[28px] border border-[var(--stroke)] bg-white p-5 shadow-[var(--shadow)]"
    >
      <div className="border-b border-[var(--stroke)] pb-4">
        <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
          AI Sidebar
        </p>
        <h2 className="mt-2 font-display text-2xl font-semibold text-[var(--navy-dark)]">
          Ask the board assistant
        </h2>
        <p className="mt-2 text-sm leading-6 text-[var(--gray-text)]">
          Get quick guidance or request board updates directly from chat.
        </p>
      </div>

      <div className="mt-4 h-[360px] space-y-3 overflow-y-auto pr-1">
        {messages.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--gray-text)]">
            Start a conversation. The assistant can respond with advice and optional board updates.
          </p>
        ) : (
          messages.map((message, index) => (
            <article
              key={`${message.role}-${index}`}
              className={`rounded-2xl px-4 py-3 text-sm leading-6 ${
                message.role === "user"
                  ? "ml-7 border border-[var(--primary-blue)]/25 bg-[var(--primary-blue)]/10 text-[var(--navy-dark)]"
                  : "mr-7 border border-[var(--secondary-purple)]/20 bg-[var(--secondary-purple)]/10 text-[var(--navy-dark)]"
              }`}
            >
              <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                {message.role === "user" ? "You" : "Assistant"}
              </p>
              <p>{message.content}</p>
            </article>
          ))
        )}
      </div>

      <form className="mt-4 space-y-3" onSubmit={handleSubmit}>
        <label
          htmlFor="ai-chat-input"
          className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]"
        >
          Ask AI assistant
        </label>
        <textarea
          id="ai-chat-input"
          data-testid="ai-chat-input"
          value={input}
          onChange={(event) => onInputChange(event.target.value)}
          placeholder="e.g. Summarize top risks and move blocked work to Review."
          className="h-24 w-full resize-none rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-3 py-2 text-sm text-[var(--navy-dark)] outline-none transition focus:border-[var(--primary-blue)]"
          disabled={isSubmitting || isBlocked}
        />
        {error ? (
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-[#b42318]">
            {error}
          </p>
        ) : null}
        {isBlocked && !isSubmitting ? (
          <p className="text-xs font-semibold uppercase tracking-[0.15em] text-[var(--gray-text)]">
            Wait for board save to finish before submitting.
          </p>
        ) : null}
        <button
          type="submit"
          data-testid="ai-chat-send"
          disabled={!canSubmit}
          className="w-full rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white transition enabled:hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70"
        >
          {isSubmitting ? "Sending..." : "Send to AI"}
        </button>
      </form>
    </aside>
  );
};
