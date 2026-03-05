"use client";

import dynamic from "next/dynamic";

const Board = dynamic(() => import("@/components/Board").then((m) => ({ default: m.Board })), {
  ssr: false,
});

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-[var(--background)] to-[var(--blue-primary)]/5 p-6">
      <h1 className="mb-6 text-3xl font-bold tracking-tight text-[var(--dark-navy)]">
        Kanban Board
      </h1>
      <Board />
    </main>
  );
}
