import type { Metadata } from "next";
import { Inter } from "next/font/google";

import "./globals.css";

import { Providers } from "./providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Kaya — Gestion de projets humanitaires",
  description:
    "Plateforme de gestion et de suivi de projets humanitaires : " +
    "bénéficiaires, activités terrain, financements et indicateurs.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fr" className={inter.variable}>
      <body><Providers>{children}</Providers></body>
    </html>
  );
}