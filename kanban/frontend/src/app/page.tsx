"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import styles from "./page.module.css";
import {
  addCard,
  deleteCard,
  moveCard,
  renameColumn,
  seedColumns,
  type Column,
} from "@/lib/kanban";

type DraftCard = {
  title: string;
  details: string;
};

type DragPayload = {
  cardId: string;
  fromColumnId: string;
};

type DropPlacement = "before" | "after" | "end";

function createCardId(): string {
  const randomId = globalThis.crypto?.randomUUID?.();
  if (randomId) {
    return randomId;
  }

  return `card-${Date.now()}-${Math.floor(Math.random() * 10000)}`;
}

function getDragPayload(rawValue: string): DragPayload | null {
  try {
    return JSON.parse(rawValue) as DragPayload;
  } catch {
    return null;
  }
}

export default function Home() {
  const [columns, setColumns] = useState<Column[]>(seedColumns);
  const [activeFormColumnId, setActiveFormColumnId] = useState<string | null>(null);
  const [draftCard, setDraftCard] = useState<DraftCard>({ title: "", details: "" });
  const [dragState, setDragState] = useState<DragPayload | null>(null);
  const [dropTargetColumnId, setDropTargetColumnId] = useState<string | null>(null);
  const [dropTargetCardId, setDropTargetCardId] = useState<string | null>(null);
  const [dropPlacement, setDropPlacement] = useState<DropPlacement | null>(null);
  const [draggingCardId, setDraggingCardId] = useState<string | null>(null);
  const dragPreviewRef = useRef<HTMLElement | null>(null);

  const totalCardCount = useMemo(
    () => columns.reduce((sum, column) => sum + column.cards.length, 0),
    [columns],
  );

  function handleColumnRename(columnId: string, nextName: string) {
    setColumns((prevColumns) => renameColumn(prevColumns, columnId, nextName));
  }

  function openAddCardForm(columnId: string) {
    setActiveFormColumnId(columnId);
    setDraftCard({ title: "", details: "" });
  }

  function closeAddCardForm() {
    setActiveFormColumnId(null);
    setDraftCard({ title: "", details: "" });
  }

  function handleCardSubmit(event: FormEvent<HTMLFormElement>, columnId: string) {
    event.preventDefault();

    const trimmedTitle = draftCard.title.trim();
    const trimmedDetails = draftCard.details.trim();

    if (!trimmedTitle || !trimmedDetails) {
      return;
    }

    setColumns((prevColumns) =>
      addCard(prevColumns, columnId, {
        id: createCardId(),
        title: trimmedTitle,
        details: trimmedDetails,
      }),
    );

    closeAddCardForm();
  }

  function cleanupDragPreview() {
    if (!dragPreviewRef.current) {
      return;
    }

    dragPreviewRef.current.remove();
    dragPreviewRef.current = null;
  }

  function getCardDropPlacement(
    event: React.DragEvent<HTMLDivElement>,
  ): Exclude<DropPlacement, "end"> {
    const rect = event.currentTarget.getBoundingClientRect();
    const midpoint = rect.top + rect.height / 2;
    return event.clientY >= midpoint ? "after" : "before";
  }

  function handleDragStart(cardId: string, fromColumnId: string, event: React.DragEvent) {
    const payload = JSON.stringify({ cardId, fromColumnId });
    event.dataTransfer.setData("text/plain", payload);
    event.dataTransfer.effectAllowed = "move";
    setDragState({ cardId, fromColumnId });
    setDraggingCardId(cardId);

    if (typeof event.dataTransfer.setDragImage !== "function") {
      return;
    }

    const sourceElement = event.currentTarget as HTMLElement;
    const sourceRect = sourceElement.getBoundingClientRect();
    const preview = sourceElement.cloneNode(true) as HTMLElement;
    preview.style.position = "fixed";
    preview.style.left = "-9999px";
    preview.style.top = "-9999px";
    preview.style.width = `${sourceRect.width}px`;
    preview.style.margin = "0";
    preview.style.opacity = "0.62";
    preview.style.transform = "rotate(1deg)";
    preview.style.pointerEvents = "none";
    preview.style.zIndex = "9999";
    document.body.appendChild(preview);

    dragPreviewRef.current = preview;

    const offsetX = Math.max(0, event.clientX - sourceRect.left);
    const offsetY = Math.max(0, event.clientY - sourceRect.top);
    event.dataTransfer.setDragImage(preview, offsetX, offsetY);
  }

  function handleDragOver(event: React.DragEvent, columnId: string) {
    const eventTarget = event.target as HTMLElement | null;
    if (eventTarget?.closest('[data-testid^="card-"]')) {
      return;
    }

    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
    setDropTargetColumnId(columnId);
    setDropTargetCardId(null);
    setDropPlacement("end");
  }

  function handleDrop(event: React.DragEvent, toColumnId: string) {
    const eventTarget = event.target as HTMLElement | null;
    if (eventTarget?.closest('[data-testid^="card-"]')) {
      return;
    }

    event.preventDefault();

    const rawPayload = event.dataTransfer.getData("text/plain");
    const parsedPayload = getDragPayload(rawPayload) ?? dragState;

    if (!parsedPayload) {
      setDropTargetColumnId(null);
      return;
    }

    setColumns((prevColumns) =>
      moveCard(
        prevColumns,
        parsedPayload.fromColumnId,
        toColumnId,
        parsedPayload.cardId,
        null,
        false,
      ),
    );

    setDragState(null);
    setDraggingCardId(null);
    setDropTargetColumnId(null);
    setDropTargetCardId(null);
    setDropPlacement(null);
    cleanupDragPreview();
  }

  function handleCardDragOver(
    event: React.DragEvent,
    columnId: string,
    cardId: string,
  ) {
    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = "move";
    setDropTargetColumnId(columnId);
    setDropTargetCardId(cardId);
    setDropPlacement(getCardDropPlacement(event));
  }

  function handleCardDrop(
    event: React.DragEvent,
    toColumnId: string,
    targetCardId: string,
  ) {
    event.preventDefault();
    event.stopPropagation();

    const rawPayload = event.dataTransfer.getData("text/plain");
    const parsedPayload = getDragPayload(rawPayload) ?? dragState;

    if (!parsedPayload) {
      setDropTargetColumnId(null);
      setDropTargetCardId(null);
      setDropPlacement(null);
      return;
    }

    const placement =
      dropTargetCardId === targetCardId &&
      (dropPlacement === "before" || dropPlacement === "after")
        ? dropPlacement
        : getCardDropPlacement(event);
    const insertAfter = placement === "after";

    setColumns((prevColumns) =>
      moveCard(
        prevColumns,
        parsedPayload.fromColumnId,
        toColumnId,
        parsedPayload.cardId,
        targetCardId,
        insertAfter,
      ),
    );

    setDragState(null);
    setDraggingCardId(null);
    setDropTargetColumnId(null);
    setDropTargetCardId(null);
    setDropPlacement(null);
    cleanupDragPreview();
  }

  function clearDragState() {
    setDragState(null);
    setDraggingCardId(null);
    setDropTargetColumnId(null);
    setDropTargetCardId(null);
    setDropPlacement(null);
    cleanupDragPreview();
  }

  useEffect(() => {
    return () => {
      if (!dragPreviewRef.current) {
        return;
      }

      dragPreviewRef.current.remove();
      dragPreviewRef.current = null;
    };
  }, []);

  return (
    <div className={styles.page}>
      <main className={styles.main}>
        <header className={styles.header}>
          <p className={styles.kicker}>Single Board</p>
          <h1 className={styles.title}>Launch Control Kanban</h1>
          <p className={styles.subtitle}>
            Five focused columns. Lightweight workflow. Zero clutter.
          </p>
          <div className={styles.metrics}>
            <span>{columns.length} columns</span>
            <span>{totalCardCount} cards</span>
          </div>
        </header>

        <section className={styles.board} data-testid="board">
          {columns.map((column) => (
            <article
              key={column.id}
              className={`${styles.column} ${
                dropTargetColumnId === column.id ? styles.columnDropTarget : ""
              }`}
              data-testid={`column-${column.id}`}
              onDragOver={(event) => handleDragOver(event, column.id)}
              onDrop={(event) => handleDrop(event, column.id)}
            >
              <div className={styles.columnHeader}>
                <input
                  aria-label={`${column.id}-name`}
                  className={styles.columnNameInput}
                  value={column.name}
                  onChange={(event) =>
                    handleColumnRename(column.id, event.target.value)
                  }
                />
                <span className={styles.cardCount}>{column.cards.length}</span>
              </div>

              <div className={styles.cardStack}>
                {column.cards.map((card) => (
                  <div
                    key={card.id}
                    className={`${styles.card} ${
                      draggingCardId === card.id ? styles.cardDragging : ""
                    } ${
                      dropTargetCardId === card.id && dropPlacement === "before"
                        ? styles.cardDropBefore
                        : ""
                    } ${
                      dropTargetCardId === card.id && dropPlacement === "after"
                        ? styles.cardDropAfter
                        : ""
                    }`}
                    data-testid={`card-${card.id}`}
                    draggable
                    onDragStart={(event) =>
                      handleDragStart(card.id, column.id, event)
                    }
                    onDragOver={(event) =>
                      handleCardDragOver(event, column.id, card.id)
                    }
                    onDrop={(event) => handleCardDrop(event, column.id, card.id)}
                    onDragEnd={clearDragState}
                  >
                    <button
                      type="button"
                      className={styles.deleteButton}
                      aria-label={`Delete ${card.title}`}
                      onClick={() =>
                        setColumns((prevColumns) =>
                          deleteCard(prevColumns, column.id, card.id),
                        )
                      }
                    >
                      Delete
                    </button>
                    <h2>{card.title}</h2>
                    <p>{card.details}</p>
                  </div>
                ))}
              </div>

              {activeFormColumnId === column.id ? (
                <form
                  className={styles.addCardForm}
                  onSubmit={(event) => handleCardSubmit(event, column.id)}
                >
                  <input
                    className={styles.input}
                    placeholder="Card title"
                    value={draftCard.title}
                    onChange={(event) =>
                      setDraftCard((prevDraft) => ({
                        ...prevDraft,
                        title: event.target.value,
                      }))
                    }
                  />
                  <textarea
                    className={styles.textarea}
                    placeholder="Card details"
                    value={draftCard.details}
                    onChange={(event) =>
                      setDraftCard((prevDraft) => ({
                        ...prevDraft,
                        details: event.target.value,
                      }))
                    }
                  />
                  <div className={styles.formActions}>
                    <button type="submit" className={styles.primaryButton}>
                      Save Card
                    </button>
                    <button
                      type="button"
                      className={styles.ghostButton}
                      onClick={closeAddCardForm}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              ) : (
                <button
                  type="button"
                  className={styles.addButton}
                  onClick={() => openAddCardForm(column.id)}
                >
                  Add card
                </button>
              )}
            </article>
          ))}
        </section>
      </main>
    </div>
  );
}
