"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  LoaderCircle,
  MapPin,
  Paperclip,
  Plus,
  RotateCcw,
  Search,
  Send,
  Users,
  X,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { api, ErreurApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ActiviteDetail, ActiviteListe, PageResultats } from "@/lib/types";

const STATUT: Record<string, { libelle: string; style: string }> = {
  brouillon: { libelle: "Brouillon", style: "bg-surface-low text-ink-muted" },
  synchronisee: { libelle: "Synchronisée", style: "bg-info-soft text-info" },
  soumise: { libelle: "Soumise", style: "bg-warning-soft text-warning" },
  validee: { libelle: "Validée", style: "bg-success-soft text-success" },
  rejetee: { libelle: "Rejetée", style: "bg-danger-soft text-danger" },
};

const FILTRES = [
  { code: null, libelle: "Toutes" },
  { code: "brouillon", libelle: "Brouillons" },
  { code: "soumise", libelle: "Soumises" },
  { code: "validee", libelle: "Validées" },
  { code: "rejetee", libelle: "Rejetées" },
];

export default function PageActivites() {
  const { utilisateur, peut } = useAuth();
  const client = useQueryClient();

  const [saisie, setSaisie] = useState("");
  const [recherche, setRecherche] = useState("");
  const [statut, setStatut] = useState<string | null>(null);
  const [selection, setSelection] = useState<number | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    const minuteur = setTimeout(() => setRecherche(saisie), 300);
    return () => clearTimeout(minuteur);
  }, [saisie]);

  const liste = useQuery({
    queryKey: ["activites", statut, recherche],
    queryFn: () =>
      api<PageResultats<ActiviteListe>>("/activites/", {
        parametres: {
          ...(statut ? { statut } : {}),
          ...(recherche ? { search: recherche } : {}),
        },
      }),
    placeholderData: (precedent) => precedent,
  });

  const detail = useQuery({
    queryKey: ["activite", selection],
    queryFn: () => api<ActiviteDetail>(`/activites/${selection}/`),
    enabled: selection !== null,
  });

  const agir = useMutation({
    mutationFn: ({ id, action }: { id: number; action: "soumettre" | "corriger" }) =>
      api<ActiviteDetail>(`/activites/${id}/${action}/`, { methode: "POST" }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["activites"] });
      client.invalidateQueries({ queryKey: ["activite", selection] });
      client.invalidateQueries({ queryKey: ["tableau-de-bord"] });
      setErreur(null);
    },
    onError: (e) =>
      setErreur(e instanceof ErreurApi ? e.message : "L'action a échoué."),
  });

  const activites = liste.data?.results ?? [];
  const courante = detail.data;
  const estAuteur = courante?.agent === utilisateur?.id;

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-title">Activités terrain</h1>
          <p className="mt-1 text-body text-ink-muted">
            {(liste.data?.count ?? 0).toLocaleString("fr-FR")} activité
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
              placeholder="Code, description, résultats…"
              aria-label="Rechercher une activité"
              className="w-full rounded-lg border border-border bg-surface py-2.5 pl-9 pr-3 text-body outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15"
            />
          </div>
          {peut("activite.creer") && (
            <Link
              href="/activites/nouvelle"
              className="flex shrink-0 items-center gap-1.5 rounded-lg bg-primary px-4 py-2.5 text-body font-semibold text-on-primary transition hover:bg-primary-strong"
            >
              <Plus className="h-4 w-4" />
              Nouvelle
            </Link>
          )}
        </div>
      </header>

      <div className="flex flex-wrap gap-2">
        {FILTRES.map((filtre) => (
          <button
            key={filtre.libelle}
            onClick={() => {
              setStatut(filtre.code);
              setSelection(null);
            }}
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

      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <section className="rounded-card bg-surface shadow-sm">
          {liste.isLoading ? (
            <div className="flex h-48 items-center justify-center">
              <LoaderCircle className="h-5 w-5 animate-spin text-ink-muted" />
            </div>
          ) : activites.length === 0 ? (
            <p className="p-8 text-center text-body text-ink-muted">
              Aucune activité ne correspond à ces critères.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-body">
                <thead>
                  <tr className="border-b border-border text-left text-overline uppercase tracking-wide text-ink-muted">
                    <th className="px-4 py-3 font-semibold">Date</th>
                    <th className="px-4 py-3 font-semibold">Activité</th>
                    <th className="px-4 py-3 font-semibold">Localité</th>
                    <th className="px-4 py-3 font-semibold">Agent</th>
                    <th className="px-4 py-3 font-semibold">Statut</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {activites.map((activite) => {
                    const badge = STATUT[activite.status];
                    return (
                      <tr
                        key={activite.id}
                        onClick={() => {
                          setSelection(activite.id);
                          setErreur(null);
                        }}
                        className={`cursor-pointer transition ${
                          selection === activite.id
                            ? "bg-primary-soft"
                            : "hover:bg-surface-low"
                        }`}
                      >
                        <td className="whitespace-nowrap px-4 py-3 text-ink-muted">
                          {activite.activity_date}
                        </td>
                        <td className="px-4 py-3">
                          <p className="text-ink">{activite.type_label}</p>
                          <p className="font-mono text-caption text-ink-muted">
                            {activite.code} · {activite.project_code}
                          </p>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-ink-muted">
                          {activite.zone_name}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3">
                          {activite.agent_name}
                        </td>
                        <td className="px-4 py-3">
                          <span
                            className={`whitespace-nowrap rounded-full px-2.5 py-0.5 text-caption ${
                              badge?.style ?? "bg-surface-low text-ink-muted"
                            }`}
                          >
                            {badge?.libelle ?? activite.status_label}
                          </span>
                          {activite.nb_alertes > 0 && (
                            <span className="ml-1.5 inline-flex items-center gap-0.5 text-caption text-warning">
                              <AlertTriangle className="h-3 w-3" />
                              {activite.nb_alertes}
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <aside className="lg:sticky lg:top-20 lg:self-start">
          {selection === null ? (
            <div className="rounded-card bg-surface p-6 text-center text-body text-ink-muted shadow-sm">
              Sélectionnez une activité pour en voir le détail.
            </div>
          ) : detail.isLoading || !courante ? (
            <div className="flex h-48 items-center justify-center rounded-card bg-surface shadow-sm">
              <LoaderCircle className="h-5 w-5 animate-spin text-ink-muted" />
            </div>
          ) : (
            <div className="rounded-card bg-surface p-5 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-mono text-overline uppercase tracking-wide text-ink-muted">
                    {courante.code}
                  </p>
                  <h2 className="text-heading">{courante.type_label}</h2>
                </div>
                <button
                  onClick={() => setSelection(null)}
                  aria-label="Fermer le panneau"
                  className="text-ink-muted transition hover:text-ink"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {courante.status === "rejetee" && courante.rejection_reason && (
                <div className="mt-4 rounded-lg border border-danger/25 bg-danger-soft p-3">
                  <p className="text-body font-semibold text-danger">Motif du rejet</p>
                  <p className="mt-0.5 text-caption text-danger">
                    {courante.rejection_reason}
                  </p>
                </div>
              )}

              {courante.alertes_qualite.length > 0 && (
                <div className="mt-4 rounded-lg border border-warning/25 bg-warning-soft p-3">
                  <p className="flex items-center gap-1.5 text-body font-semibold text-warning">
                    <AlertTriangle className="h-4 w-4" />
                    Alertes qualité
                  </p>
                  <ul className="mt-1.5 list-inside list-disc space-y-0.5 text-caption text-warning">
                    {courante.alertes_qualite.map((alerte) => (
                      <li key={alerte}>{alerte}</li>
                    ))}
                  </ul>
                </div>
              )}

              <dl className="mt-4 space-y-2.5 text-body">
                <Ligne libelle="Projet" valeur={courante.project_code} />
                <Ligne libelle="Agent" valeur={courante.agent_name} />
                <Ligne libelle="Réalisée le" valeur={courante.activity_date} />
                <Ligne libelle="Localité" valeur={courante.zone_name} />
                {courante.validated_by_name && (
                  <Ligne libelle="Statuée par" valeur={courante.validated_by_name} />
                )}
              </dl>

              <p className="mt-4 text-caption uppercase tracking-wide text-ink-muted">
                Description
              </p>
              <p className="mt-1 text-body text-ink">{courante.description}</p>

              <div className="mt-4 flex flex-wrap gap-3 text-caption text-ink-muted">
                <span className="flex items-center gap-1">
                  <Users className="h-3.5 w-3.5" />
                  {courante.participants_totaux.total} participants
                </span>
                {courante.latitude && (
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3.5 w-3.5" />
                    {Number(courante.latitude).toFixed(3)},{" "}
                    {Number(courante.longitude).toFixed(3)}
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Paperclip className="h-3.5 w-3.5" />
                  {courante.attachments.length} pièce
                  {courante.attachments.length > 1 ? "s" : ""}
                </span>
              </div>

              {erreur && (
                <p role="alert" className="mt-3 text-caption text-danger">
                  {erreur}
                </p>
              )}

              {/* actions reservees a l'auteur de la saisie */}
              {estAuteur &&
                ["brouillon", "synchronisee"].includes(courante.status) && (
                  <button
                    disabled={agir.isPending}
                    onClick={() =>
                      agir.mutate({ id: courante.id, action: "soumettre" })
                    }
                    className="mt-5 flex w-full items-center justify-center gap-1.5 rounded-lg bg-primary px-3 py-2.5 text-body font-semibold text-on-primary transition hover:bg-primary-strong disabled:opacity-60"
                  >
                    <Send className="h-4 w-4" />
                    Soumettre à validation
                  </button>
                )}

              {estAuteur && courante.status === "rejetee" && (
                <button
                  disabled={agir.isPending}
                  onClick={() => agir.mutate({ id: courante.id, action: "corriger" })}
                  className="mt-5 flex w-full items-center justify-center gap-1.5 rounded-lg border border-primary/40 px-3 py-2.5 text-body font-semibold text-primary transition hover:bg-primary-soft disabled:opacity-60"
                >
                  <RotateCcw className="h-4 w-4" />
                  Reprendre pour correction
                </button>
              )}

              {courante.status === "validee" && (
                <p className="mt-5 rounded-lg bg-success-soft px-3 py-2.5 text-center text-caption text-success">
                  Activité validée — elle alimente désormais les indicateurs et ne peut
                  plus être modifiée.
                </p>
              )}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

function Ligne({ libelle, valeur }: { libelle: string; valeur: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-ink-muted">{libelle}</dt>
      <dd className="text-right text-ink">{valeur}</dd>
    </div>
  );
}