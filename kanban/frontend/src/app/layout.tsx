import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kanban MVP",
  description: "Single-board Kanban application MVP",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
