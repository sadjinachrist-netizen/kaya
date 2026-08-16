"use client";

import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, LoaderCircle } from "lucide-react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { TableauDeBord } from "@/lib/types";

import Link from "next/link";
import { Plus } from "lucide-react";

import {
  SectionACorriger,
  SectionBudget,
  SectionCollecte,
  SectionEcheances,
  SectionFileValidation,
  SectionIndicateurs,
  SectionMesProjets,
  SectionPyramide,
} from "@/components/tableau-de-bord/sections";
import type { TableauAgent, TableauProjet, TableauSuperviseur } from "@/lib/types";


/** Libelles lisibles pour les cles renvoyees par l'API. */
const LIBELLES: Record<string, string> = {
  a_corriger: "À corriger",
  brouillons: "Brouillons",
  en_attente_validation: "En attente de validation",
  validees: "Validées",
  activites_a_valider: "Activités à valider",
  alertes_qualite: "Alertes qualité",
  doublons_a_arbitrer: "Doublons à arbitrer",
  menages_a_valider: "Ménages à valider",
  projets: "Projets",
  beneficiaires: "Ménages bénéficiaires",
  individus: "Personnes",
  indicateurs: "Indicateurs",
  menages: "Ménages",
  activites_validees: "Activités validées",
  conventions: "Conventions",
  depenses_a_valider: "Dépenses à valider",
  alertes_rythme: "Alertes de rythme",
  echeances_30j: "Échéances sous 30 jours",
  projets_en_cours: "Projets en cours",
  personnes_atteintes: "Personnes atteintes",
  projets_finances: "Projets financés",
};

const ROLES_LISIBLES: Record<string, string> = {
  agent_terrain: "Agent terrain",
  superviseur: "Superviseur terrain",
  chef_projet: "Chef de projet",
  coordinateur: "Coordinateur de programme",
  suivi_evaluation: "Suivi-évaluation",
  charge_financier: "Chargé financier",
  direction: "Direction",
  bailleur: "Bailleur",
  auditeur: "Auditeur",
};

export default function PageTableauDeBord() {
  const { utilisateur } = useAuth();

  const { data, isLoading, error } = useQuery({
    queryKey: ["tableau-de-bord"],
    queryFn: () => api<TableauDeBord>("/tableau-de-bord/"),
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <LoaderCircle className="h-6 w-6 animate-spin text-ink-muted" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-start gap-3 rounded-card border border-danger/25 bg-danger-soft p-4 text-danger">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
        <div>
          <p className="font-semibold">Impossible de charger le tableau de bord</p>
          <p className="text-body">{(error as Error).message}</p>
        </div>
      </div>
    );
  }

  const tuiles = Object.entries(data?.tuiles ?? {});

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-title">
          Bonjour {utilisateur?.first_name || utilisateur?.username}
        </h1>
        <p className="mt-1 text-body text-ink-muted">
          {ROLES_LISIBLES[data?.role ?? ""] ?? "Vue d'ensemble"} — Solidarité
          Développement Togo
        </p>
      </header>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {tuiles.map(([cle, valeur]) => (
          <article
            key={cle}
            className="rounded-card bg-surface p-5 shadow-sm transition hover:-translate-y-0.5"
          >
            <p className="text-overline uppercase tracking-wide text-ink-muted">
              {LIBELLES[cle] ?? cle.replaceAll("_", " ")}
            </p>
            <p className="mt-1 text-display text-ink">
              {typeof valeur === "number" ? valeur.toLocaleString("fr-FR") : String(valeur)}
            </p>
          </article>
        ))}
      </section>


            {/* ---------------------- sections propres a l'agent terrain ---------------------- */}
      {data?.role === "agent_terrain" && (
        <>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/menages/nouveau"
              className="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2.5 text-body font-semibold text-on-primary transition hover:bg-primary-strong"
            >
              <Plus className="h-4 w-4" />
              Enregistrer un ménage
            </Link>
            <Link
              href="/activites/nouvelle"
              className="flex items-center gap-1.5 rounded-lg border border-primary/40 px-4 py-2.5 text-body font-semibold text-primary transition hover:bg-primary-soft"
            >
              <Plus className="h-4 w-4" />
              Enregistrer une activité
            </Link>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <SectionCollecte
              collecte={
                (data as TableauAgent).collecte_du_mois ?? { menages: 0, activites: 0 }
              }
            />
            <SectionACorriger activites={(data as TableauAgent).a_corriger ?? []} />
          </div>

          <SectionMesProjets projets={(data as TableauAgent).mes_projets ?? []} />
        </>
      )}

            {/* --------- sections propres au chef de projet et a la direction --------- */}
      {data && ["chef_projet", "coordinateur", "bailleur"].includes(data.role ?? "") && (
        <div className="grid gap-4 lg:grid-cols-2">
          <SectionBudget lignes={(data as TableauProjet).budget ?? []} />
          <SectionIndicateurs
            repartition={(data as TableauProjet).indicateurs?.repartition ?? {
              atteint: 0,
              en_cours: 0,
              en_retard: 0,
            }}
            detail={(data as TableauProjet).indicateurs?.detail ?? []}
          />
          <SectionPyramide sadd={(data as TableauProjet).sadd ?? {}} />
          <SectionEcheances echeances={(data as TableauProjet).echeances ?? []} />
        </div>
      )}

      {/* --------------------- section propre au superviseur --------------------- */}
      {data?.role === "superviseur" && (
        <div className="grid gap-4 lg:grid-cols-2">
          <SectionFileValidation
            activites={(data as TableauSuperviseur).file_validation ?? []}
          />
        </div>
      )}

      {/* --------------------- direction et suivi-evaluation --------------------- */}
      {data && ["direction", "suivi_evaluation"].includes(data.role ?? "") && (
        <div className="grid gap-4 lg:grid-cols-2">
          <SectionPyramide sadd={(data as TableauProjet).sadd ?? {}} />
        </div>
      )}
    </div>
  );
}