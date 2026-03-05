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
          className="fixed inset-0 z-40 bg-[var(--ink)]/30 backdrop-blur-sm transition-opacity"
          onClick={onToggle}
        />
      )}

      {/* Toggle button */}
      <button
        type="button"
        onClick={onToggle}
        className={`fixed top-1/2 z-50 -translate-y-1/2 bg-[var(--sidebar-bg)] px-2 py-5 text-[var(--sidebar-text)] shadow-lg transition-all hover:bg-[var(--sidebar-surface)] ${isOpen ? "right-[420px]" : "right-0"}`}
        aria-label={isOpen ? "Close AI chat" : "Open AI chat"}
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`transition-transform ${isOpen ? "rotate-180" : ""}`}
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </button>

      {/* Slide-out panel -- dark editorial sidebar */}
      <aside
        data-testid="ai-chat-sidebar"
        className={`fixed right-0 top-0 z-50 flex h-full w-[420px] flex-col bg-[var(--sidebar-bg)] shadow-[-12px_0_40px_rgba(0,0,0,0.3)] transition-transform duration-300 ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
      >
        <div className="flex items-center justify-between border-b border-[var(--sidebar-border)] px-6 py-5">
          <div>
            <p className="text-[10px] font-medium tracking-[0.3em] uppercase text-[var(--sidebar-muted)]">
              AI Assistant
            </p>
            <h2 className="mt-1 font-display text-2xl text-[var(--sidebar-text)]">
              Board Chat
            </h2>
          </div>
          <button
            type="button"
            onClick={onToggle}
            className="p-2 text-[var(--sidebar-muted)] transition hover:text-[var(--sidebar-text)]"
            aria-label="Close AI chat"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="flex-1 space-y-3 overflow-y-auto px-6 py-5">
          {messages.length === 0 ? (
            <p className="border border-dashed border-[var(--sidebar-border)] px-4 py-3 text-sm leading-relaxed text-[var(--sidebar-muted)]">
              Start a conversation. The assistant can respond with advice and optional board updates.
            </p>
          ) : (
            messages.map((message) => (
              <article
                key={message.id}
                className={`px-4 py-3 text-sm leading-relaxed ${
                  message.role === "user"
                    ? "ml-6 border-l-2 border-[var(--copper)] bg-[var(--copper)]/10 text-[var(--sidebar-text)]"
                    : "mr-6 border-l-2 border-[var(--sage-light)] bg-white/5 text-[var(--sidebar-text)]"
                }`}
              >
                <p className="mb-1.5 text-[10px] font-medium tracking-[0.25em] uppercase text-[var(--sidebar-muted)]">
                  {message.role === "user" ? "You" : "Assistant"}
                </p>
                <p>{message.content}</p>
              </article>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        <form className="border-t border-[var(--sidebar-border)] px-6 py-5 space-y-3" onSubmit={handleSubmit}>
          <label
            htmlFor="ai-chat-input"
            className="text-[10px] font-medium tracking-[0.25em] uppercase text-[var(--sidebar-muted)]"
          >
            Message
          </label>
          <textarea
            id="ai-chat-input"
            data-testid="ai-chat-input"
            value={input}
            onChange={(event) => onInputChange(event.target.value)}
            placeholder="e.g. Summarize top risks and move blocked work to Review."
            className="h-24 w-full resize-none border border-[var(--sidebar-border)] bg-[var(--sidebar-surface)] px-3 py-2.5 text-sm text-[var(--sidebar-text)] outline-none transition-colors focus:border-[var(--copper)]/50 placeholder:text-[var(--sidebar-muted)]/50"
            disabled={isSubmitting || isBlocked}
          />
          {error ? (
            <p className="text-[11px] font-medium tracking-wider uppercase text-[#EF4444]">
              {error}
            </p>
          ) : null}
          {isBlocked && !isSubmitting ? (
            <p className="text-[11px] font-medium tracking-wider uppercase text-[var(--sidebar-muted)]">
              Wait for board save to finish before submitting.
            </p>
          ) : null}
          <button
            type="submit"
            data-testid="ai-chat-send"
            disabled={!canSubmit}
            className="w-full bg-[var(--copper)] px-4 py-2.5 text-[10px] font-medium tracking-[0.25em] uppercase text-white transition-colors enabled:hover:bg-[var(--copper-light)] disabled:cursor-not-allowed disabled:opacity-40"
          >
            {isSubmitting ? "Sending..." : "Send"}
          </button>
        </form>
      </aside>
    </>
  );
};
