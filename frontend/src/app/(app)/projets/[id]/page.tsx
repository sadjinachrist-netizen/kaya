"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  LoaderCircle,
  MapPin,
  Pencil,
  Target,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";

import { api, ErreurApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ProjetDetail } from "@/lib/types";

const STATUT_STYLE: Record<string, string> = {
  brouillon: "bg-surface-low text-ink-muted",
  en_instruction: "bg-info-soft text-info",
  approuve: "bg-info-soft text-info",
  en_cours: "bg-success-soft text-success",
  suspendu: "bg-warning-soft text-warning",
  cloture: "bg-surface-low text-ink-muted",
  archive: "bg-surface-low text-ink-muted",
};

/** Intitulé de l'action qui mène vers chaque état. */
const TRANSITION_LIBELLE: Record<string, string> = {
  en_instruction: "Soumettre pour instruction",
  approuve: "Approuver le projet",
  en_cours: "Démarrer la mise en œuvre",
  brouillon: "Renvoyer en brouillon",
  suspendu: "Suspendre le projet",
  cloture: "Clôturer le projet",
  archive: "Archiver le projet",
};

/** Transitions pour lesquelles le modèle exige un motif écrit. */
const MOTIF_OBLIGATOIRE = new Set(["suspendu", "brouillon"]);

const dateLongue = (iso: string) =>
  new Date(iso).toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

export default function PageProjetDetail() {
  const { id } = useParams<{ id: string }>();
  const { peut } = useAuth();
  const client = useQueryClient();

  const [cible, setCible] = useState<string | null>(null);
  const [motif, setMotif] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["projet", id],
    queryFn: () => api<ProjetDetail>(`/projets/${id}/`),
  });

  const changerStatut = useMutation({
    mutationFn: (statut: string) =>
      api<ProjetDetail>(`/projets/${id}/changer-statut/`, {
        methode: "POST",
        corps: { statut, motif },
      }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["projet", id] });
      client.invalidateQueries({ queryKey: ["projets"] });
      client.invalidateQueries({ queryKey: ["tableau-de-bord"] });
      setCible(null);
      setMotif("");
      setErreur(null);
    },
    onError: (e) =>
      setErreur(e instanceof ErreurApi ? e.message : "La transition a été refusée."),
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
          Ce projet est introuvable ou hors de votre périmètre.
        </p>
        <Link href="/projets" className="mt-3 inline-block text-body text-primary underline">
          Retour à la liste
        </Link>
      </div>
    );
  }

  const membresActifs = data.members.filter((m) => m.is_active);
  const pilotable = peut("projet.modifier") && data.transitions_possibles.length > 0;

  return (
    <div className="space-y-5">
      <Link
        href="/projets"
        className="inline-flex items-center gap-1.5 text-caption text-ink-muted transition hover:text-ink"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Tous les projets
      </Link>

      <header className="rounded-card bg-surface p-6 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-overline uppercase tracking-wide text-ink-muted">
              {data.code}
            </p>
            <h1 className="mt-0.5 text-title leading-tight">{data.title}</h1>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`rounded-full px-3 py-1 text-caption ${
                STATUT_STYLE[data.status] ?? "bg-surface-low text-ink-muted"
              }`}
            >
              {data.status_label}
            </span>
            {peut("projet.modifier") && (
              <Link
                href={`/projets/${data.id}/modifier`}
                className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-caption text-ink transition hover:bg-surface-low"
              >
                <Pencil className="h-3.5 w-3.5" />
                Modifier
              </Link>
            )}
          </div>
        </div>

        {data.sector_labels.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {data.sector_labels.map((secteur) => (
              <span
                key={secteur}
                className="rounded bg-surface-low px-2 py-0.5 text-caption text-ink-muted"
              >
                {secteur}
              </span>
            ))}
          </div>
        )}

        <dl className="mt-5 grid gap-4 sm:grid-cols-3">
          <Meta libelle="Chef de projet" valeur={data.manager_name} />
          <Meta
            libelle="Période"
            valeur={`${dateLongue(data.start_date)} → ${dateLongue(data.end_date)}`}
          />
          <Meta
            libelle="Cible bénéficiaires"
            valeur={`${data.target_beneficiaries.toLocaleString("fr-FR")} personnes`}
          />
        </dl>
      </header>

      {/* ------------------------------ cycle de vie ------------------------------ */}
      {pilotable && (
        <section className="rounded-card bg-surface p-6 shadow-sm">
          <h2 className="text-heading">Cycle de vie</h2>
          <p className="mt-0.5 text-caption text-ink-muted">
            Seules les transitions prévues par le modèle sont proposées. Chacune est
            tracée dans le journal d&apos;audit.
          </p>

          <div className="mt-4 flex flex-wrap gap-2">
            {data.transitions_possibles.map((statut) => (
              <button
                key={statut}
                onClick={() => {
                  setCible(statut === cible ? null : statut);
                  setMotif("");
                  setErreur(null);
                }}
                className={`rounded-lg px-4 py-2.5 text-body font-semibold transition ${
                  cible === statut
                    ? "bg-primary text-on-primary"
                    : "border border-border text-ink hover:bg-surface-low"
                }`}
              >
                {TRANSITION_LIBELLE[statut] ?? statut}
              </button>
            ))}
          </div>

          {cible && (
            <div className="mt-4 border-t border-border pt-4">
              <label htmlFor="motif" className="text-caption text-ink-muted">
                Motif{" "}
                {MOTIF_OBLIGATOIRE.has(cible)
                  ? "— obligatoire pour cette transition"
                  : "— facultatif"}
              </label>
              <textarea
                id="motif"
                rows={2}
                value={motif}
                onChange={(e) => setMotif(e.target.value)}
                placeholder={
                  cible === "suspendu"
                    ? "Retard de décaissement du bailleur, insécurité dans la zone…"
                    : "Précision utile pour l'historique du projet…"
                }
                className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-body outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15"
              />

              <div className="mt-3 flex gap-2">
                <button
                  disabled={
                    changerStatut.isPending ||
                    (MOTIF_OBLIGATOIRE.has(cible) && motif.trim() === "")
                  }
                  onClick={() => changerStatut.mutate(cible)}
                  className="rounded-lg bg-primary px-4 py-2.5 text-body font-semibold text-on-primary transition hover:bg-primary-strong disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Confirmer : {TRANSITION_LIBELLE[cible] ?? cible}
                </button>
                <button
                  onClick={() => {
                    setCible(null);
                    setMotif("");
                  }}
                  className="rounded-lg border border-border px-4 py-2.5 text-body text-ink transition hover:bg-surface-low"
                >
                  Annuler
                </button>
              </div>
            </div>
          )}

          {erreur && (
            <p role="alert" className="mt-3 text-caption text-danger">
              {erreur}
            </p>
          )}
        </section>
      )}

      {/* ------------------------- avancement decompose ------------------------- */}
      <section className="rounded-card bg-surface p-6 shadow-sm">
        <h2 className="text-heading">Avancement</h2>
        <p className="mt-1 text-caption text-ink-muted">
          Trois mesures indépendantes, sans moyenne pondérée : c&apos;est l&apos;écart
          entre elles qui informe.
        </p>
        <div className="mt-4 space-y-4">
          <Jauge libelle="Calendrier écoulé" valeur={data.avancement.temporel} teinte="bg-info" />
          <Jauge
            libelle="Cibles atteintes (moyenne des indicateurs)"
            valeur={data.avancement.indicateurs}
            teinte="bg-primary"
          />
          <Jauge
            libelle="Budget consommé"
            valeur={data.avancement.budgetaire}
            teinte="bg-warning"
          />
        </div>
      </section>

      {data.description && (
        <section className="rounded-card bg-surface p-6 shadow-sm">
          <h2 className="text-heading">Description</h2>
          <p className="mt-2 whitespace-pre-line text-body text-ink">{data.description}</p>
        </section>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <section className="rounded-card bg-surface p-6 shadow-sm">
          <h2 className="flex items-center gap-2 text-heading">
            <MapPin className="h-4 w-4 text-ink-muted" />
            Sites d&apos;intervention
            <span className="text-caption font-normal text-ink-muted">
              ({data.sites.length})
            </span>
          </h2>
          {data.sites.length === 0 ? (
            <p className="mt-3 text-body text-ink-muted">Aucun site renseigné.</p>
          ) : (
            <ul className="mt-3 divide-y divide-border">
              {data.sites.map((site) => (
                <li key={site.id} className="flex items-start justify-between gap-3 py-2.5">
                  <div>
                    <p className="text-body text-ink">{site.zone_name}</p>
                    <p className="text-caption text-ink-muted">{site.zone_path}</p>
                  </div>
                  {site.target_population !== null && (
                    <span className="shrink-0 whitespace-nowrap text-caption text-ink-muted">
                      {site.target_population.toLocaleString("fr-FR")} pers.
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="rounded-card bg-surface p-6 shadow-sm">
          <h2 className="flex items-center gap-2 text-heading">
            <Users className="h-4 w-4 text-ink-muted" />
            Équipe
            <span className="text-caption font-normal text-ink-muted">
              ({membresActifs.length} actif{membresActifs.length > 1 ? "s" : ""})
            </span>
          </h2>
          {data.members.length === 0 ? (
            <p className="mt-3 text-body text-ink-muted">Aucun membre affecté.</p>
          ) : (
            <ul className="mt-3 divide-y divide-border">
              {data.members.map((membre) => (
                <li key={membre.id} className="flex items-center justify-between gap-3 py-2.5">
                  <div>
                    <p className="text-body text-ink">{membre.user_name}</p>
                    <p className="text-caption text-ink-muted">{membre.role_label}</p>
                  </div>
                  {!membre.is_active && (
                    <span className="shrink-0 rounded-full bg-surface-low px-2 py-0.5 text-caption text-ink-muted">
                      Affectation close
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

function Meta({ libelle, valeur }: { libelle: string; valeur: string }) {
  return (
    <div>
      <dt className="text-caption uppercase tracking-wide text-ink-muted">{libelle}</dt>
      <dd className="mt-0.5 text-body text-ink">{valeur}</dd>
    </div>
  );
}

function Jauge({
  libelle,
  valeur,
  teinte,
}: {
  libelle: string;
  valeur: number | null;
  teinte: string;
}) {
  if (valeur === null) {
    return (
      <div className="flex items-center gap-2 text-body text-ink-muted">
        <Target className="h-3.5 w-3.5" />
        {libelle} — non renseigné pour ce projet
      </div>
    );
  }
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