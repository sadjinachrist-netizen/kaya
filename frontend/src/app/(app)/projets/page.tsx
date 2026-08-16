"use client";

import { useQuery } from "@tanstack/react-query";
import {
  CalendarDays,
  LoaderCircle,
  Plus,
  Search,
  UserRound,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { PageResultats, ProjetListe } from "@/lib/types";

const STATUT_STYLE: Record<string, string> = {
  brouillon: "bg-surface-low text-ink-muted",
  en_instruction: "bg-info-soft text-info",
  approuve: "bg-info-soft text-info",
  en_cours: "bg-success-soft text-success",
  suspendu: "bg-warning-soft text-warning",
  cloture: "bg-surface-low text-ink-muted",
  archive: "bg-surface-low text-ink-muted",
};

function avancementTemporel(debut: string, fin: string) {
  const d = new Date(debut).getTime();
  const f = new Date(fin).getTime();
  const maintenant = Date.now();
  if (maintenant <= d) return 0;
  if (maintenant >= f) return 100;
  return Math.round(((maintenant - d) / (f - d)) * 100);
}

const dateCourte = (iso: string) =>
  new Date(iso).toLocaleDateString("fr-FR", { month: "short", year: "numeric" });

export default function PageProjets() {
  const { peut } = useAuth();

  const [saisie, setSaisie] = useState("");
  const [recherche, setRecherche] = useState("");
  const [statut, setStatut] = useState<string | null>(null);

  // on n'interroge l'API qu'une fois la frappe stabilisee
  useEffect(() => {
    const minuteur = setTimeout(() => setRecherche(saisie), 300);
    return () => clearTimeout(minuteur);
  }, [saisie]);

  const liste = useQuery({
    queryKey: ["projets", recherche],
    queryFn: () =>
      api<PageResultats<ProjetListe>>("/projets/", {
        parametres: recherche ? { search: recherche } : undefined,
      }),
    placeholderData: (precedent) => precedent,
  });

  const projets = useMemo(() => liste.data?.results ?? [], [liste.data]);

  const statuts = useMemo(() => {
    const compte = new Map<string, { libelle: string; total: number }>();
    for (const p of projets) {
      const entree = compte.get(p.status) ?? { libelle: p.status_label, total: 0 };
      entree.total += 1;
      compte.set(p.status, entree);
    }
    return [...compte.entries()].sort((a, b) => b[1].total - a[1].total);
  }, [projets]);

  const affiches = statut ? projets.filter((p) => p.status === statut) : projets;

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-title">Projets</h1>
          <p className="mt-1 text-body text-ink-muted">
            {liste.data?.count ?? 0} projet{(liste.data?.count ?? 0) > 1 ? "s" : ""} dans
            votre périmètre.
          </p>
        </div>

        <div className="flex w-full items-center gap-2 sm:w-auto">
          <div className="relative flex-1 sm:w-72">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
            <input
              type="search"
              value={saisie}
              onChange={(e) => setSaisie(e.target.value)}
              placeholder="Code, intitulé, description…"
              aria-label="Rechercher un projet"
              className="w-full rounded-lg border border-border bg-surface py-2.5 pl-9 pr-3 text-body outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15"
            />
          </div>
          {peut("projet.creer") && (
            <Link
              href="/projets/nouveau"
              className="flex shrink-0 items-center gap-1.5 rounded-lg bg-primary px-4 py-2.5 text-body font-semibold text-on-primary transition hover:bg-primary-strong"
            >
              <Plus className="h-4 w-4" />
              Nouveau
            </Link>
          )}
        </div>
      </header>

      {statuts.length > 1 && (
        <div className="flex flex-wrap gap-2">
          <Filtre actif={statut === null} onClick={() => setStatut(null)}>
            Tous · {projets.length}
          </Filtre>
          {statuts.map(([code, { libelle, total }]) => (
            <Filtre key={code} actif={statut === code} onClick={() => setStatut(code)}>
              {libelle} · {total}
            </Filtre>
          ))}
        </div>
      )}

      {liste.isLoading ? (
        <div className="flex h-48 items-center justify-center">
          <LoaderCircle className="h-5 w-5 animate-spin text-ink-muted" />
        </div>
      ) : affiches.length === 0 ? (
        <p className="rounded-card bg-surface p-8 text-center text-body text-ink-muted shadow-sm">
          Aucun projet ne correspond à cette recherche.
        </p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {affiches.map((projet) => {
            const ecoule = avancementTemporel(projet.start_date, projet.end_date);
            return (
              <Link
                key={projet.id}
                href={`/projets/${projet.id}`}
                className="flex flex-col rounded-card bg-surface p-5 shadow-sm transition hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary/30"
              >
                <div className="flex items-start justify-between gap-3">
                  <span className="text-overline uppercase tracking-wide text-ink-muted">
                    {projet.code}
                  </span>
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-0.5 text-caption ${
                      STATUT_STYLE[projet.status] ?? "bg-surface-low text-ink-muted"
                    }`}
                  >
                    {projet.status_label}
                  </span>
                </div>

                <h2 className="mt-1.5 text-heading leading-snug text-ink">{projet.title}</h2>

                {projet.sectors.length > 0 && (
                  <div className="mt-2.5 flex flex-wrap gap-1.5">
                    {projet.sectors.map((secteur) => (
                      <span
                        key={secteur}
                        className="rounded bg-surface-low px-2 py-0.5 text-caption text-ink-muted"
                      >
                        {secteur}
                      </span>
                    ))}
                  </div>
                )}

                <dl className="mt-4 space-y-1.5 text-caption text-ink-muted">
                  <div className="flex items-center gap-1.5">
                    <UserRound className="h-3.5 w-3.5 shrink-0" />
                    {projet.manager_name}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <CalendarDays className="h-3.5 w-3.5 shrink-0" />
                    {dateCourte(projet.start_date)} → {dateCourte(projet.end_date)}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Users className="h-3.5 w-3.5 shrink-0" />
                    {projet.target_beneficiaries.toLocaleString("fr-FR")} bénéficiaires visés
                  </div>
                </dl>

                <div className="mt-auto pt-4">
                  <div className="flex items-baseline justify-between text-caption">
                    <span className="text-ink-muted">Calendrier écoulé</span>
                    <span className="font-semibold text-ink">{ecoule} %</span>
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-surface-low">
                    <div
                      className="h-full rounded-full bg-primary"
                      style={{ width: `${ecoule}%` }}
                    />
                  </div>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Filtre({
  actif,
  onClick,
  children,
}: {
  actif: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full px-3 py-1.5 text-caption transition ${
        actif
          ? "bg-primary text-on-primary"
          : "bg-surface text-ink-muted shadow-sm hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}