import { render, screen } from "@testing-library/react";
import { Board } from "./Board";

describe("Board", () => {
  it("renders 5 columns with dummy data", () => {
    render(<Board />);
    expect(screen.getByText("Backlog")).toBeInTheDocument();
    expect(screen.getByText("To Do")).toBeInTheDocument();
    expect(screen.getByText("In Progress")).toBeInTheDocument();
    expect(screen.getByText("Review")).toBeInTheDocument();
    expect(screen.getByText("Done")).toBeInTheDocument();
  });

  it("renders cards in columns", () => {
    render(<Board />);
    expect(screen.getByText("Set up project")).toBeInTheDocument();
    expect(screen.getByText("Deploy MVP")).toBeInTheDocument();
  });
});
