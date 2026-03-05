"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  DragOverlay,
  PointerSensor,
  useSensor,
  useSensors,
  pointerWithin,
  closestCenter,
  type DragEndEvent,
  type DragStartEvent,
  type DragOverEvent,
  type CollisionDetection,
} from "@dnd-kit/core";
import { AIChatSidebar, createChatMessage, type ChatMessage } from "@/components/AIChatSidebar";
import { KanbanColumn } from "@/components/KanbanColumn";
import { KanbanCardPreview } from "@/components/KanbanCardPreview";
import { createId, moveCard, type BoardData, type Column } from "@/lib/kanban";

const columnAwareCollision: CollisionDetection = (args) => {
  const pointerCollisions = pointerWithin(args);
  if (pointerCollisions.length > 0) {
    return pointerCollisions;
  }
  return closestCenter(args);
};

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

const COLUMN_ACCENTS = [
  "var(--copper)",
  "var(--sage)",
  "var(--ink-muted)",
  "#6366F1",
];

export const KanbanBoard = ({ onAuthExpired }: KanbanBoardProps = {}) => {
  const [board, setBoard] = useState<BoardData | null>(null);
  const [boardVersion, setBoardVersion] = useState<number | null>(null);
  const [activeCardId, setActiveCardId] = useState<string | null>(null);
  const [overCardId, setOverCardId] = useState<string | null>(null);
  const [isLoadingBoard, setIsLoadingBoard] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [hasQueuedSaves, setHasQueuedSaves] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState("");
  const [isAiSubmitting, setIsAiSubmitting] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [isChatOpen, setIsChatOpen] = useState(false);

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

  const handleDragOver = (event: DragOverEvent) => {
    setOverCardId(event.over?.id as string | null);
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveCardId(null);
    setOverCardId(null);

    if (!over || active.id === over.id) {
      return;
    }

    updateBoard((previous) => ({
      ...previous,
      columns: moveCard(previous.columns, active.id as string, over.id as string),
    }));
  };

  const handleDragCancel = () => {
    setActiveCardId(null);
    setOverCardId(null);
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
      <main className="flex min-h-screen items-center justify-center bg-[var(--cream)]">
        <p className="font-display text-lg italic text-[var(--ink-muted)]">
          Loading board...
        </p>
      </main>
    );
  }

  if (!board || loadError) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--cream)] px-4">
        <section className="w-full max-w-lg border border-[var(--rule-strong)] bg-[var(--paper)] p-10 text-center shadow-[var(--shadow-warm)]">
          <h1 className="font-display text-3xl text-[var(--ink)]">
            Unable to load board
          </h1>
          <p className="mt-3 text-sm text-[var(--ink-muted)]">
            {loadError ?? "Unable to load board."}
          </p>
          <button
            type="button"
            onClick={() => void fetchBoard()}
            className="mt-6 bg-[var(--ink)] px-5 py-2.5 text-[11px] font-medium tracking-[0.2em] uppercase text-[var(--cream)] transition-colors hover:bg-[var(--ink-light)]"
          >
            Retry
          </button>
        </section>
      </main>
    );
  }

  const statusText = isAiSubmitting
    ? "AI is thinking..."
    : isSaving
    ? "Saving..."
    : saveError
      ? saveError
      : "Saved";

  return (
    <div className="relative overflow-hidden">
      <main className="relative mx-auto flex min-h-screen flex-col gap-6 px-6 pb-16 pt-6">
        <header className="flex items-center justify-between gap-6 border-b border-[var(--rule)] pb-5">
          <div className="flex items-center gap-8">
            <div>
              <h1 className="font-display text-3xl text-[var(--ink)]">
                Kanban Studio
              </h1>
              <p className="mt-1 text-[11px] font-medium tracking-[0.1em] uppercase text-[var(--ink-muted)]">
                {statusText}
              </p>
            </div>
            <div className="hidden items-center gap-3 md:flex">
              {board.columns.map((column, index) => (
                <div
                  key={column.id}
                  className="flex items-center gap-2 text-[11px] font-medium tracking-[0.1em] uppercase text-[var(--ink-muted)]"
                >
                  <span
                    className="h-2 w-2 rounded-full"
                    style={{ backgroundColor: COLUMN_ACCENTS[index % COLUMN_ACCENTS.length] }}
                  />
                  {column.title}
                  <span className="font-bold text-[var(--ink-light)]">{column.cardIds.length}</span>
                </div>
              ))}
            </div>
          </div>
        </header>

        <DndContext
          sensors={sensors}
          collisionDetection={columnAwareCollision}
          onDragStart={handleDragStart}
          onDragOver={handleDragOver}
          onDragEnd={handleDragEnd}
          onDragCancel={handleDragCancel}
        >
          <section className="grid auto-cols-fr grid-flow-col gap-5">
            {board.columns.map((column, index) => (
              <KanbanColumn
                key={column.id}
                column={column}
                cards={column.cardIds.map((cardId) => board.cards[cardId])}
                onRename={handleRenameColumn}
                onAddCard={handleAddCard}
                onDeleteCard={handleDeleteCard}
                activeCardId={activeCardId}
                overCardId={overCardId}
                accentColor={COLUMN_ACCENTS[index % COLUMN_ACCENTS.length]}
              />
            ))}
          </section>
          <DragOverlay dropAnimation={null}>
            {activeCard ? (
              <div className="w-[240px] cursor-grabbing">
                <KanbanCardPreview card={activeCard} />
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </main>

      <AIChatSidebar
        messages={chatMessages}
        input={chatInput}
        onInputChange={setChatInput}
        onSubmit={() => void handleSubmitChat()}
        isSubmitting={isAiSubmitting}
        isBlocked={isSaving || hasQueuedSaves}
        error={aiError}
        isOpen={isChatOpen}
        onToggle={() => setIsChatOpen((prev) => !prev)}
      />
    </div>
  );
};
