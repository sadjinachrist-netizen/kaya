"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, LoaderCircle, Search, Sigma, X } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";

import { api, ErreurApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type {
  IndicateurDetail,
  IndicateurListe,
  PageResultats,
  ProjetListe,
  Releve,
} from "@/lib/types";

const STATUT: Record<string, { libelle: string; barre: string; texte: string }> = {
  atteint: { libelle: "Atteint", barre: "bg-success", texte: "text-success" },
  en_cours: { libelle: "En cours", barre: "bg-warning", texte: "text-warning" },
  en_retard: { libelle: "En retard", barre: "bg-danger", texte: "text-danger" },
};

const FILTRES = [
  { code: null, libelle: "Tous" },
  { code: "atteint", libelle: "Atteints" },
  { code: "en_cours", libelle: "En cours" },
  { code: "en_retard", libelle: "En retard" },
];

interface FormulaireReleve {
  period_start: string;
  period_end: string;
  achieved_value: string;
  comment: string;
}

export default function PageIndicateurs() {
  const { peut } = useAuth();
  const client = useQueryClient();

  const [saisie, setSaisie] = useState("");
  const [recherche, setRecherche] = useState("");
  const [statut, setStatut] = useState<string | null>(null);
  const [projet, setProjet] = useState("");
  const [selection, setSelection] = useState<number | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  useEffect(() => {
    const minuteur = setTimeout(() => setRecherche(saisie), 300);
    return () => clearTimeout(minuteur);
  }, [saisie]);

  const liste = useQuery({
    queryKey: ["indicateurs", recherche, statut, projet],
    queryFn: () =>
      api<PageResultats<IndicateurListe>>("/indicateurs/", {
        parametres: {
          ...(recherche ? { search: recherche } : {}),
          ...(statut ? { statut } : {}),
          ...(projet ? { projet } : {}),
        },
      }),
    placeholderData: (precedent) => precedent,
  });

  const detail = useQuery({
    queryKey: ["indicateur", selection],
    queryFn: () => api<IndicateurDetail>(`/indicateurs/${selection}/`),
    enabled: selection !== null,
  });

  const projets = useQuery({
    queryKey: ["projets", ""],
    queryFn: () => api<PageResultats<ProjetListe>>("/projets/"),
  });

  const { register, handleSubmit, reset, formState } = useForm<FormulaireReleve>();

  const rafraichir = () => {
    client.invalidateQueries({ queryKey: ["indicateurs"] });
    client.invalidateQueries({ queryKey: ["indicateur", selection] });
    client.invalidateQueries({ queryKey: ["tableau-de-bord"] });
  };

  const releverValeur = useMutation({
    mutationFn: (valeurs: FormulaireReleve) =>
      api<Releve>("/releves/", {
        methode: "POST",
        corps: {
          indicator: selection,
          period_start: valeurs.period_start,
          period_end: valeurs.period_end,
          achieved_value: valeurs.achieved_value,
          comment: valeurs.comment,
        },
      }),
    onSuccess: () => {
      reset();
      rafraichir();
      setErreur(null);
    },
    onError: (e) =>
      setErreur(e instanceof ErreurApi ? e.message : "Le relevé a été refusé."),
  });

  const validerReleve = useMutation({
    mutationFn: (id: number) =>
      api<Releve>(`/releves/${id}/valider/`, { methode: "POST" }),
    onSuccess: () => {
      rafraichir();
      setErreur(null);
    },
    onError: (e) =>
      setErreur(e instanceof ErreurApi ? e.message : "La validation a échoué."),
  });

  const indicateurs = liste.data?.results ?? [];
  const courant = detail.data;

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-title">Indicateurs</h1>
          <p className="mt-1 text-body text-ink-muted">
            Le statut compare l&apos;atteinte réelle à l&apos;atteinte attendue à cette
            date, et non à la cible finale.
          </p>
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
          <input
            type="search"
            value={saisie}
            onChange={(e) => setSaisie(e.target.value)}
            placeholder="Code, intitulé, définition…"
            aria-label="Rechercher un indicateur"
            className="w-full rounded-lg border border-border bg-surface py-2.5 pl-9 pr-3 text-body outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15"
          />
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-2">
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
        <select
          value={projet}
          onChange={(e) => {
            setProjet(e.target.value);
            setSelection(null);
          }}
          className="ml-auto rounded-lg border border-border bg-surface px-3 py-2 text-caption text-ink outline-none focus:border-primary"
        >
          <option value="">Tous les projets</option>
          {(projets.data?.results ?? []).map((p) => (
            <option key={p.id} value={p.id}>
              {p.code}
            </option>
          ))}
        </select>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_400px]">
        {/* ------------------------------- la liste ------------------------------- */}
        <section className="space-y-3">
          {liste.isLoading ? (
            <div className="flex h-48 items-center justify-center">
              <LoaderCircle className="h-5 w-5 animate-spin text-ink-muted" />
            </div>
          ) : indicateurs.length === 0 ? (
            <p className="rounded-card bg-surface p-8 text-center text-body text-ink-muted shadow-sm">
              Aucun indicateur ne correspond à ces critères.
            </p>
          ) : (
            indicateurs.map((indicateur) => {
              const style = STATUT[indicateur.statut_atteinte] ?? STATUT.en_cours;
              const taux = Math.min(indicateur.taux_atteinte, 100);
              return (
                <button
                  key={indicateur.id}
                  onClick={() => {
                    setSelection(indicateur.id);
                    setErreur(null);
                    reset();
                  }}
                  className={`w-full rounded-card p-5 text-left shadow-sm transition ${
                    selection === indicateur.id
                      ? "bg-primary-soft ring-1 ring-primary/30"
                      : "bg-surface hover:shadow-md"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-mono text-overline uppercase tracking-wide text-ink-muted">
                        {indicateur.code} · {indicateur.project_code}
                      </p>
                      <p className="mt-0.5 text-body text-ink">{indicateur.title}</p>
                    </div>
                    <span className={`shrink-0 text-caption ${style.texte}`}>
                      {style.libelle}
                    </span>
                  </div>

                  <div className="mt-3 flex items-baseline justify-between text-caption text-ink-muted">
                    <span>
                      {Number(indicateur.valeur_atteinte).toLocaleString("fr-FR")} /{" "}
                      {Number(indicateur.target).toLocaleString("fr-FR")}{" "}
                      {indicateur.unit_label.toLowerCase()}
                    </span>
                    <span>
                      {indicateur.taux_atteinte} % · attendu {indicateur.taux_attendu} %
                    </span>
                  </div>

                  <div className="relative mt-1 h-2 overflow-hidden rounded-full bg-surface-low">
                    <div
                      className={`h-full rounded-full ${style.barre}`}
                      style={{ width: `${taux}%` }}
                    />
                    <span
                      className="absolute top-0 h-full w-0.5 bg-ink/40"
                      style={{ left: `${Math.min(indicateur.taux_attendu, 100)}%` }}
                      title={`Attendu à cette date : ${indicateur.taux_attendu} %`}
                    />
                  </div>
                </button>
              );
            })
          )}
        </section>

        {/* ------------------------------ le panneau ------------------------------ */}
        <aside className="lg:sticky lg:top-20 lg:self-start">
          {selection === null ? (
            <div className="rounded-card bg-surface p-6 text-center text-body text-ink-muted shadow-sm">
              Sélectionnez un indicateur pour voir ses relevés.
            </div>
          ) : detail.isLoading || !courant ? (
            <div className="flex h-48 items-center justify-center rounded-card bg-surface shadow-sm">
              <LoaderCircle className="h-5 w-5 animate-spin text-ink-muted" />
            </div>
          ) : (
            <div className="rounded-card bg-surface p-5 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-mono text-overline uppercase tracking-wide text-ink-muted">
                    {courant.code}
                  </p>
                  <h2 className="text-heading leading-snug">{courant.title}</h2>
                </div>
                <button
                  onClick={() => setSelection(null)}
                  aria-label="Fermer le panneau"
                  className="text-ink-muted transition hover:text-ink"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              {courant.definition && (
                <p className="mt-3 text-caption text-ink-muted">{courant.definition}</p>
              )}

              <dl className="mt-4 space-y-2 text-body">
                <Ligne libelle="Référence" valeur={Number(courant.baseline).toLocaleString("fr-FR")} />
                <Ligne libelle="Cible" valeur={Number(courant.target).toLocaleString("fr-FR")} />
                <Ligne libelle="Unité" valeur={courant.unit_label} />
                <Ligne
                  libelle="Mode"
                  valeur={
                    courant.computation_mode === "calcule"
                      ? "Calculé automatiquement"
                      : "Saisi manuellement"
                  }
                />
                {courant.owner_name && <Ligne libelle="Responsable" valeur={courant.owner_name} />}
              </dl>

              {courant.disaggregations.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {courant.disaggregations.map((d) => (
                    <span
                      key={d.id}
                      className="rounded bg-surface-low px-2 py-0.5 text-caption text-ink-muted"
                    >
                      {d.dimension_label}
                    </span>
                  ))}
                </div>
              )}

              {courant.valeur_calculee !== null && (
                <p className="mt-3 flex items-center gap-1.5 rounded-lg bg-info-soft px-3 py-2 text-caption text-info">
                  <Sigma className="h-3.5 w-3.5 shrink-0" />
                  Valeur proposée par le système :{" "}
                  {Number(courant.valeur_calculee).toLocaleString("fr-FR")}
                </p>
              )}

              {/* --------------------------- les releves --------------------------- */}
              <h3 className="mt-5 border-t border-border pt-4 text-body font-semibold text-ink">
                Relevés
              </h3>
              {courant.readings.length === 0 ? (
                <p className="mt-2 text-caption text-ink-muted">Aucun relevé enregistré.</p>
              ) : (
                <ul className="mt-2 divide-y divide-border">
                  {[...courant.readings]
                    .sort((a, b) => b.period_end.localeCompare(a.period_end))
                    .map((releve) => (
                      <li key={releve.id} className="py-2.5">
                        <div className="flex items-baseline justify-between gap-2">
                          <span className="text-body text-ink">
                            {Number(releve.achieved_value).toLocaleString("fr-FR")}
                          </span>
                          <span className="text-caption text-ink-muted">
                            {releve.period_start} → {releve.period_end}
                          </span>
                        </div>
                        <div className="mt-1 flex items-center justify-between gap-2">
                          <span
                            className={`rounded-full px-2 py-0.5 text-caption ${
                              releve.status === "valide"
                                ? "bg-success-soft text-success"
                                : "bg-surface-low text-ink-muted"
                            }`}
                          >
                            {releve.status === "valide" ? "Validé" : "Brouillon"}
                          </span>
                          {releve.status !== "valide" && peut("indicateur.valider") && (
                            <button
                              disabled={validerReleve.isPending}
                              onClick={() => validerReleve.mutate(releve.id)}
                              className="flex items-center gap-1 text-caption text-primary underline disabled:opacity-50"
                            >
                              <Check className="h-3 w-3" />
                              Valider
                            </button>
                          )}
                        </div>
                        {releve.comment && (
                          <p className="mt-1 text-caption text-ink-muted">{releve.comment}</p>
                        )}
                      </li>
                    ))}
                </ul>
              )}

              {/* ------------------------ saisir un releve ------------------------ */}
              {peut("indicateur.relever") && (
                <form
                  onSubmit={handleSubmit((v) => releverValeur.mutate(v))}
                  className="mt-4 space-y-3 border-t border-border pt-4"
                >
                  <h3 className="text-body font-semibold text-ink">Nouveau relevé</h3>
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-caption text-ink-muted">Début de période</label>
                      <input
                        type="date"
                        {...register("period_start", { required: true })}
                        className={`mt-1 ${saisieClasse}`}
                      />
                    </div>
                    <div>
                      <label className="text-caption text-ink-muted">Fin de période</label>
                      <input
                        type="date"
                        {...register("period_end", { required: true })}
                        className={`mt-1 ${saisieClasse}`}
                      />
                    </div>
                  </div>
                  <div>
                    <label className="text-caption text-ink-muted">Valeur atteinte</label>
                    <input
                      type="number"
                      step="0.01"
                      {...register("achieved_value", { required: true })}
                      className={`mt-1 ${saisieClasse}`}
                    />
                  </div>
                  <div>
                    <label className="text-caption text-ink-muted">Commentaire</label>
                    <textarea
                      rows={2}
                      {...register("comment")}
                      placeholder="Source, méthode, réserves…"
                      className={`mt-1 ${saisieClasse}`}
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={releverValeur.isPending || !formState.isValid}
                    className="w-full rounded-lg bg-primary px-3 py-2.5 text-body font-semibold text-on-primary transition hover:bg-primary-strong disabled:opacity-50"
                  >
                    Enregistrer le relevé
                  </button>
                  <p className="text-caption text-ink-muted">
                    Un relevé est créé en brouillon : il n&apos;influence l&apos;indicateur
                    qu&apos;une fois validé.
                  </p>
                </form>
              )}

              {erreur && (
                <p role="alert" className="mt-3 text-caption text-danger">
                  {erreur}
                </p>
              )}
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}

const saisieClasse =
  "w-full rounded-lg border border-border bg-surface px-3 py-2 text-body text-ink outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15";

function Ligne({ libelle, valeur }: { libelle: string; valeur: string }) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-ink-muted">{libelle}</dt>
      <dd className="text-right text-ink">{valeur}</dd>
    </div>
  );
}