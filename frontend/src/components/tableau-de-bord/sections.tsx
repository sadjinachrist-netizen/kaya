"use client";
import {
  AlertTriangle,
  CalendarClock,
  ChevronRight,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

import Link from "next/link";

import type {
  ActiviteAValider,
  EcheanceResume,
  IndicateurResume,
  LigneBudget,
  Sadd,
  StatutIndicateur,
} from "@/lib/types";

/* ------------------------------------------------------------------ carte */
export function Carte({
  titre,
  action,
  children,
  className = "",
}: {
  titre: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section className={`rounded-card bg-surface p-5 shadow-sm ${className}`}>
      <header className="mb-4 flex items-start justify-between gap-3">
        <h2 className="text-heading text-ink">{titre}</h2>
        {action}
      </header>
      {children}
    </section>
  );
}

const COULEUR_STATUT: Record<StatutIndicateur, string> = {
  atteint: "bg-success",
  en_cours: "bg-warning",
  en_retard: "bg-danger",
};

const LIBELLE_STATUT: Record<StatutIndicateur, string> = {
  atteint: "Atteints",
  en_cours: "En cours",
  en_retard: "En retard",
};

/* ----------------------------------------------------------- indicateurs */
export function SectionIndicateurs({
  repartition,
  detail,
}: {
  repartition: Record<StatutIndicateur, number>;
  detail: IndicateurResume[];
}) {
  return (
    <Carte
      titre="Indicateurs du cadre logique"
      action={
        <div className="flex gap-3 text-caption">
          {(Object.keys(LIBELLE_STATUT) as StatutIndicateur[]).map((statut) => (
            <span key={statut} className="flex items-center gap-1.5 text-ink-muted">
              <span className={`h-2 w-2 rounded-full ${COULEUR_STATUT[statut]}`} />
              {repartition[statut] ?? 0}
            </span>
          ))}
        </div>
      }
    >
      {detail.length === 0 ? (
        <p className="text-body text-ink-muted">Aucun indicateur défini.</p>
      ) : (
        <ul className="space-y-4">
          {detail.map((indicateur) => (
            <li key={indicateur.id}>
              <div className="flex items-baseline justify-between gap-4">
                <p className="text-body text-ink" title={indicateur.titre}>
                  {indicateur.titre.length > 58
                    ? `${indicateur.titre.slice(0, 58)}…`
                    : indicateur.titre}
                </p>
                <p className="shrink-0 text-caption text-ink-muted">
                  {Number(indicateur.atteint).toLocaleString("fr-FR")} /{" "}
                  {Number(indicateur.cible).toLocaleString("fr-FR")}
                </p>
              </div>
              <div className="relative mt-1.5 h-2 rounded-full bg-surface-low">
                {/* repere : ce qui devrait etre atteint a cette date */}
                <span
                  className="absolute top-1/2 h-3.5 w-px -translate-y-1/2 bg-ink-muted/50"
                  style={{ left: `${Math.min(indicateur.attendu, 100)}%` }}
                  title={`Attendu à ce stade : ${indicateur.attendu} %`}
                />
                <span
                  className={`block h-2 rounded-full ${COULEUR_STATUT[indicateur.statut]}`}
                  style={{ width: `${Math.min(indicateur.taux, 100)}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-4 text-caption text-ink-muted">
        Le trait vertical indique la part de la cible normalement atteinte à cette date.
      </p>
    </Carte>
  );
}

/* --------------------------------------------------------------- budget */
export function SectionBudget({ lignes }: { lignes: LigneBudget[] }) {
  return (
    <Carte titre="Consommation budgétaire vs temps écoulé">
      {lignes.length === 0 ? (
        <p className="text-body text-ink-muted">Aucun financement rattaché.</p>
      ) : (
        <ul className="space-y-5">
          {lignes.map((ligne) => {
            const enAlerte = ligne.alerte !== null;
            const sous = ligne.alerte === "sous_consommation";
            return (
              <li key={ligne.convention}>
                <div className="flex items-baseline justify-between gap-3">
                  <p className="text-body font-medium text-ink">{ligne.convention}</p>
                  {enAlerte && (
                    <span
                      className={`flex items-center gap-1 rounded-full px-2 py-0.5 text-caption ${
                        sous ? "bg-warning-soft text-warning" : "bg-danger-soft text-danger"
                      }`}
                    >
                      {sous ? (
                        <TrendingDown className="h-3 w-3" />
                      ) : (
                        <TrendingUp className="h-3 w-3" />
                      )}
                      {ligne.ecart > 0 ? "+" : ""}
                      {ligne.ecart} pts
                    </span>
                  )}
                </div>
                <p className="text-caption text-ink-muted">
                  {ligne.bailleur} — {Number(ligne.montant).toLocaleString("fr-FR")}{" "}
                  {ligne.devise}
                </p>

                <div className="mt-2 space-y-1.5">
                  <Barre libelle="Consommé" valeur={ligne.consomme} couleur="bg-primary" />
                  <Barre
                    libelle="Temps écoulé"
                    valeur={ligne.temps_ecoule}
                    couleur="bg-ink-muted/40"
                  />
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Carte>
  );
}

function Barre({
  libelle,
  valeur,
  couleur,
}: {
  libelle: string;
  valeur: number;
  couleur: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-24 shrink-0 text-caption text-ink-muted">{libelle}</span>
      <div className="h-2 flex-1 rounded-full bg-surface-low">
        <span
          className={`block h-2 rounded-full ${couleur}`}
          style={{ width: `${Math.min(valeur, 100)}%` }}
        />
      </div>
      <span className="w-12 shrink-0 text-right text-caption tabular-nums text-ink">
        {valeur} %
      </span>
    </div>
  );
}

/* -------------------------------------------------------- pyramide SADD */
const TRANCHES: Array<[string, string]> = [
  ["60_plus", "60 ans et +"],
  ["18_59", "18 – 59 ans"],
  ["6_17", "6 – 17 ans"],
  ["0_5", "0 – 5 ans"],
];

export function SectionPyramide({ sadd }: { sadd: Sadd }) {
  const maximum = Math.max(
    1,
    ...TRANCHES.flatMap(([cle]) => [sadd[cle]?.hommes ?? 0, sadd[cle]?.femmes ?? 0]),
  );
  const total = TRANCHES.reduce((somme, [cle]) => somme + (sadd[cle]?.total ?? 0), 0);

  return (
    <Carte
      titre="Répartition par sexe et par âge"
      action={
        <span className="text-caption text-ink-muted">
          {total.toLocaleString("fr-FR")} personnes
        </span>
      }
    >
      <div className="mb-2 flex text-caption text-ink-muted">
        <span className="flex-1 text-right pr-2">Hommes</span>
        <span className="w-24 text-center">Tranche</span>
        <span className="flex-1 pl-2">Femmes</span>
      </div>
      <ul className="space-y-2">
        {TRANCHES.map(([cle, libelle]) => {
          const tranche = sadd[cle] ?? { hommes: 0, femmes: 0, total: 0 };
          return (
            <li key={cle} className="flex items-center">
              <div className="flex flex-1 items-center justify-end gap-2">
                <span className="text-caption tabular-nums text-ink-muted">
                  {tranche.hommes}
                </span>
                <div
                  className="h-4 rounded-l bg-info"
                  style={{ width: `${(tranche.hommes / maximum) * 100}%` }}
                />
              </div>
              <span className="w-24 text-center text-caption text-ink">{libelle}</span>
              <div className="flex flex-1 items-center gap-2">
                <div
                  className="h-4 rounded-r bg-primary-strong"
                  style={{ width: `${(tranche.femmes / maximum) * 100}%` }}
                />
                <span className="text-caption tabular-nums text-ink-muted">
                  {tranche.femmes}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
    </Carte>
  );
}

/* ------------------------------------------------------------ echeances */
export function SectionEcheances({ echeances }: { echeances: EcheanceResume[] }) {
  return (
    <Carte titre="Échéances bailleur">
      {echeances.length === 0 ? (
        <p className="text-body text-ink-muted">Aucune échéance dans les 30 jours.</p>
      ) : (
        <ul className="divide-y divide-border">
          {echeances.map((echeance) => (
            <li key={echeance.id} className="flex items-center gap-3 py-3 first:pt-0">
              <CalendarClock className="h-4 w-4 shrink-0 text-ink-muted" />
              <div className="min-w-0 flex-1">
                <p className="truncate text-body text-ink">{echeance.type}</p>
                <p className="text-caption text-ink-muted">
                  {echeance.convention} — {echeance.echeance}
                </p>
              </div>
              <span
                className={`shrink-0 rounded-full px-2.5 py-0.5 text-caption ${
                  echeance.jours_restants <= 7
                    ? "bg-danger-soft text-danger"
                    : echeance.jours_restants <= 15
                      ? "bg-warning-soft text-warning"
                      : "bg-surface-low text-ink-muted"
                }`}
              >
                J-{echeance.jours_restants}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Carte>
  );
}

/* ------------------------------------------------------ file de validation */
export function SectionFileValidation({
  activites,
}: {
  activites: ActiviteAValider[];
}) {
  return (
    <Carte
      titre="File de validation"
      action={
        <span className="text-caption text-ink-muted">
          {activites.length} en attente
        </span>
      }
      className="lg:col-span-2"
    >
      {activites.length === 0 ? (
        <p className="text-body text-ink-muted">Aucune activité en attente. 👌</p>
      ) : (
        <div className="scrollbar-fine overflow-x-auto">
          <table className="w-full text-body">
            <thead>
              <tr className="border-b border-border text-left text-overline uppercase tracking-wide text-ink-muted">
                <th className="pb-2 pr-3 font-semibold">Date</th>
                <th className="pb-2 pr-3 font-semibold">Agent</th>
                <th className="pb-2 pr-3 font-semibold">Activité</th>
                <th className="pb-2 pr-3 font-semibold">Localité</th>
                <th className="pb-2 font-semibold">Qualité</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {activites.map((activite) => (
                <tr key={activite.id}>
                  <td className="py-2.5 pr-3 whitespace-nowrap text-ink-muted">
                    {activite.date}
                  </td>
                  <td className="py-2.5 pr-3 whitespace-nowrap">{activite.agent}</td>
                  <td className="py-2.5 pr-3">
                    <p className="text-ink">{activite.type}</p>
                    <p className="text-caption text-ink-muted">{activite.projet}</p>
                  </td>
                  <td className="py-2.5 pr-3 whitespace-nowrap text-ink-muted">
                    {activite.zone}
                  </td>
                  <td className="py-2.5">
                    {activite.alertes.length === 0 ? (
                      <span className="rounded-full bg-success-soft px-2.5 py-0.5 text-caption text-success">
                        Standard
                      </span>
                    ) : (
                      <span
                        className="flex items-center gap-1 rounded-full bg-warning-soft px-2.5 py-0.5 text-caption text-warning"
                        title={activite.alertes.join(" · ")}
                      >
                        <AlertTriangle className="h-3 w-3" />
                        {activite.alertes[0]}
                        {activite.alertes.length > 1 && ` +${activite.alertes.length - 1}`}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Carte>
  );

}


/* ------------------------------------------------ tableau de l'agent terrain */

export function SectionCollecte({
  collecte,
}: {
  collecte: { menages: number; activites: number };
}) {
  return (
    <section className="rounded-card bg-surface p-6 shadow-sm">
      <h2 className="text-heading">Ma collecte du mois</h2>
      <p className="mt-0.5 text-caption text-ink-muted">
        Depuis le premier jour du mois en cours.
      </p>
      <div className="mt-4 grid grid-cols-2 gap-4">
        <div className="rounded-lg bg-surface-low p-4">
          <p className="text-display text-ink">{collecte.menages}</p>
          <p className="text-caption text-ink-muted">ménages enregistrés</p>
        </div>
        <div className="rounded-lg bg-surface-low p-4">
          <p className="text-display text-ink">{collecte.activites}</p>
          <p className="text-caption text-ink-muted">activités saisies</p>
        </div>
      </div>
    </section>
  );
}

export function SectionACorriger({
  activites,
}: {
  activites: { id: number; code: string; projet: string; date: string; motif: string }[];
}) {
  return (
    <section className="rounded-card bg-surface p-6 shadow-sm">
      <h2 className="text-heading">Saisies à corriger</h2>
      {activites.length === 0 ? (
        <p className="mt-3 text-body text-ink-muted">
          Rien à reprendre — toutes vos saisies ont été acceptées.
        </p>
      ) : (
        <ul className="mt-3 divide-y divide-border">
          {activites.map((activite) => (
            <li key={activite.id} className="py-3">
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-mono text-caption text-ink-muted">
                  {activite.code} · {activite.projet}
                </span>
                <span className="shrink-0 text-caption text-ink-muted">
                  {activite.date}
                </span>
              </div>
              <p className="mt-0.5 text-body text-danger">{activite.motif}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}


export function SectionMesProjets({
  projets,
}: {
  projets: { id: number; code: string; title: string; status: string }[];
}) {
  return (
    <section className="rounded-card bg-surface p-6 shadow-sm">
      <h2 className="text-heading">Mes projets</h2>
      <p className="mt-0.5 text-caption text-ink-muted">
        Les projets sur lesquels vous êtes affecté. Cliquez pour ouvrir la fiche.
      </p>

      {projets.length === 0 ? (
        <p className="mt-4 text-body text-ink-muted">
          Vous n&apos;êtes affecté à aucun projet.
        </p>
      ) : (
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {projets.map((projet) => (
            <Link
              key={projet.id}
              href={`/projets/${projet.id}`}
              className="group flex items-center justify-between gap-3 rounded-lg border border-border p-4 transition hover:border-primary/40 hover:bg-primary-soft/40 focus:outline-none focus:ring-2 focus:ring-primary/30"
            >
              <div className="min-w-0">
                <p className="truncate text-body text-ink">{projet.title}</p>
                <p className="font-mono text-caption text-ink-muted">{projet.code}</p>
              </div>
              <ChevronRight className="h-4 w-4 shrink-0 text-ink-muted transition group-hover:text-primary" />
            </Link>
          ))}
        </div>
      )}
    </section>
  );
}