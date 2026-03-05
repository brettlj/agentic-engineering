import type { Metadata } from "next";
import { Nunito, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const displayFont = Nunito({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["600", "700", "800"],
});

const bodyFont = Plus_Jakarta_Sans({
  variable: "--font-body",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Kanban Studio",
  description: "A focused, single-board kanban workspace.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${displayFont.variable} ${bodyFont.variable}`}>
        {children}
      </body>
    </html>
  );
}
