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
      <main className="flex min-h-screen items-center justify-center bg-[var(--surface)]">
        <p className="text-sm font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Checking session...
        </p>
      </main>
    );
  }

  return (
    <div>
      <div className="relative z-10 mx-auto flex w-full max-w-[1500px] items-center justify-end gap-3 px-6 pt-6">
        <p className="rounded-full border border-[var(--stroke)] bg-white px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--gray-text)]">
          Signed in as {username ?? "user"}
        </p>
        <button
          type="button"
          onClick={handleLogout}
          disabled={isLoggingOut}
          className="rounded-full bg-[var(--secondary-purple)] px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-white transition enabled:hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-70"
        >
          {isLoggingOut ? "Logging out..." : "Log out"}
        </button>
      </div>
      <KanbanBoard onAuthExpired={() => router.replace("/")} />
    </div>
  );
}
