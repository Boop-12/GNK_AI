import type { Metadata } from "next";
import { ThemeProvider } from "@/components/ThemeProvider";
import "./globals.css";
import "./themes.css";
import "./gnk.css";

export const metadata: Metadata = {
  title: "GNK Algo — Intelligence behind every trade",
  description: "Predict, analyze, execute, manage risk, and automate with GNK Algo.",
  metadataBase: new URL("https://www.gnkalgo.com"),
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" data-theme="carbon" data-accent="green">
      <body><ThemeProvider>{children}</ThemeProvider></body>
    </html>
  );
}
