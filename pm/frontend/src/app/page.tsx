"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type SessionResponse = {
  authenticated: boolean;
  username: string | null;
};

export default function Home() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let isActive = true;

    const checkSession = async () => {
      try {
        const response = await fetch("/api/auth/session", {
          credentials: "include",
        });
        const data = (await response.json()) as SessionResponse;
        if (!isActive) {
          return;
        }
        if (data.authenticated) {
          router.replace("/board");
          return;
        }
      } catch {
        if (isActive) {
          setError("Unable to reach the server. Please try again.");
        }
      } finally {
        if (isActive) {
          setIsLoading(false);
        }
      }
    };

    checkSession();
    return () => {
      isActive = false;
    };
  }, [router]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        setError("Invalid username or password.");
        return;
      }

      router.replace("/board");
    } catch {
      setError("Unable to sign in right now.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--bg)]">
        <p className="font-display text-base font-semibold text-[var(--text-muted)]">
          Checking session...
        </p>
      </main>
    );
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center bg-[var(--bg)] px-4 overflow-hidden">
      {/* Warm decorative blobs */}
      <div className="pointer-events-none absolute -top-32 -right-32 h-[500px] w-[500px] rounded-full bg-[var(--col-peach)] opacity-60 blur-3xl" />
      <div className="pointer-events-none absolute -bottom-40 -left-40 h-[400px] w-[400px] rounded-full bg-[var(--col-sky)] opacity-50 blur-3xl" />

      <section className="relative w-full max-w-[420px] rounded-3xl border border-[var(--border)] bg-[var(--bg-raised)] px-10 py-10 shadow-[var(--shadow-lg)]">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--coral)] text-white">
            <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <rect x="3" y="3" width="7" height="7" rx="1" />
              <rect x="14" y="3" width="7" height="7" rx="1" />
              <rect x="3" y="14" width="7" height="7" rx="1" />
              <rect x="14" y="14" width="7" height="7" rx="1" />
            </svg>
          </div>
          <h2 className="font-display text-lg font-bold text-[var(--text)]">Kanban Studio</h2>
        </div>

        <h1 className="mt-7 font-display text-2xl font-extrabold text-[var(--text)]">
          Welcome back
        </h1>
        <p className="mt-2 text-sm text-[var(--text-secondary)] leading-relaxed">
          Sign in with the MVP credentials to get started.
        </p>

        <form className="mt-7 space-y-4" onSubmit={handleSubmit}>
          <label className="block text-[13px] font-semibold text-[var(--text)]">
            Username
            <input
              className="mt-1.5 w-full rounded-xl border border-[var(--border-strong)] bg-[var(--bg)] px-3.5 py-2.5 text-sm text-[var(--text)] outline-none transition-all focus:border-[var(--coral)] focus:ring-2 focus:ring-[var(--coral-soft)]"
              name="username"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </label>

          <label className="block text-[13px] font-semibold text-[var(--text)]">
            Password
            <input
              className="mt-1.5 w-full rounded-xl border border-[var(--border-strong)] bg-[var(--bg)] px-3.5 py-2.5 text-sm text-[var(--text)] outline-none transition-all focus:border-[var(--coral)] focus:ring-2 focus:ring-[var(--coral-soft)]"
              type="password"
              name="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>

          {error ? (
            <p className="rounded-lg bg-red-50 px-3 py-2 text-sm font-medium text-red-600">{error}</p>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-xl bg-[var(--coral)] px-4 py-2.5 text-sm font-bold text-white shadow-sm transition-all hover:bg-[var(--coral-hover)] hover:shadow-md active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
