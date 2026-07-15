import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "CAPA Review Console",
  description: "AI-assisted corrective action planning — human-in-the-loop review",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="top">
          <h1>
            <Link href="/">CAPA Review Console</Link>
          </h1>
          <span className="sub">
            AI proposes · QE approves (HITL #1) · verifies evidence (HITL #2)
          </span>
        </header>
        <main className="wrap">{children}</main>
      </body>
    </html>
  );
}
