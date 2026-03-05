"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { KanbanBoard } from "@/components/KanbanBoard";

type SessionResponse = {
  authenticated: boolean;
  username: string | null;
};

export default function BoardPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(true);
  const [username, setUsername] = useState<string | null>(null);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

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

        if (!data.authenticated) {
          router.replace("/");
          return;
        }

        setUsername(data.username);
      } catch {
        router.replace("/");
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

  const handleLogout = async () => {
    setIsLoggingOut(true);
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
      });
    } finally {
      router.replace("/");
      setIsLoggingOut(false);
    }
  };

  if (isLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[var(--bg)]">
        <p className="font-display text-base font-semibold text-[var(--text-muted)]">
          Loading...
        </p>
      </main>
    );
  }

  return (
    <div>
      <div className="relative z-10 flex w-full items-center justify-end gap-2.5 px-6 pt-4">
        <div className="flex items-center gap-2 rounded-full border border-[var(--border)] bg-[var(--bg-raised)] px-3 py-1.5 shadow-[var(--shadow-sm)]">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-[var(--col-lavender)] text-[10px] font-bold text-[var(--text)]">
            {(username ?? "U")[0].toUpperCase()}
          </div>
          <span className="text-[13px] font-medium text-[var(--text-secondary)]">
            {username ?? "user"}
          </span>
        </div>
        <button
          type="button"
          onClick={handleLogout}
          disabled={isLoggingOut}
          className="rounded-full border border-[var(--border-strong)] px-3.5 py-1.5 text-[13px] font-semibold text-[var(--text-secondary)] transition-all hover:bg-[var(--bg)] hover:text-[var(--text)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLoggingOut ? "Logging out..." : "Log out"}
        </button>
      </div>
      <KanbanBoard onAuthExpired={() => router.replace("/")} />
    </div>
  );
}
