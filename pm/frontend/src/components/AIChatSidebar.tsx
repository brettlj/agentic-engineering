"use client";

import { FormEvent, useEffect, useRef } from "react";

let nextMessageId = 0;

export type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
};

export function createChatMessage(role: ChatMessage["role"], content: string): ChatMessage {
  return { id: nextMessageId++, role, content };
}

type AIChatSidebarProps = {
  messages: ChatMessage[];
  input: string;
  onInputChange: (value: string) => void;
  onSubmit: () => void;
  isSubmitting: boolean;
  isBlocked: boolean;
  error: string | null;
  isOpen: boolean;
  onToggle: () => void;
};

export const AIChatSidebar = ({
  messages,
  input,
  onInputChange,
  onSubmit,
  isSubmitting,
  isBlocked,
  error,
  isOpen,
  onToggle,
}: AIChatSidebarProps) => {
  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    onSubmit();
  };

  const canSubmit = !isSubmitting && !isBlocked && input.trim().length > 0;
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView?.({ behavior: "smooth" });
  }, [messages]);

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/10 backdrop-blur-[2px] transition-opacity"
          onClick={onToggle}
        />
      )}

      {/* Toggle button */}
      <button
        type="button"
        onClick={onToggle}
        className={`fixed top-1/2 z-50 -translate-y-1/2 rounded-l-2xl bg-[var(--coral)] px-2.5 py-4 text-white shadow-lg transition-all hover:bg-[var(--coral-hover)] ${isOpen ? "right-[420px]" : "right-0"}`}
        aria-label={isOpen ? "Close AI chat" : "Open AI chat"}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`transition-transform ${isOpen ? "rotate-180" : ""}`}
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </button>

      {/* Slide-out panel */}
      <aside
        data-testid="ai-chat-sidebar"
        className={`fixed right-0 top-0 z-50 flex h-full w-[420px] flex-col border-l border-[var(--border)] bg-[var(--bg-raised)] shadow-[-8px_0_30px_rgba(0,0,0,0.08)] transition-transform duration-300 ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-[var(--border)] px-5 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-[var(--col-lavender)]">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8B6CC1" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 2a4 4 0 0 0-4 4v2H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10a2 2 0 0 0-2-2h-2V6a4 4 0 0 0-4-4z" />
                <circle cx="9" cy="15" r="1" />
                <circle cx="15" cy="15" r="1" />
              </svg>
            </div>
            <div>
              <h2 className="font-display text-[15px] font-bold text-[var(--text)]">
                AI Assistant
              </h2>
              <p className="text-[11px] text-[var(--text-muted)]">Ask anything about your board</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onToggle}
            className="rounded-lg p-1.5 text-[var(--text-muted)] transition hover:bg-[var(--bg)] hover:text-[var(--text)]"
            aria-label="Close AI chat"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
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
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto px-5 py-4">
          {messages.length === 0 ? (
            <div className="rounded-2xl bg-[var(--col-lavender)] p-4 text-sm leading-relaxed text-[var(--text-secondary)]">
              <p className="font-semibold text-[var(--text)]">Hey there!</p>
              <p className="mt-1">I can help manage your board. Ask me to move cards, summarize progress, or suggest improvements.</p>
            </div>
          ) : (
            messages.map((message) => (
              <article
                key={message.id}
                className={`rounded-2xl px-4 py-3 text-[13px] leading-relaxed ${
                  message.role === "user"
                    ? "ml-8 bg-[var(--coral)] text-white"
                    : "mr-8 bg-[var(--bg)] text-[var(--text)]"
                }`}
              >
                <p>{message.content}</p>
              </article>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        <form className="border-t border-[var(--border)] px-5 py-4 space-y-3" onSubmit={handleSubmit}>
          <label
            htmlFor="ai-chat-input"
            className="text-[12px] font-semibold text-[var(--text-muted)]"
          >
            Message
          </label>
          <textarea
            id="ai-chat-input"
            data-testid="ai-chat-input"
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            placeholder="e.g. Summarize top risks and move blocked work to Review."
            className="h-20 w-full resize-none rounded-xl border border-[var(--border-strong)] bg-[var(--bg)] px-3.5 py-2.5 text-[13px] text-[var(--text)] outline-none transition-all focus:border-[var(--coral)] focus:ring-2 focus:ring-[var(--coral-soft)]"
            disabled={isSubmitting || isBlocked}
          />
          {error ? (
            <p className="rounded-lg bg-red-50 px-3 py-1.5 text-[12px] font-semibold text-red-500">
              {error}
            </p>
          ) : null}
          {isBlocked && !isSubmitting ? (
            <p className="text-[12px] font-medium text-[var(--text-muted)]">
              Waiting for board to finish saving...
            </p>
          ) : null}
          <button
            type="submit"
            data-testid="ai-chat-send"
            disabled={!canSubmit}
            className="w-full rounded-xl bg-[var(--coral)] px-4 py-2.5 text-[13px] font-bold text-white transition-all enabled:hover:bg-[var(--coral-hover)] enabled:active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSubmitting ? "Sending..." : "Send"}
          </button>
        </form>
      </aside>
    </>
  );
};
