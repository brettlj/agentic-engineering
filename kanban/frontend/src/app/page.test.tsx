import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Home from "./page";

type DataTransferMock = {
  data: Record<string, string>;
  setData: (type: string, value: string) => void;
  getData: (type: string) => string;
  effectAllowed: string;
  dropEffect: string;
};

function createDataTransfer(): DataTransferMock {
  return {
    data: {},
    setData(type: string, value: string) {
      this.data[type] = value;
    },
    getData(type: string) {
      return this.data[type] ?? "";
    },
    effectAllowed: "",
    dropEffect: "",
  };
}

describe("Home page", () => {
  it("renders exactly five columns", () => {
    render(<Home />);

    expect(screen.getAllByTestId(/column-col-/)).toHaveLength(5);
  });

  it("renames a column", async () => {
    const user = userEvent.setup();
    render(<Home />);

    const columnInput = screen.getByLabelText("col-1-name");
    await user.clear(columnInput);
    await user.type(columnInput, "Ideas");

    expect(columnInput).toHaveValue("Ideas");
  });

  it("adds and deletes a card", async () => {
    const user = userEvent.setup();
    render(<Home />);

    const backlogColumn = screen.getByTestId("column-col-1");
    await user.click(within(backlogColumn).getByRole("button", { name: "Add card" }));

    await user.type(screen.getByPlaceholderText("Card title"), "Ship final polish");
    await user.type(
      screen.getByPlaceholderText("Card details"),
      "Run final pass on spacing and hover states.",
    );

    await user.click(screen.getByRole("button", { name: "Save Card" }));

    expect(screen.getByText("Ship final polish")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Delete Ship final polish" }));

    expect(screen.queryByText("Ship final polish")).not.toBeInTheDocument();
  });

  it("moves a card between columns via drag and drop", () => {
    render(<Home />);

    const card = screen.getByTestId("card-card-1");
    const readyColumn = screen.getByTestId("column-col-2");
    const backlogColumn = screen.getByTestId("column-col-1");

    const dataTransfer = createDataTransfer();

    fireEvent.dragStart(card, { dataTransfer });
    fireEvent.dragOver(readyColumn, { dataTransfer });
    fireEvent.drop(readyColumn, { dataTransfer });

    expect(within(readyColumn).getByText("Finalize pricing page")).toBeInTheDocument();
    expect(
      within(backlogColumn).queryByText("Finalize pricing page"),
    ).not.toBeInTheDocument();
  });

  it("reorders cards within a column via drag and drop", () => {
    render(<Home />);

    const backlogColumn = screen.getByTestId("column-col-1");
    const sourceCard = within(backlogColumn).getByTestId("card-card-2");
    const targetCard = within(backlogColumn).getByTestId("card-card-1");
    const dataTransfer = createDataTransfer();
    const rectSpy = vi.spyOn(targetCard, "getBoundingClientRect").mockReturnValue({
      x: 0,
      y: 0,
      width: 120,
      height: 40,
      top: 0,
      left: 0,
      right: 120,
      bottom: 40,
      toJSON: () => ({}),
    });

    fireEvent.dragStart(sourceCard, { dataTransfer });
    fireEvent.dragOver(targetCard, { dataTransfer, clientY: 1 });
    fireEvent.drop(targetCard, { dataTransfer, clientY: 1 });

    const orderedTitles = within(backlogColumn)
      .getAllByRole("heading", { level: 2 })
      .map((heading) => heading.textContent);

    expect(orderedTitles).toEqual([
      "Collect launch screenshots",
      "Finalize pricing page",
    ]);

    rectSpy.mockRestore();
  });

});
