# Kanban MVP Plan

## Overview

Build a single-board Kanban web app with Next.js (client-rendered), drag-and-drop, and a polished UI using the specified color scheme. No persistence, no auth.

---

## Phase 1: Project Scaffolding

**Goal:** Establish the Next.js app structure and tooling.

| Task | Success Criteria |
|------|------------------|
| Create Next.js app in `frontend/` | `frontend/` exists with `package.json`, `next.config.js`, `app/` layout |
| Configure client rendering | App uses `"use client"` where needed; no server components for interactive UI |
| Add .gitignore entries | `.gitignore` covers `node_modules`, `.next`, `.env*`, coverage, logs |
| Add dependencies | `@dnd-kit/core`, `@dnd-kit/sortable` (or similar) for drag-and-drop; `vitest` + `@testing-library/react` for unit tests |
| Add npm scripts | `dev`, `build`, `start`, `test`, `test:watch` |

---

## Phase 2: Data Model and Dummy Data

**Goal:** Define types and seed the board with dummy data.

| Task | Success Criteria |
|------|------------------|
| Define types | `Board`, `Column`, `Card` types; columns have `id`, `title`; cards have `id`, `title`, `details`, `columnId` |
| Create dummy data | 5 columns (e.g. Backlog, To Do, In Progress, Review, Done) with 2–4 cards each |
| Export data module | Single module exports types and `initialBoard` |

---

## Phase 3: Core UI Components

**Goal:** Implement the board, columns, and cards with the design system.

| Task | Success Criteria |
|------|------------------|
| Global styles | CSS variables for Accent Yellow `#ecad0a`, Blue Primary `#209dd7`, Purple Secondary `#753991`, Dark Navy `#032147`, Gray Text `#888888` |
| Board layout | Board renders 5 columns in a horizontal layout |
| Column component | Column shows title (editable/renamable), card list, add-card control |
| Card component | Card shows title and details; delete button visible on hover or click |
| Responsive layout | Board scrolls horizontally on narrow viewports; columns have min-width |

---

## Phase 4: Interactivity

**Goal:** Implement all user actions.

| Task | Success Criteria |
|------|------------------|
| Drag and drop | Cards can be dragged between columns; state updates on drop |
| Reorder cards | Cards can be reordered within a column via drag and drop |
| Add card | "Add card" in each column opens inline form or modal; new card has title + details |
| Delete card | Delete button removes card from state |
| Rename column | Column title is editable (inline or via click); updates state |
| State management | React state (useState/useReducer) holds board; no persistence |

---

## Phase 5: Unit Testing

**Goal:** Rigorous unit tests for components and logic.

| Task | Success Criteria |
|------|------------------|
| Test utilities | Vitest + React Testing Library configured; `render` helper if needed |
| Card tests | Renders title/details; delete button triggers callback |
| Column tests | Renders cards; add-card and rename work |
| Board tests | Renders 5 columns; drag-and-drop updates order/column |
| Data/logic tests | Dummy data shape is valid; any pure helpers covered |

---

## Phase 6: Integration Testing (Playwright)

**Goal:** End-to-end flows work in a real browser.

| Task | Success Criteria |
|------|------------------|
| Playwright setup | `playwright.config.ts`; `npm run test:e2e` runs E2E tests |
| Add card flow | User can add a card to a column; card appears |
| Delete card flow | User can delete a card; card disappears |
| Rename column flow | User can rename a column; title updates |
| Drag-and-drop flow | User can drag card to another column; card moves |
| Reorder flow | User can reorder cards within a column; order persists |
| App loads with dummy data | On load, board shows 5 columns with cards |

---

## Phase 7: Polish and Delivery

**Goal:** Production-ready, server running.

| Task | Success Criteria |
|------|------------------|
| UI polish | Typography, spacing, hover states, transitions; professional look |
| README | Minimal README: how to install, run, test |
| Build passes | `npm run build` succeeds |
| Dev server runs | `npm run dev` starts server; app accessible at localhost |
| All tests pass | Unit and E2E tests green |

---

## Completion Checklist

- [x] Phase 1: Scaffolding
- [x] Phase 2: Data model
- [x] Phase 3: Core UI
- [x] Phase 4: Interactivity
- [x] Phase 5: Unit tests
- [x] Phase 6: E2E tests
- [x] Phase 7: Polish and delivery
