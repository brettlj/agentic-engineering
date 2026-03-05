import { render, screen, fireEvent } from "@testing-library/react";
import { DndContext } from "@dnd-kit/core";
import { Column } from "./Column";

const column = { id: "col-1", title: "Backlog" };
const cards = [
  {
    id: "card-1",
    title: "Card 1",
    details: "Details 1",
    columnId: "col-1",
  },
];

function wrapWithDnd(children: React.ReactNode) {
  return (
    <DndContext onDragEnd={() => {}} onDragOver={() => {}}>
      {children}
    </DndContext>
  );
}

describe("Column", () => {
  it("renders column title and cards", () => {
    render(
      wrapWithDnd(
        <Column
          column={column}
          cards={cards}
          onDeleteCard={() => {}}
          onRenameColumn={() => {}}
          onAddCard={() => {}}
        />
      )
    );
    expect(screen.getByText("Backlog")).toBeInTheDocument();
    expect(screen.getByText("Card 1")).toBeInTheDocument();
  });

  it("calls onAddCard when Add card is clicked", () => {
    const onAddCard = vi.fn();
    render(
      wrapWithDnd(
        <Column
          column={column}
          cards={[]}
          onDeleteCard={() => {}}
          onRenameColumn={() => {}}
          onAddCard={onAddCard}
        />
      )
    );
    fireEvent.click(screen.getByText("Add card"));
    expect(onAddCard).toHaveBeenCalledWith("col-1");
  });

  it("allows renaming column", async () => {
    const onRenameColumn = vi.fn();
    render(
      wrapWithDnd(
        <Column
          column={column}
          cards={[]}
          onDeleteCard={() => {}}
          onRenameColumn={onRenameColumn}
          onAddCard={() => {}}
        />
      )
    );
    fireEvent.click(screen.getByText("Backlog"));
    const input = screen.getByRole("textbox");
    fireEvent.change(input, { target: { value: "New Title" } });
    fireEvent.blur(input);
    expect(onRenameColumn).toHaveBeenCalledWith("col-1", "New Title");
  });
});
