export type Card = {
  id: string;
  title: string;
  details: string;
  columnId: string;
};

export type Column = {
  id: string;
  title: string;
};

export type Board = {
  columns: Column[];
  cards: Card[];
};

export const initialBoard: Board = {
  columns: [
    { id: "col-1", title: "Backlog" },
    { id: "col-2", title: "To Do" },
    { id: "col-3", title: "In Progress" },
    { id: "col-4", title: "Review" },
    { id: "col-5", title: "Done" },
  ],
  cards: [
    { id: "card-1", title: "Set up project", details: "Initialize repo and dependencies", columnId: "col-1" },
    { id: "card-2", title: "Design mockups", details: "Create wireframes for main views", columnId: "col-1" },
    { id: "card-3", title: "Build board layout", details: "Implement column and card components", columnId: "col-2" },
    { id: "card-4", title: "Add drag and drop", details: "Integrate dnd-kit for card movement", columnId: "col-2" },
    { id: "card-5", title: "Implement card CRUD", details: "Add, edit, delete cards", columnId: "col-3" },
    { id: "card-6", title: "Style components", details: "Apply design system and polish", columnId: "col-3" },
    { id: "card-7", title: "Write tests", details: "Unit and E2E test coverage", columnId: "col-4" },
    { id: "card-8", title: "Fix bugs", details: "Address review feedback", columnId: "col-4" },
    { id: "card-9", title: "Deploy MVP", details: "Ship to production", columnId: "col-5" },
    { id: "card-10", title: "Documentation", details: "Update README and docs", columnId: "col-5" },
  ],
};
