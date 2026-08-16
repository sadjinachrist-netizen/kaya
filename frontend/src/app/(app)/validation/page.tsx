"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  Check,
  Clock,
  LoaderCircle,
  MapPin,
  Paperclip,
  Users,
  X,
} from "lucide-react";
import { useState } from "react";

import { api, ErreurApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ActiviteDetail, ActiviteListe, PageResultats } from "@/lib/types";

export default function PageValidation() {
  const { peut } = useAuth();
  const client = useQueryClient();
  const [selection, setSelection] = useState<number | null>(null);
  const [motif, setMotif] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);

  const file = useQuery({
    queryKey: ["activites", "soumise"],
    queryFn: () =>
      api<PageResultats<ActiviteListe>>("/activites/", {
        parametres: { statut: "soumise" },
      }),
  });

  const detail = useQuery({
    queryKey: ["activite", selection],
    queryFn: () => api<ActiviteDetail>(`/activites/${selection}/`),
    enabled: selection !== null,
  });

  const statuer = useMutation({
    mutationFn: async ({ id, action }: { id: number; action: "valider" | "rejeter" }) =>
      api<ActiviteDetail>(`/activites/${id}/${action}/`, {
        methode: "POST",
        corps: action === "rejeter" ? { motif } : undefined,
      }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["activites"] });
      client.invalidateQueries({ queryKey: ["tableau-de-bord"] });
      setSelection(null);
      setMotif("");
      setErreur(null);
    },
    onError: (e) =>
      setErreur(e instanceof ErreurApi ? e.message : "L'action a échoué."),
  });

  if (!peut("activite.valider")) {
    return (
      <p className="rounded-card bg-surface p-6 text-body text-ink-muted">
        Vous ne disposez pas des droits de validation.
      </p>
    );
  }

  const activites = file.data?.results ?? [];

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-title">File de validation</h1>
        <p className="mt-1 text-body text-ink-muted">
          Contrôlez les saisies remontées par le terrain avant qu'elles n'alimentent
          les indicateurs.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-[1fr_380px]">
        {/* ------------------------------ tableau ------------------------------ */}
        <section className="rounded-card bg-surface shadow-sm">
          {file.isLoading ? (
            <div className="flex h-48 items-center justify-center">
              <LoaderCircle className="h-5 w-5 animate-spin text-ink-muted" />
            </div>
          ) : activites.length === 0 ? (
            <p className="p-8 text-center text-body text-ink-muted">
              Aucune activité en attente de validation.
            </p>
          ) : (
            <div className="scrollbar-fine overflow-x-auto">
              <table className="w-full text-body">
                <thead>
                  <tr className="border-b border-border text-left text-overline uppercase tracking-wide text-ink-muted">
                    <th className="px-4 py-3 font-semibold">Date</th>
                    <th className="px-4 py-3 font-semibold">Agent</th>
                    <th className="px-4 py-3 font-semibold">Activité</th>
                    <th className="px-4 py-3 font-semibold">Localité</th>
                    <th className="px-4 py-3 font-semibold">Qualité</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {activites.map((activite) => {
                    const actif = selection === activite.id;
                    return (
                      <tr
                        key={activite.id}
                        onClick={() => {
                          setSelection(activite.id);
                          setMotif("");
                          setErreur(null);
                        }}
                        className={`cursor-pointer transition ${
                          actif ? "bg-primary-soft" : "hover:bg-surface-low"
                        }`}
                      >
                        <td className="whitespace-nowrap px-4 py-3 text-ink-muted">
                          {activite.activity_date}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3">{activite.agent_name}</td>
                        <td className="px-4 py-3">
                          <p className="text-ink">{activite.type_label}</p>
                          <p className="text-caption text-ink-muted">
                            {activite.project_code}
                          </p>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-ink-muted">
                          {activite.zone_name}
                        </td>
                        <td className="px-4 py-3">
                          {activite.nb_alertes === 0 ? (
                            <span className="rounded-full bg-success-soft px-2.5 py-0.5 text-caption text-success">
                              Standard
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 rounded-full bg-warning-soft px-2.5 py-0.5 text-caption text-warning">
                              <AlertTriangle className="h-3 w-3" />
                              {activite.nb_alertes} alerte
                              {activite.nb_alertes > 1 ? "s" : ""}
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

        {/* --------------------------- panneau detail --------------------------- */}
        <aside className="lg:sticky lg:top-20 lg:self-start">
          {selection === null ? (
            <div className="rounded-card bg-surface p-6 text-center text-body text-ink-muted shadow-sm">
              Sélectionnez une activité pour en voir le détail.
            </div>
          ) : detail.isLoading || !detail.data ? (
            <div className="flex h-48 items-center justify-center rounded-card bg-surface shadow-sm">
              <LoaderCircle className="h-5 w-5 animate-spin text-ink-muted" />
            </div>
          ) : (
            <div className="rounded-card bg-surface p-5 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-overline uppercase tracking-wide text-ink-muted">
                    {detail.data.code}
                  </p>
                  <h2 className="text-heading">{detail.data.type_label}</h2>
                </div>
                <button
                  onClick={() => setSelection(null)}
                  aria-label="Fermer le panneau"
                  className="text-ink-muted transition hover:text-ink"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {detail.data.alertes_qualite.length > 0 && (
                <div className="mt-4 rounded-lg border border-warning/25 bg-warning-soft p-3">
                  <p className="flex items-center gap-1.5 text-body font-semibold text-warning">
                    <AlertTriangle className="h-4 w-4" />
                    Alertes qualité
                  </p>
                  <ul className="mt-1.5 list-inside list-disc space-y-0.5 text-caption text-warning">
                    {detail.data.alertes_qualite.map((alerte) => (
                      <li key={alerte}>{alerte}</li>
                    ))}
                  </ul>
                </div>
              )}

              <dl className="mt-4 space-y-2.5 text-body">
                <Ligne libelle="Projet" valeur={detail.data.project_code} />
                <Ligne libelle="Agent" valeur={detail.data.agent_name} />
                <Ligne libelle="Réalisée le" valeur={detail.data.activity_date} />
                <Ligne libelle="Localité" valeur={detail.data.zone_name} />
              </dl>

              <p className="mt-4 text-caption uppercase tracking-wide text-ink-muted">
                Description
              </p>
              <p className="mt-1 text-body text-ink">{detail.data.description}</p>

              {detail.data.results && (
                <>
                  <p className="mt-3 text-caption uppercase tracking-wide text-ink-muted">
                    Résultats
                  </p>
                  <p className="mt-1 text-body text-ink">{detail.data.results}</p>
                </>
              )}

              <div className="mt-4 flex flex-wrap gap-3 text-caption text-ink-muted">
                <span className="flex items-center gap-1">
                  <Users className="h-3.5 w-3.5" />
                  {detail.data.participants_totaux.total} participants
                </span>
                {detail.data.latitude && (
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3.5 w-3.5" />
                    {Number(detail.data.latitude).toFixed(3)},{" "}
                    {Number(detail.data.longitude).toFixed(3)}
                    {detail.data.gps_accuracy && ` (±${detail.data.gps_accuracy} m)`}
                  </span>
                )}
                {detail.data.entry_duration_seconds !== null && (
                  <span className="flex items-center gap-1">
                    <Clock className="h-3.5 w-3.5" />
                    {Math.round(detail.data.entry_duration_seconds / 60)} min de saisie
                  </span>
                )}
                <span className="flex items-center gap-1">
                  <Paperclip className="h-3.5 w-3.5" />
                  {detail.data.attachments.length} pièce
                  {detail.data.attachments.length > 1 ? "s" : ""}
                </span>
              </div>

              {/* ---------------------------- actions ---------------------------- */}
              <div className="mt-5 border-t border-border pt-4">
                <label htmlFor="motif" className="text-caption text-ink-muted">
                  Motif — obligatoire en cas de rejet
                </label>
                <textarea
                  id="motif"
                  rows={2}
                  value={motif}
                  onChange={(e) => setMotif(e.target.value)}
                  placeholder="Liste de présence illisible, merci de la rescanner…"
                  className="mt-1 w-full rounded-lg border border-border bg-surface px-3 py-2 text-body outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15"
                />

                {erreur && (
                  <p role="alert" className="mt-2 text-caption text-danger">
                    {erreur}
                  </p>
                )}

                <div className="mt-3 flex gap-2">
                  <button
                    disabled={statuer.isPending}
                    onClick={() =>
                      statuer.mutate({ id: detail.data!.id, action: "valider" })
                    }
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-primary px-3 py-2.5 text-body font-semibold text-on-primary transition hover:bg-primary-strong disabled:opacity-60"
                  >
                    <Check className="h-4 w-4" />
                    Valider
                  </button>
                  <button
                    disabled={statuer.isPending || motif.trim() === ""}
                    title={motif.trim() === "" ? "Renseignez un motif de rejet" : undefined}
                    onClick={() =>
                      statuer.mutate({ id: detail.data!.id, action: "rejeter" })
                    }
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-danger/40 px-3 py-2.5 text-body font-semibold text-danger transition hover:bg-danger-soft disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    <X className="h-4 w-4" />
                    Rejeter
                  </button>
                </div>
              </div>
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