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
        <header className="border-b bg-card">
          <div className="container flex h-16 items-center justify-between">
            <Link href="/" className="flex items-center gap-2 font-semibold">
              <span className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <Radio className="h-4 w-4" />
              </span>
              <span className="text-lg">EchoBrief</span>
            </Link>
            <HealthIndicator />
          </div>
        </header>
        <main className="container py-8">{children}</main>
      </body>
    </html>
  );
}
