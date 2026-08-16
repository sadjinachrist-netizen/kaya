"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, CalendarClock, LoaderCircle, Wallet } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";

import { api } from "@/lib/api";
import type { ConventionDetail } from "@/lib/types";

const argent = (montant: string, devise = "") =>
  `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(
    Number(montant),
  )} ${devise}`.trim();

const ALERTE_ECHEANCE: Record<string, string> = {
  depassee: "bg-danger-soft text-danger",
  j7: "bg-danger-soft text-danger",
  j15: "bg-warning-soft text-warning",
  j30: "bg-warning-soft text-warning",
};

export default function PageConvention() {
  const { id } = useParams<{ id: string }>();

  const { data, isLoading, error } = useQuery({
    queryKey: ["financement", id],
    queryFn: () => api<ConventionDetail>(`/financements/${id}/`),
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
      <div className="rounded-card bg-surface p-8 text-center shadow-sm">
        <p className="text-body text-ink">
          Cette convention est introuvable ou hors de votre périmètre.
        </p>
        <Link
          href="/financements"
          className="mt-3 inline-block text-body text-primary underline"
        >
          Retour à la liste
        </Link>
      </div>
    );
  }

  const devise = data.currency_code;

  return (
    <div className="space-y-5">
      <Link
        href="/financements"
        className="inline-flex items-center gap-1.5 text-caption text-ink-muted transition hover:text-ink"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Financements
      </Link>

      <header className="rounded-card bg-surface p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="font-mono text-overline uppercase tracking-wide text-ink-muted">
              {data.contract_number}
            </p>
            <h1 className="mt-0.5 text-title leading-tight">{data.title}</h1>
            <p className="mt-1 text-body text-ink-muted">{data.donor_name}</p>
          </div>
          <span className="rounded-full bg-surface-low px-3 py-1 text-caption text-ink-muted">
            {data.status_label}
          </span>
        </div>

        <dl className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Chiffre libelle="Montant engagé" valeur={argent(data.amount, devise)} />
          <Chiffre libelle="Budget structuré" valeur={argent(data.budget_total, devise)} />
          <Chiffre libelle="Dépensé" valeur={argent(data.montant_depense, devise)} />
          <Chiffre libelle="Disponible" valeur={argent(data.montant_disponible, devise)} />
        </dl>

        <div className="mt-5 space-y-2 border-t border-border pt-4">
          <Barre libelle="Consommation budgétaire" valeur={data.taux_consommation} teinte="bg-primary" />
          <Barre libelle="Temps écoulé" valeur={data.taux_temps_ecoule} teinte="bg-ink-muted/40" />
          <p className="text-caption text-ink-muted">
            Éligibilité des dépenses : {data.eligibility_start} → {data.eligibility_end}.
            Écart de rythme : {data.ecart_rythme > 0 ? "+" : ""}
            {data.ecart_rythme} points.
          </p>
        </div>
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        {/* ------------------------------ cofinancement ------------------------------ */}
        <section className="rounded-card bg-surface p-6 shadow-sm">
          <h2 className="text-heading">Projets financés</h2>
          <p className="mt-0.5 text-caption text-ink-muted">
            Quote-part cumulée : {data.quote_part_totale} % — le total ne peut excéder
            100 %.
          </p>
          {data.project_links.length === 0 ? (
            <p className="mt-3 text-body text-ink-muted">Aucun projet rattaché.</p>
          ) : (
            <ul className="mt-3 divide-y divide-border">
              {data.project_links.map((lien) => (
                <li key={lien.id} className="flex items-start justify-between gap-3 py-2.5">
                  <div>
                    <Link
                      href={`/projets/${lien.project}`}
                      className="text-body text-ink underline-offset-2 hover:underline"
                    >
                      {lien.project_title}
                    </Link>
                    <p className="font-mono text-caption text-ink-muted">
                      {lien.project_code}
                    </p>
                  </div>
                  <span className="shrink-0 text-body text-ink">{lien.share_percent} %</span>
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* -------------------------------- echeancier -------------------------------- */}
        <section className="rounded-card bg-surface p-6 shadow-sm">
          <h2 className="flex items-center gap-2 text-heading">
            <CalendarClock className="h-4 w-4 text-ink-muted" />
            Échéancier de rapportage
          </h2>
          {data.deadlines.length === 0 ? (
            <p className="mt-3 text-body text-ink-muted">Aucune échéance enregistrée.</p>
          ) : (
            <ul className="mt-3 divide-y divide-border">
              {data.deadlines.map((echeance) => (
                <li key={echeance.id} className="flex items-center justify-between gap-3 py-2.5">
                  <div>
                    <p className="text-body text-ink">{echeance.type_label}</p>
                    <p className="text-caption text-ink-muted">
                      Due le {echeance.due_date} · {echeance.status_label}
                    </p>
                  </div>
                  {echeance.alerte && (
                    <span
                      className={`shrink-0 whitespace-nowrap rounded-full px-2.5 py-0.5 text-caption ${
                        ALERTE_ECHEANCE[echeance.alerte] ?? "bg-surface-low text-ink-muted"
                      }`}
                    >
                      {echeance.jours_restants < 0
                        ? `${Math.abs(echeance.jours_restants)} j de retard`
                        : `J-${echeance.jours_restants}`}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* ------------------------------ lignes budgetaires ------------------------------ */}
        <section className="rounded-card bg-surface p-6 shadow-sm lg:col-span-2">
          <h2 className="flex items-center gap-2 text-heading">
            <Wallet className="h-4 w-4 text-ink-muted" />
            Lignes budgétaires
          </h2>
          {data.budget_lines.length === 0 ? (
            <p className="mt-3 text-body text-ink-muted">Budget non structuré.</p>
          ) : (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-body">
                <thead>
                  <tr className="border-b border-border text-left text-overline uppercase tracking-wide text-ink-muted">
                    <th className="px-2 py-2 font-semibold">Ligne</th>
                    <th className="px-2 py-2 font-semibold">Rubrique</th>
                    <th className="px-2 py-2 text-right font-semibold">Budgété</th>
                    <th className="px-2 py-2 text-right font-semibold">Dépensé</th>
                    <th className="px-2 py-2 text-right font-semibold">Disponible</th>
                    <th className="px-2 py-2 font-semibold">Consommation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {data.budget_lines.map((ligne) => (
                    <tr key={ligne.id} className={ligne.est_depassee ? "bg-danger-soft/40" : ""}>
                      <td className="px-2 py-2.5">
                        <p className="text-ink">{ligne.label}</p>
                        <p className="font-mono text-caption text-ink-muted">{ligne.code}</p>
                      </td>
                      <td className="whitespace-nowrap px-2 py-2.5 text-ink-muted">
                        {ligne.category_label}
                      </td>
                      <td className="whitespace-nowrap px-2 py-2.5 text-right text-ink">
                        {argent(ligne.budgeted_amount)}
                      </td>
                      <td className="whitespace-nowrap px-2 py-2.5 text-right text-ink">
                        {argent(ligne.montant_depense)}
                      </td>
                      <td
                        className={`whitespace-nowrap px-2 py-2.5 text-right ${
                          ligne.est_depassee ? "font-semibold text-danger" : "text-ink-muted"
                        }`}
                      >
                        {argent(ligne.montant_disponible)}
                      </td>
                      <td className="px-2 py-2.5">
                        <div className="flex items-center gap-2">
                          <div className="h-1.5 w-24 overflow-hidden rounded-full bg-surface-low">
                            <div
                              className={`h-full rounded-full ${
                                ligne.est_depassee ? "bg-danger" : "bg-primary"
                              }`}
                              style={{ width: `${Math.min(ligne.taux_consommation, 100)}%` }}
                            />
                          </div>
                          <span className="whitespace-nowrap text-caption text-ink-muted">
                            {ligne.taux_consommation} %
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* -------------------------------- versements -------------------------------- */}
        {data.installments.length > 0 && (
          <section className="rounded-card bg-surface p-6 shadow-sm lg:col-span-2">
            <h2 className="text-heading">Tranches de versement</h2>
            <ul className="mt-3 divide-y divide-border">
              {data.installments.map((tranche) => (
                <li key={tranche.id} className="flex items-center justify-between gap-3 py-2.5">
                  <div>
                    <p className="text-body text-ink">{argent(tranche.amount, devise)}</p>
                    <p className="text-caption text-ink-muted">
                      Attendu le {tranche.expected_date}
                      {tranche.received_date && ` · reçu le ${tranche.received_date}`}
                    </p>
                  </div>
                  <span
                    className={`shrink-0 rounded-full px-2.5 py-0.5 text-caption ${
                      tranche.received_date
                        ? "bg-success-soft text-success"
                        : "bg-surface-low text-ink-muted"
                    }`}
                  >
                    {tranche.status_label}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}

function Chiffre({ libelle, valeur }: { libelle: string; valeur: string }) {
  return (
    <div>
      <dt className="text-caption uppercase tracking-wide text-ink-muted">{libelle}</dt>
      <dd className="mt-0.5 text-heading text-ink">{valeur}</dd>
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
      <div className="flex items-baseline justify-between text-body">
        <span className="text-ink-muted">{libelle}</span>
        <span className="font-semibold text-ink">{valeur} %</span>
      </div>
      <div className="mt-1 h-2 overflow-hidden rounded-full bg-surface-low">
        <div
          className={`h-full rounded-full ${teinte}`}
          style={{ width: `${Math.min(valeur, 100)}%` }}
        />
      </div>
    </div>
  );
}