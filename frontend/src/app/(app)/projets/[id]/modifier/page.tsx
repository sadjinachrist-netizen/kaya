"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import FormulaireProjet from "@/components/projets/FormulaireProjet";
import { api } from "@/lib/api";
import type { ProjetDetail } from "@/lib/types";

export default function PageModifierProjet() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ["projet", id],
    queryFn: () => api<ProjetDetail>(`/projets/${id}/`),
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoaderCircle className="h-6 w-6 animate-spin text-ink-muted" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <p className="rounded-card bg-surface p-8 text-center text-body text-ink-muted shadow-sm">
        Projet introuvable ou hors de votre périmètre.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <Link
        href={`/projets/${id}`}
        className="inline-flex items-center gap-1.5 text-caption text-ink-muted transition hover:text-ink"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Retour à la fiche
      </Link>
      <FormulaireProjet projet={data} />
    </div>
  );
}