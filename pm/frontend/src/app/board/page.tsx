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
      <main className="flex min-h-screen items-center justify-center bg-[var(--cream)]">
        <p className="font-display text-lg italic text-[var(--ink-muted)]">
          Loading...
        </p>
      </main>
    );
  }

  return (
    <div>
      <div className="relative z-10 flex w-full items-center justify-end gap-3 px-6 pt-4">
        <p className="border-b border-[var(--rule)] px-1 py-1 text-[11px] font-medium tracking-[0.15em] uppercase text-[var(--ink-muted)]">
          {username ?? "user"}
        </p>
        <button
          type="button"
          onClick={handleLogout}
          disabled={isLoggingOut}
          className="bg-[var(--ink)] px-3 py-1.5 text-[10px] font-medium tracking-[0.2em] uppercase text-[var(--cream)] transition-colors hover:bg-[var(--ink-light)] disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLoggingOut ? "Logging out..." : "Log out"}
        </button>
      </div>
      <KanbanBoard onAuthExpired={() => router.replace("/")} />
    </div>
  );
}
