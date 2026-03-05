# Kanban MVP Execution Plan

## Phase 1: Project Baseline
- [x] Scaffold a modern Next.js app in `frontend`.
- [x] Add root-level `.gitignore` for the workspace.
- [x] Add scripts/config for lint, unit tests, and Playwright e2e.

Success criteria:
- App scaffolds and installs with current stable Next.js toolchain.
- Repository ignores build/test artifacts.
- One command each exists for lint, unit, and e2e workflows.

## Phase 2: Kanban MVP UI
- [x] Build a single-board Kanban UI with exactly 5 columns.
- [x] Implement renameable columns.
- [x] Implement card add/delete with title + details only.
- [x] Implement drag and drop between columns.
- [x] Apply the required color scheme in a polished responsive design.
- [x] Seed the board with dummy data on first render.

Success criteria:
- All business requirements in `AGENTS.md` are implemented with no extra features.
- UI is visually polished and responsive on desktop/mobile.

## Phase 3: Unit Tests
- [x] Add rigorous unit tests for board state behavior.
- [x] Add component tests for core user interactions.

Success criteria:
- Unit test suite validates rename, add, delete, and move logic.
- Tests run green from a single command.

## Phase 4: Integration Tests
- [x] Add Playwright e2e coverage for critical flows.
- [x] Validate render, rename, add, delete, and drag/drop in browser context.

Success criteria:
- Playwright suite passes headless.
- Regressions in key user journeys are caught by tests.

## Phase 5: Final Validation
- [x] Run lint + unit + e2e.
- [x] Start the dev server and keep it running for handoff.

Success criteria:
- Full quality gate passes.
- App server is running and ready to use.
