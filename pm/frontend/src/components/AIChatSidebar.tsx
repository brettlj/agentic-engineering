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
          className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm transition-opacity"
          onClick={onToggle}
        />
      )}

      {/* Toggle button */}
      <button
        type="button"
        onClick={onToggle}
        className={`fixed top-1/2 z-50 -translate-y-1/2 rounded-l-xl bg-[var(--secondary-purple)] px-2 py-4 text-white shadow-lg transition-all hover:brightness-110 ${isOpen ? "right-[420px]" : "right-0"}`}
        aria-label={isOpen ? "Close AI chat" : "Open AI chat"}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="20"
          height="20"
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
        className={`fixed right-0 top-0 z-50 flex h-full w-[420px] flex-col border-l border-[var(--stroke)] bg-white shadow-[-8px_0_30px_rgba(3,33,71,0.1)] transition-transform duration-300 ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-[var(--stroke)] px-6 py-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
              AI Sidebar
            </p>
            <h2 className="mt-1 font-display text-xl font-semibold text-[var(--navy-dark)]">
              Board Assistant
            </h2>
          </div>
          <button
            type="button"
            onClick={onToggle}
            className="rounded-lg p-2 text-[var(--gray-text)] transition hover:bg-[var(--surface)] hover:text-[var(--navy-dark)]"
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

        <div className="flex-1 space-y-3 overflow-y-auto px-6 py-4">
          {messages.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-[var(--stroke)] bg-[var(--surface)] px-4 py-3 text-sm text-[var(--gray-text)]">
              Start a conversation. The assistant can respond with advice and optional board updates.
            </p>
          ) : (
            messages.map((message) => (
              <article
                key={message.id}
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
          <div ref={messagesEndRef} />
        </div>

        <form className="border-t border-[var(--stroke)] px-6 py-4 space-y-3" onSubmit={handleSubmit}>
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
    </>
  );
};
