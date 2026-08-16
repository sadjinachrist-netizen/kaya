"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, LoaderCircle, SplitSquareHorizontal } from "lucide-react";

import { api, ErreurApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Doublon, PageResultats, ResumeMenage } from "@/lib/types";
import { useState } from "react";

export default function PageDoublons() {
  const { peut } = useAuth();
  const client = useQueryClient();
  const [erreur, setErreur] = useState<string | null>(null);

  const liste = useQuery({
    queryKey: ["doublons"],
    queryFn: () =>
      api<PageResultats<Doublon>>("/doublons/", {
        parametres: { statut: "a_arbitrer" },
      }),
  });

  const arbitrer = useMutation({
    mutationFn: ({ id, confirme }: { id: number; confirme: boolean }) =>
      api<Doublon>(`/doublons/${id}/arbitrer/`, {
        methode: "POST",
        corps: { confirme },
      }),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["doublons"] });
      client.invalidateQueries({ queryKey: ["menages"] });
      client.invalidateQueries({ queryKey: ["tableau-de-bord"] });
      setErreur(null);
    },
    onError: (e) =>
      setErreur(e instanceof ErreurApi ? e.message : "L'arbitrage a échoué."),
  });

  if (!peut("doublon.arbitrer")) {
    return (
      <p className="rounded-card bg-surface p-6 text-body text-ink-muted">
        L&apos;arbitrage des doublons est réservé aux superviseurs.
      </p>
    );
  }

  const doublons = liste.data?.results ?? [];

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-title">Doublons à arbitrer</h1>
        <p className="mt-1 text-body text-ink-muted">
          Rapprochements proposés par le système sur le nom du chef de ménage, la
          localité et la taille du foyer. La machine propose, vous tranchez.
        </p>
      </header>

      {erreur && (
        <p role="alert" className="rounded-lg bg-danger-soft px-4 py-3 text-body text-danger">
          {erreur}
        </p>
      )}

      {liste.isLoading ? (
        <div className="flex h-48 items-center justify-center">
          <LoaderCircle className="h-5 w-5 animate-spin text-ink-muted" />
        </div>
      ) : doublons.length === 0 ? (
        <p className="rounded-card bg-surface p-8 text-center text-body text-ink-muted shadow-sm">
          Aucun rapprochement en attente. La file est vide.
        </p>
      ) : (
        <div className="space-y-4">
          {doublons.map((doublon) => {
            const similarite = Math.round(Number(doublon.score) * 100);
            return (
              <article key={doublon.id} className="rounded-card bg-surface p-6 shadow-sm">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h2 className="flex items-center gap-2 text-heading">
                    <Copy className="h-4 w-4 text-ink-muted" />
                    Rapprochement proposé
                  </h2>
                  <span
                    className={`rounded-full px-3 py-1 text-caption ${
                      similarite >= 85
                        ? "bg-danger-soft text-danger"
                        : "bg-warning-soft text-warning"
                    }`}
                  >
                    {similarite} % de similarité
                  </span>
                </div>

                <div className="mt-4 grid gap-4 md:grid-cols-2">
                  <Fiche menage={doublon.menage_a} etiquette="Enregistrement le plus ancien" />
                  <Fiche menage={doublon.menage_b} etiquette="Enregistrement le plus récent" />
                </div>

                <div className="mt-5 flex flex-wrap gap-3 border-t border-border pt-4">
                  <button
                    disabled={arbitrer.isPending}
                    onClick={() => arbitrer.mutate({ id: doublon.id, confirme: true })}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-danger px-4 py-2.5 text-body font-semibold text-white transition hover:opacity-90 disabled:opacity-60"
                  >
                    <Copy className="h-4 w-4" />
                    C&apos;est le même ménage
                  </button>
                  <button
                    disabled={arbitrer.isPending}
                    onClick={() => arbitrer.mutate({ id: doublon.id, confirme: false })}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-border px-4 py-2.5 text-body font-semibold text-ink transition hover:bg-surface-low disabled:opacity-60"
                  >
                    <SplitSquareHorizontal className="h-4 w-4" />
                    Ce sont deux ménages distincts
                  </button>
                </div>

                <p className="mt-3 text-caption text-ink-muted">
                  Confirmer le doublon marque le second enregistrement comme tel : il
                  sort des effectifs sans être supprimé, et reste consultable.
                </p>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Fiche({ menage, etiquette }: { menage: ResumeMenage; etiquette: string }) {
  return (
    <div className="rounded-lg border border-border p-4">
      <p className="text-overline uppercase tracking-wide text-ink-muted">{etiquette}</p>
      <p className="mt-1 text-heading text-ink">{menage.head_name}</p>
      <p className="font-mono text-caption text-ink-muted">{menage.code}</p>

      <dl className="mt-3 space-y-1.5 text-body">
        <Ligne libelle="Localité" valeur={menage.zone} />
        <Ligne libelle="Taille" valeur={`${menage.size} personnes`} />
        <Ligne
          libelle="Enregistré le"
          valeur={new Date(menage.registered_at).toLocaleDateString("fr-FR")}
        />
        <Ligne libelle="Par" valeur={menage.registered_by} />
      </dl>
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