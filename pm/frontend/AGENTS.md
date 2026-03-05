# Frontend architecture overview

## Purpose

The frontend is a Next.js App Router application that provides an MVP login flow and a persistent kanban experience ("Kanban Studio"). Session/authentication checks and board persistence are backend-driven.

## Tech stack

- Framework: Next.js (App Router)
- UI: React + TypeScript
- Styling: Tailwind CSS v4 + CSS variables in `src/app/globals.css`
- Drag and drop: `@dnd-kit` (`core`, `sortable`, `utilities`)
- Testing:
  - Unit/component: Vitest + Testing Library (`src/**/*.test.ts(x)`)
  - Browser e2e: Playwright (`tests/`)

## Runtime architecture

- Entry routes:
  - `src/app/page.tsx` renders the login experience.
  - `src/app/board/page.tsx` renders the authenticated kanban experience.
- App shell:
  - `src/app/layout.tsx` sets metadata, global fonts, and root layout.
  - `src/app/globals.css` defines the design tokens and base styles.
- Feature composition:
  - `KanbanBoard` is the stateful orchestrator for board data and drag/drop events.
  - `AIChatSidebar` renders chat history, input, submit state, and errors.
  - `KanbanColumn` renders one column, title editing, card list, and add-card form.
  - `KanbanCard` renders sortable card UI with delete action.
  - `NewCardForm` handles card creation UX per column.
  - `KanbanCardPreview` renders drag overlay content.

## State and data model

- Domain model lives in `src/lib/kanban.ts`:
  - `Card`, `Column`, and `BoardData` types.
  - `initialData` demo board seed.
  - `moveCard` utility for intra/inter-column drag reordering.
  - `createId` helper for new card IDs.
- Current state ownership:
  - `KanbanBoard` holds the active board state in React local state as a client cache.
  - Child components receive data + callbacks via props.

## Interaction flow

- Login page calls backend auth session and login endpoints.
- Board page checks backend session before rendering board and supports logout.
- `KanbanBoard` fetches board data from `/api/board` after load.
- `KanbanBoard` persists board edits through `/api/board` with optimistic version checks.
- `KanbanBoard` wires `DndContext` and tracks active drag card.
- Column title edits, card add/delete, and card moves update local state and then sync to backend.
- Loading, saving, and error states are rendered in the board UI.
- Sidebar chat posts to `/api/ai/chat` with question + conversation history.
- AI responses render assistant messages and can return a full board snapshot update.
- While AI work is in-flight, chat submit is blocked to avoid race-condition writes.

## Testing architecture

- Unit/component:
  - Business logic tests for board operations (`src/lib/kanban.test.ts`).
  - Component behavior tests (`src/components/KanbanBoard.test.tsx`).
  - Login page behavior tests (`src/app/page.test.tsx`).
- E2E:
  - Auth gating, invalid login, logout, persistent kanban interactions, and sidebar AI chat flow (`tests/kanban.spec.ts`).
- Config:
  - Vitest config in `vitest.config.ts`.
  - Playwright config in `playwright.config.ts`.

## Boundaries for upcoming phases

- Keep UI behavior and visual design stable while evolving the API contract.
- Preserve optimistic update behavior and conflict handling as backend capabilities expand.
- Preserve current test intent while adding backend-integrated integration/regression/e2e coverage.
