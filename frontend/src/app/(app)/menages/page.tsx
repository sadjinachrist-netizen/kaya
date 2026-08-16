"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ChevronLeft,
  ChevronRight,
  LoaderCircle,
  Plus,
  Search,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { MenageListe, PageResultats } from "@/lib/types";

const RESIDENCE: Record<string, string> = {
  resident: "Résident",
  deplace: "Déplacé interne",
  refugie: "Réfugié",
  retourne: "Retourné",
};

const VALIDATION: Record<string, { libelle: string; style: string }> = {
  a_valider: { libelle: "À valider", style: "bg-warning-soft text-warning" },
  valide: { libelle: "Validé", style: "bg-success-soft text-success" },
  doublon: { libelle: "Doublon confirmé", style: "bg-danger-soft text-danger" },
};

const FILTRES = [
  { code: null, libelle: "Tous" },
  { code: "a_valider", libelle: "À valider" },
  { code: "valide", libelle: "Validés" },
  { code: "doublon", libelle: "Doublons" },
];

export default function PageMenages() {
  const { peut } = useAuth();
  const nominatif = peut("beneficiaire.voir_donnees_nominatives");

  const [saisie, setSaisie] = useState("");
  const [recherche, setRecherche] = useState("");
  const [statut, setStatut] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  useEffect(() => {
    const minuteur = setTimeout(() => setRecherche(saisie), 300);
    return () => clearTimeout(minuteur);
  }, [saisie]);

  useEffect(() => setPage(1), [recherche, statut]);

  const liste = useQuery({
    queryKey: ["menages", recherche, statut, page],
    queryFn: () =>
      api<PageResultats<MenageListe>>("/menages/", {
        parametres: {
          ...(recherche ? { search: recherche } : {}),
          ...(statut ? { statut } : {}),
          page: String(page),
        },
      }),
    placeholderData: (precedent) => precedent,
  });

  const menages = liste.data?.results ?? [];

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-title">Ménages bénéficiaires</h1>
          <p className="mt-1 text-body text-ink-muted">
            {(liste.data?.count ?? 0).toLocaleString("fr-FR")} ménage
            {(liste.data?.count ?? 0) > 1 ? "s" : ""} dans votre périmètre.
          </p>
        </div>

        <div className="flex w-full items-center gap-2 sm:w-auto">
          <div className="relative flex-1 sm:w-72">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
            <input
              type="search"
              value={saisie}
              onChange={(e) => setSaisie(e.target.value)}
              placeholder={nominatif ? "Nom, code, localité…" : "Code, localité…"}
              aria-label="Rechercher un ménage"
              className="w-full rounded-lg border border-border bg-surface py-2.5 pl-9 pr-3 text-body outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15"
            />
          </div>
          {peut("beneficiaire.creer") && (
            <Link
              href="/menages/nouveau"
              className="flex shrink-0 items-center gap-1.5 rounded-lg bg-primary px-4 py-2.5 text-body font-semibold text-on-primary transition hover:bg-primary-strong"
            >
              <Plus className="h-4 w-4" />
              Nouveau
            </Link>
          )}
        </div>
      </header>

      {!nominatif && (
        <div className="flex items-start gap-2.5 rounded-card border border-info/20 bg-info-soft px-4 py-3">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-info" />
          <p className="text-body text-info">
            Les identités sont masquées pour votre rôle. Chaque ménage est désigné par
            son code d&apos;enregistrement — la substitution est faite par le serveur,
            les noms ne quittent jamais la base.
          </p>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {FILTRES.map((filtre) => (
          <button
            key={filtre.libelle}
            onClick={() => setStatut(filtre.code)}
            className={`rounded-full px-3 py-1.5 text-caption transition ${
              statut === filtre.code
                ? "bg-primary text-on-primary"
                : "bg-surface text-ink-muted shadow-sm hover:text-ink"
            }`}
          >
            {filtre.libelle}
          </button>
        ))}
      </div>

      <section className="rounded-card bg-surface shadow-sm">
        {liste.isLoading ? (
          <div className="flex h-48 items-center justify-center">
            <LoaderCircle className="h-5 w-5 animate-spin text-ink-muted" />
          </div>
        ) : menages.length === 0 ? (
          <p className="p-8 text-center text-body text-ink-muted">
            Aucun ménage ne correspond à ces critères.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-body">
              <thead>
                <tr className="border-b border-border text-left text-overline uppercase tracking-wide text-ink-muted">
                  <th className="px-4 py-3 font-semibold">
                    {nominatif ? "Chef de ménage" : "Identifiant"}
                  </th>
                  <th className="px-4 py-3 font-semibold">Taille</th>
                  <th className="px-4 py-3 font-semibold">Localité</th>
                  <th className="px-4 py-3 font-semibold">Statut de résidence</th>
                  <th className="px-4 py-3 font-semibold">Validation</th>
                  <th className="px-4 py-3 font-semibold">Enregistré le</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {menages.map((menage) => {
                  const validation = VALIDATION[menage.validation_status];
                  return (
                    <tr key={menage.id} className="transition hover:bg-surface-low">
                      <td className="px-4 py-3">
                        <p className={nominatif ? "text-ink" : "font-mono text-ink"}>
                          {menage.head_name}
                        </p>
                        {nominatif && (
                          <p className="font-mono text-caption text-ink-muted">
                            {menage.code}
                          </p>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-ink-muted">
                        {menage.nb_membres} pers.
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">{menage.zone_name}</td>
                      <td className="whitespace-nowrap px-4 py-3 text-ink-muted">
                        {RESIDENCE[menage.residence_status] ?? menage.residence_status}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`whitespace-nowrap rounded-full px-2.5 py-0.5 text-caption ${
                            validation?.style ?? "bg-surface-low text-ink-muted"
                          }`}
                        >
                          {validation?.libelle ?? menage.validation_status}
                        </span>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-ink-muted">
                        {new Date(menage.registered_at).toLocaleDateString("fr-FR")}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {(liste.data?.next || liste.data?.previous) && (
          <div className="flex items-center justify-between gap-3 border-t border-border px-4 py-3">
            <button
              disabled={!liste.data?.previous}
              onClick={() => setPage((p) => p - 1)}
              className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-caption text-ink-muted transition hover:bg-surface-low disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ChevronLeft className="h-3.5 w-3.5" />
              Précédent
            </button>
            <span className="text-caption text-ink-muted">Page {page}</span>
            <button
              disabled={!liste.data?.next}
              onClick={() => setPage((p) => p + 1)}
              className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-caption text-ink-muted transition hover:bg-surface-low disabled:cursor-not-allowed disabled:opacity-40"
            >
              Suivant
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          </div>
        )}
      </section>
    </div>
  );
}