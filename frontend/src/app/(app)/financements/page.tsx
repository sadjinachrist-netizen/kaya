"use client";

import { useQuery } from "@tanstack/react-query";
import { LoaderCircle, Search, TrendingDown, TrendingUp } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import type { ConventionListe, PageResultats } from "@/lib/types";

const argent = (montant: string, devise: string) =>
  `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(
    Number(montant),
  )} ${devise}`;

export default function PageFinancements() {
  const [saisie, setSaisie] = useState("");
  const [recherche, setRecherche] = useState("");

  useEffect(() => {
    const minuteur = setTimeout(() => setRecherche(saisie), 300);
    return () => clearTimeout(minuteur);
  }, [saisie]);

  const liste = useQuery({
    queryKey: ["financements", recherche],
    queryFn: () =>
      api<PageResultats<ConventionListe>>("/financements/", {
        parametres: recherche ? { search: recherche } : undefined,
      }),
    placeholderData: (precedent) => precedent,
  });

  const conventions = liste.data?.results ?? [];
  const total = conventions.reduce((somme, c) => somme + Number(c.amount), 0);

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-title">Financements</h1>
          <p className="mt-1 text-body text-ink-muted">
            {liste.data?.count ?? 0} convention{(liste.data?.count ?? 0) > 1 ? "s" : ""} —{" "}
            {new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(total)}{" "}
            engagés, toutes devises confondues.
          </p>
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
          <input
            type="search"
            value={saisie}
            onChange={(e) => setSaisie(e.target.value)}
            placeholder="Numéro de contrat, bailleur…"
            aria-label="Rechercher une convention"
            className="w-full rounded-lg border border-border bg-surface py-2.5 pl-9 pr-3 text-body outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15"
          />
        </div>
      </header>

      {liste.isLoading ? (
        <div className="flex h-48 items-center justify-center">
          <LoaderCircle className="h-5 w-5 animate-spin text-ink-muted" />
        </div>
      ) : conventions.length === 0 ? (
        <p className="rounded-card bg-surface p-8 text-center text-body text-ink-muted shadow-sm">
          Aucune convention accessible.
        </p>
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {conventions.map((convention) => (
            <Link
              key={convention.id}
              href={`/financements/${convention.id}`}
              className="rounded-card bg-surface p-5 shadow-sm transition hover:shadow-md focus:outline-none focus:ring-2 focus:ring-primary/30"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-mono text-overline uppercase tracking-wide text-ink-muted">
                    {convention.contract_number}
                  </p>
                  <p className="mt-0.5 text-heading leading-snug text-ink">
                    {convention.donor_name}
                  </p>
                </div>
                <span className="shrink-0 rounded-full bg-surface-low px-2.5 py-0.5 text-caption text-ink-muted">
                  {convention.status_label}
                </span>
              </div>

              <p className="mt-2 text-body text-ink">
                {argent(convention.amount, convention.currency_code)}
              </p>
              <p className="text-caption text-ink-muted">
                Éligibilité : {convention.eligibility_start} → {convention.eligibility_end}
              </p>

              <div className="mt-4 space-y-2">
                <Barre
                  libelle="Consommé"
                  valeur={convention.taux_consommation}
                  teinte="bg-primary"
                />
                <Barre
                  libelle="Temps écoulé"
                  valeur={convention.taux_temps_ecoule}
                  teinte="bg-ink-muted/40"
                />
              </div>

              {convention.alerte_rythme && (
                <p
                  className={`mt-3 inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-caption ${
                    convention.ecart_rythme > 0
                      ? "bg-danger-soft text-danger"
                      : "bg-warning-soft text-warning"
                  }`}
                >
                  {convention.ecart_rythme > 0 ? (
                    <TrendingUp className="h-3 w-3" />
                  ) : (
                    <TrendingDown className="h-3 w-3" />
                  )}
                  {convention.ecart_rythme > 0 ? "+" : ""}
                  {convention.ecart_rythme} pts d&apos;écart
                </p>
              )}
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function Barre({
  libelle,
  valeur,
  teinte,
}: {
  libelle: string;
  valeur: number;
  teinte: string;
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between text-caption">
        <span className="text-ink-muted">{libelle}</span>
        <span className="text-ink">{valeur} %</span>
      </div>
      <div className="mt-0.5 h-1.5 overflow-hidden rounded-full bg-surface-low">
        <div
          className={`h-full rounded-full ${teinte}`}
          style={{ width: `${Math.min(valeur, 100)}%` }}
        />
      </div>
    </div>
  );
}