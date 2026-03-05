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
      <main className="flex min-h-screen items-center justify-center bg-[var(--cream)]">
        <p className="font-display text-lg italic text-[var(--ink-muted)]">
          Checking session...
        </p>
      </main>
    );
  }

  return (
    <main className="relative flex min-h-screen items-center justify-center bg-[var(--cream)] px-4 overflow-hidden">
      {/* Decorative ruled lines */}
      <div className="pointer-events-none absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: "repeating-linear-gradient(0deg, transparent, transparent 31px, var(--ink) 31px, var(--ink) 32px)",
      }} />
      {/* Copper margin line */}
      <div className="pointer-events-none absolute top-0 bottom-0 left-[12%] w-px bg-[var(--copper)] opacity-[0.08]" />

      <section className="relative w-full max-w-[400px] rounded-sm border border-[var(--rule-strong)] bg-[var(--paper)] px-10 py-12 shadow-[var(--shadow-warm)]">
        {/* Top edge detail */}
        <div className="absolute top-0 left-6 right-6 h-px bg-gradient-to-r from-transparent via-[var(--copper)] to-transparent opacity-40" />

        <p className="text-[11px] font-medium tracking-[0.3em] uppercase text-[var(--ink-muted)]">
          Kanban Studio
        </p>
        <h1 className="mt-4 font-display text-4xl text-[var(--ink)]">
          Sign in
        </h1>
        <p className="mt-3 text-sm text-[var(--ink-muted)] leading-relaxed">
          Use the MVP credentials to continue.
        </p>

        <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
          <label className="block text-xs font-medium tracking-[0.1em] uppercase text-[var(--ink-light)]">
            Username
            <input
              className="mt-2 w-full border-b border-[var(--rule-strong)] bg-transparent px-0 py-2 text-sm text-[var(--ink)] outline-none transition-colors focus:border-[var(--copper)] placeholder:text-[var(--ink-muted)]/40"
              name="username"
              autoComplete="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </label>

          <label className="block text-xs font-medium tracking-[0.1em] uppercase text-[var(--ink-light)]">
            Password
            <input
              className="mt-2 w-full border-b border-[var(--rule-strong)] bg-transparent px-0 py-2 text-sm text-[var(--ink)] outline-none transition-colors focus:border-[var(--copper)] placeholder:text-[var(--ink-muted)]/40"
              type="password"
              name="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>

          {error ? (
            <p className="text-sm font-medium text-[#B91C1C]">{error}</p>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="mt-2 w-full bg-[var(--ink)] px-4 py-3 text-[11px] font-medium tracking-[0.25em] uppercase text-[var(--cream)] transition-all hover:bg-[var(--ink-light)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
