import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Aunix",
  description: "Digital worker management",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="min-h-screen bg-slate-50 text-slate-900 antialiased">
        <nav className="border-b bg-white">
          <div className="mx-auto flex max-w-4xl items-center gap-6 px-4 py-3">
            <a href="/" className="font-semibold">Aunix</a>
            <a href="/" className="text-sm text-slate-600 hover:text-slate-900">Agents</a>
            <a href="/create" className="text-sm text-slate-600 hover:text-slate-900">New agent</a>
            <a href="/feed" className="text-sm text-slate-600 hover:text-slate-900">Activity feed</a>
          </div>
        </nav>
        <main className="mx-auto max-w-4xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
