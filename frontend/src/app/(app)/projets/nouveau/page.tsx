"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import FormulaireProjet from "@/components/projets/FormulaireProjet";

export default function PageNouveauProjet() {
  return (
    <div className="space-y-4">
      <Link
        href="/projets"
        className="inline-flex items-center gap-1.5 text-caption text-ink-muted transition hover:text-ink"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Projets
      </Link>
      <FormulaireProjet />
    </div>
  );
}