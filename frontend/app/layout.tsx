import type { Metadata } from "next";
import Link from "next/link";
import { Radio } from "lucide-react";
import "./globals.css";
import { HealthIndicator } from "@/components/HealthIndicator";

export const metadata: Metadata = {
  title: "EchoBrief",
  description: "Async voice brief → structured incident notes",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="border-b-4 border-black bg-primary">
          <div className="container flex h-16 items-center justify-between">
            <Link href="/" className="flex items-center gap-2.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-md border-2 border-black bg-black text-primary shadow-brutal-sm">
                <Radio className="h-5 w-5" />
              </span>
              <span className="text-xl font-black uppercase tracking-tight">
                EchoBrief
              </span>
            </Link>
            <HealthIndicator />
          </div>
        </header>
        <main className="container py-8">{children}</main>
      </body>
    </html>
  );
}
