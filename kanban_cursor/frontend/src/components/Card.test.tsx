import { render, screen, fireEvent } from "@testing-library/react";
import { Card } from "./Card";

describe("Card", () => {
  const card = {
    id: "card-1",
    title: "Test Card",
    details: "Test details",
    columnId: "col-1",
  };

  it("renders title and details", () => {
    render(<Card card={card} onDelete={() => {}} />);
    expect(screen.getByText("Test Card")).toBeInTheDocument();
    expect(screen.getByText("Test details")).toBeInTheDocument();
  });

  it("renders without details when empty", () => {
    const cardNoDetails = { ...card, details: "" };
    render(<Card card={cardNoDetails} onDelete={() => {}} />);
    expect(screen.getByText("Test Card")).toBeInTheDocument();
    expect(screen.queryByText("Test details")).not.toBeInTheDocument();
  });

  it("calls onDelete when delete button is clicked", () => {
    const onDelete = vi.fn();
    render(<Card card={card} onDelete={onDelete} />);
    fireEvent.click(screen.getByLabelText("Delete Test Card"));
    expect(onDelete).toHaveBeenCalledWith("card-1");
  });
});
