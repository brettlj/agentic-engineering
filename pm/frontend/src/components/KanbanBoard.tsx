"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
  type DragEndEvent,
  type DragStartEvent,
} from "@dnd-kit/core";
import { AIChatSidebar, createChatMessage, type ChatMessage } from "@/components/AIChatSidebar";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { createId, moveCard, type BoardData } from "@/lib/kanban";

type BoardApiResponse = {
  board: BoardData;
  version: number;
};

type AIChatResponse = {
  assistant_message: string;
  should_update_board: boolean;
  board: BoardData;
  version: number;
};

type KanbanBoardProps = {
  onAuthExpired?: () => void;
};

export const KanbanBoard = ({ onAuthExpired }: KanbanBoardProps = {}) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [boardVersion, setBoardVersion] = useState<number | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [isLoadingBoard, setIsLoadingBoard] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [hasQueuedSaves, setHasQueuedSaves] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isAiSubmitting, setIsAiSubmitting] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);

  const boardVersionRef = useRef<number | null>(null);
  const pendingBoardRef = useRef<BoardData | null>(null);
  const saveInFlightRef = useRef(false);

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  useEffect(() => {
    boardVersionRef.current = boardVersion;
  }, [boardVersion]);

  const fetchBoard = useCallback(async () => {
    setIsLoadingBoard(true);
    setLoadError(null);

    try {
      const response = await fetch("/api/board", {
        credentials: "include",
      });
      if (response.status === 401) {
        onAuthExpired?.();
        return;
      }
      if (!response.ok) {
        throw new Error("Unable to load board.");
      }
      const data = (await response.json()) as BoardApiResponse;
      setBoard(data.board);
      setBoardVersion(data.version);
      setSaveError(null);
      setHasQueuedSaves(false);
    } catch {
      setLoadError("Unable to load board.");
    } finally {
      setIsLoadingBoard(false);
    }
  }, [onAuthExpired]);

  const flushPendingSave = useCallback(async () => {
    if (saveInFlightRef.current) {
      return;
    }
    const pendingBoard = pendingBoardRef.current;
    const expectedVersion = boardVersionRef.current;
    if (!pendingBoard || expectedVersion === null) {
      return;
    }

    saveInFlightRef.current = true;
    pendingBoardRef.current = null;
    setHasQueuedSaves(false);
    setIsSaving(true);
    setSaveError(null);

    try {
      const response = await fetch("/api/board", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          board: pendingBoard,
          expected_version: expectedVersion,
        }),
      });

      if (response.status === 401) {
        onAuthExpired?.();
        return;
      }
      if (response.status === 409) {
        setSaveError("Board changed elsewhere. Reloaded latest version.");
        await fetchBoard();
        return;
      }
      if (!response.ok) {
        throw new Error("Unable to save board.");
      }

      const data = (await response.json()) as BoardApiResponse;
      setBoardVersion(data.version);
    } catch {
      setSaveError("Unable to save changes.");
    } finally {
      saveInFlightRef.current = false;
      setIsSaving(false);
      setHasQueuedSaves(pendingBoardRef.current !== null);
      if (pendingBoardRef.current) {
        void flushPendingSave();
      }
    }
  }, [fetchBoard, onAuthExpired]);

  useEffect(() => {
    void fetchBoard();
  }, [fetchBoard]);

  const queueBoardSave = (nextBoard: BoardData) => {
    if (boardVersionRef.current === null) {
      return;
    }
    pendingBoardRef.current = nextBoard;
    setHasQueuedSaves(true);
    void flushPendingSave();
  };

  const updateBoard = (updater: (previous: BoardData) => BoardData) => {
    setBoard((previous) => {
      if (!previous) {
        return previous;
      }
      const nextBoard = updater(previous);
      queueBoardSave(nextBoard);
      return nextBoard;
    });
  };

  const cardsById = useMemo(() => board?.cards ?? {}, [board]);

  const handleDragStart = (event: DragStartEvent) => {
    setActiveCardId(event.active.id as string);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);

    if (!over || active.id === over.id) {
      return;
    }

    updateBoard((previous) => ({
      ...previous,
      columns: moveCard(previous.columns, active.id as string, over.id as string),
    }));
  };

  const handleRenameColumn = (columnId: string, title: string) => {
    updateBoard((previous) => ({
      ...previous,
      columns: previous.columns.map((column) =>
        column.id === columnId ? { ...column, title } : column
      ),
    }));
  };

  const handleAddCard = (columnId: string, title: string, details: string) => {
    const id = createId("card");
    updateBoard((previous) => ({
      ...previous,
      cards: {
        ...previous.cards,
        [id]: { id, title, details: details || "No details yet." },
      },
      columns: previous.columns.map((column) =>
        column.id === columnId
          ? { ...column, cardIds: [...column.cardIds, id] }
          : column
      ),
    }));
  };

  const handleDeleteCard = (columnId: string, cardId: string) => {
    updateBoard((previous) => ({
      ...previous,
      cards: Object.fromEntries(
        Object.entries(previous.cards).filter(([id]) => id !== cardId)
      ),
      columns: previous.columns.map((column) =>
        column.id === columnId
          ? {
              ...column,
              cardIds: column.cardIds.filter((id) => id !== cardId),
            }
          : column
      ),
    }));
  };

  const handleSubmitChat = async () => {
    const question = chatInput.trim();
    if (!question || isAiSubmitting) {
      return;
    }
    if (saveInFlightRef.current || pendingBoardRef.current || isSaving) {
      setAiError("Please wait for board changes to finish saving.");
      return;
    }

    const conversationHistory = chatMessages.map((message) => ({
      role: message.role,
      content: message.content,
    }));
    setIsAiSubmitting(true);
    setAiError(null);
    setChatInput("");
    setChatMessages((previous) => [...previous, createChatMessage("user", question)]);

    try {
      const response = await fetch("/api/ai/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          question,
          conversation_history: conversationHistory,
        }),
      });

      if (response.status === 401) {
        onAuthExpired?.();
        return;
      }
      if (!response.ok) {
        const errorPayload = (await response.json().catch(() => null)) as
          | { detail?: string }
          | null;
        const detail =
          typeof errorPayload?.detail === "string"
            ? errorPayload.detail
            : "Unable to process chat request.";
        throw new Error(detail);
      }

      const data = (await response.json()) as AIChatResponse;
      setChatMessages((previous) => [
        ...previous,
        createChatMessage("assistant", data.assistant_message),
      ]);

      if (data.should_update_board) {
        setBoard(data.board);
        setBoardVersion(data.version);
        setSaveError(null);
        if (pendingBoardRef.current) {
          // Local changes were made while AI was responding — re-queue them
          // against the new version so they aren't silently lost.
          void flushPendingSave();
        } else {
          setHasQueuedSaves(false);
        }
      }
    } catch (error) {
      setAiError(error instanceof Error ? error.message : "Unable to get AI response.");
    } finally {
      setIsAiSubmitting(false);
    }
  };

  const activeCard = activeCardId ? cardsById[activeCardId] : null;

  if (isLoadingBoard) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--surface)]">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Loading board...
        </p>
      </main>
    );
  }

  if (!board || loadError) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--surface)] px-4">
        <section className="w-full max-w-lg rounded-3xl border border-[var(--stroke)] bg-white p-8 text-center shadow-[var(--shadow)]">
          <h1 className="font-display text-3xl font-semibold text-[var(--navy-dark)]">
            Unable to load board
          </h1>
          <p className="mt-3 text-sm text-[var(--gray-text)]">
            {loadError ?? "Unable to load board."}
          </p>
          <button
            type="button"
            onClick={() => void fetchBoard()}
            className="mt-6 rounded-full bg-[var(--secondary-purple)] px-5 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white transition hover:brightness-110"
          >
            Retry
          </button>
        </section>
      </main>
    );
  }

  return (
    <div className="relative overflow-hidden">
      <div className="pointer-events-none absolute left-0 top-0 h-[420px] w-[420px] -translate-x-1/3 -translate-y-1/3 rounded-full bg-[radial-gradient(circle,_rgba(32,157,215,0.25)_0%,_rgba(32,157,215,0.05)_55%,_transparent_70%)]" />
      <div className="pointer-events-none absolute bottom-0 right-0 h-[520px] w-[520px] translate-x-1/4 translate-y-1/4 rounded-full bg-[radial-gradient(circle,_rgba(117,57,145,0.18)_0%,_rgba(117,57,145,0.05)_55%,_transparent_75%)]" />

      <main className="relative mx-auto flex min-h-screen max-w-[1500px] flex-col gap-10 px-6 pb-16 pt-12">
        <header className="flex flex-col gap-6 rounded-[32px] border border-[var(--stroke)] bg-white/80 p-8 shadow-[var(--shadow)] backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-6">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.35em] text-[var(--gray-text)]">
                Single Board Kanban
              </p>
              <h1 className="mt-3 font-display text-4xl font-semibold text-[var(--navy-dark)]">
                Kanban Studio
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-[var(--gray-text)]">
                Keep momentum visible. Rename columns, drag cards between stages,
                and capture quick notes without getting buried in settings.
              </p>
            </div>
            <div className="rounded-2xl border border-[var(--stroke)] bg-[var(--surface)] px-5 py-4">
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-[var(--gray-text)]">
                Focus
              </p>
              <p className="mt-2 text-lg font-semibold text-[var(--primary-blue)]">
                One board. Five columns. Zero clutter.
              </p>
              <p className="mt-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
                {isAiSubmitting
                  ? "AI request in progress..."
                  : isSaving
                  ? "Saving changes..."
                  : saveError
                    ? saveError
                    : "All changes saved"}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-4">
            {board.columns.map((column) => (
              <div
                key={column.id}
                className="flex items-center gap-2 rounded-full border border-[var(--stroke)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--navy-dark)]"
              >
                <span className="h-2 w-2 rounded-full bg-[var(--accent-yellow)]" />
                {column.title}
              </div>
            ))}
          </div>
        </header>

        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px] xl:items-start">
          <DndContext
            sensors={sensors}
            collisionDetection={closestCorners}
            onDragStart={handleDragStart}
            onDragEnd={handleDragEnd}
          >
            <section className="grid gap-6 lg:grid-cols-5">
              {board.columns.map((column) => (
                <KanbanColumn
                  key={column.id}
                  column={column}
                  cards={column.cardIds.map((cardId) => board.cards[cardId])}
                  onRename={handleRenameColumn}
                  onAddCard={handleAddCard}
                  onDeleteCard={handleDeleteCard}
                />
              ))}
            </section>
            <DragOverlay>
              {activeCard ? (
                <div className="w-[260px]">
                  <KanbanCardPreview card={activeCard} />
                </div>
              ) : null}
            </DragOverlay>
          </DndContext>

          <AIChatSidebar
            messages={chatMessages}
            input={chatInput}
            onInputChange={setChatInput}
            onSubmit={() => void handleSubmitChat()}
            isSubmitting={isAiSubmitting}
            isBlocked={isSaving || hasQueuedSaves}
            error={aiError}
          />
        </div>
      </main>
    </div>
  );
};
