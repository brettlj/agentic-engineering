import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KanbanBoard } from "@/components/KanbanBoard";
import { initialData, type BoardData } from "@/lib/kanban";

const getFirstColumn = () => screen.getAllByTestId(/column-/i)[0];
const cloneBoard = () => structuredClone(initialData) as BoardData;
let holdAiResponse = false;
let releaseAiResponse: (() => void) | null = null;

describe("KanbanBoard", () => {
  beforeEach(() => {
    holdAiResponse = false;
    releaseAiResponse = null;
    let persistedBoard = cloneBoard();
    let version = 1;

    const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = input.toString();
      const method = init?.method ?? "GET";
      if (url.endsWith("/api/board") && method === "GET") {
        return {
          ok: true,
          status: 200,
          json: async () => ({ board: persistedBoard, version }),
        };
      }

      if (url.endsWith("/api/board") && method === "PUT") {
        const body = JSON.parse(String(init?.body ?? "{}")) as {
          board: BoardData;
          expected_version: number;
        };
        if (body.expected_version !== version) {
          return {
            ok: false,
            status: 409,
            json: async () => ({ detail: "Version mismatch." }),
          };
        }
        persistedBoard = body.board;
        version += 1;
        return {
          ok: true,
          status: 200,
          json: async () => ({ board: persistedBoard, version }),
        };
      }

      if (url.endsWith("/api/ai/chat") && method === "POST") {
        if (holdAiResponse) {
          await new Promise<void>((resolve) => {
            releaseAiResponse = resolve;
          });
        }

        const body = JSON.parse(String(init?.body ?? "{}")) as {
          question: string;
        };
        if (body.question.toLowerCase().includes("update")) {
          persistedBoard = {
            ...persistedBoard,
            columns: persistedBoard.columns.map((column, index) =>
              index === 0 ? { ...column, title: "AI Updated" } : column
            ),
          };
          version += 1;
          return {
            ok: true,
            status: 200,
            json: async () => ({
              assistant_message: "Updated your board.",
              should_update_board: true,
              board: persistedBoard,
              version,
            }),
          };
        }

        return {
          ok: true,
          status: 200,
          json: async () => ({
            assistant_message: "No update needed.",
            should_update_board: false,
            board: persistedBoard,
            version,
          }),
        };
      }

      return {
        ok: false,
        status: 404,
        json: async () => ({ detail: "Not found." }),
      };
    });

    vi.stubGlobal("fetch", fetchMock);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders five columns", async () => {
    render(<KanbanBoard />);
    expect(await screen.findAllByTestId(/column-/i)).toHaveLength(5);
  });

  it("renames a column", async () => {
    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);
    const column = getFirstColumn();
    const input = within(column).getByLabelText("Column title");
    await userEvent.clear(input);
    await userEvent.type(input, "New Name");
    expect(input).toHaveValue("New Name");
  });

  it("adds and removes a card", async () => {
    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);
    const column = getFirstColumn();
    const addButton = within(column).getByRole("button", {
      name: /add a card/i,
    });
    await userEvent.click(addButton);

    const titleInput = within(column).getByPlaceholderText(/card title/i);
    await userEvent.type(titleInput, "New card");
    const detailsInput = within(column).getByPlaceholderText(/details/i);
    await userEvent.type(detailsInput, "Notes");

    await userEvent.click(within(column).getByRole("button", { name: /add card/i }));

    expect(within(column).getByText("New card")).toBeInTheDocument();

    const deleteButton = within(column).getByRole("button", {
      name: /delete new card/i,
    });
    await userEvent.click(deleteButton);

    expect(within(column).queryByText("New card")).not.toBeInTheDocument();
  });

  it("shows assistant messages in the sidebar", async () => {
    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);

    const input = screen.getByLabelText("Ask AI assistant");
    await userEvent.type(input, "Summarize priorities");
    await userEvent.click(screen.getByRole("button", { name: /send to ai/i }));

    expect(await screen.findByText("Summarize priorities")).toBeInTheDocument();
    expect(await screen.findByText("No update needed.")).toBeInTheDocument();
  });

  it("applies ai board updates and blocks repeat submits while in flight", async () => {
    holdAiResponse = true;
    render(<KanbanBoard />);
    await screen.findAllByTestId(/column-/i);

    const input = screen.getByLabelText("Ask AI assistant");
    await userEvent.type(input, "Please update the first column");
    const sendButton = screen.getByRole("button", { name: /send to ai/i });
    await userEvent.click(sendButton);

    expect(screen.getByRole("button", { name: /sending/i })).toBeDisabled();
    releaseAiResponse?.();

    await waitFor(() =>
      expect(screen.getByDisplayValue("AI Updated")).toBeInTheDocument()
    );
    expect(await screen.findByText("Updated your board.")).toBeInTheDocument();
  });
});
