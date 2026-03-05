import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Home from "@/app/page";

const replaceMock = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    replace: replaceMock,
  }),
}));

describe("Login page", () => {
  beforeEach(() => {
    replaceMock.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders sign in form when user is not authenticated", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.includes("/api/auth/session")) {
        return {
          ok: true,
          json: async () => ({ authenticated: false, username: null }),
        };
      }
      throw new Error(`Unexpected URL: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<Home />);

    expect(await screen.findByRole("heading", { name: "Welcome back" })).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });

  it("shows invalid credentials error on failed login", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = input.toString();
      if (url.includes("/api/auth/session")) {
        return {
          ok: true,
          json: async () => ({ authenticated: false, username: null }),
        };
      }
      if (url.includes("/api/auth/login")) {
        return {
          ok: false,
          json: async () => ({ detail: "Invalid credentials." }),
        };
      }
      throw new Error(`Unexpected URL: ${url}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<Home />);

    await screen.findByRole("heading", { name: "Welcome back" });
    await userEvent.type(screen.getByLabelText("Username"), "user");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: /^sign in$/i }));

    expect(await screen.findByText("Invalid username or password.")).toBeInTheDocument();
    expect(replaceMock).not.toHaveBeenCalled();
  });
});
