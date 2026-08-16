"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, LoaderCircle, Plus, TriangleAlert, X } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { api, ErreurApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type {
  ConventionListe,
  Depense,
  Devise,
  LigneBudgetaire,
  PageResultats,
  ProjetListe,
} from "@/lib/types";

const STATUT: Record<string, { libelle: string; style: string }> = {
  saisie: { libelle: "En attente", style: "bg-warning-soft text-warning" },
  validee: { libelle: "Validée", style: "bg-success-soft text-success" },
  rejetee: { libelle: "Rejetée", style: "bg-danger-soft text-danger" },
};

const FILTRES = [
  { code: "saisie", libelle: "En attente" },
  { code: "validee", libelle: "Validées" },
  { code: "rejetee", libelle: "Rejetées" },
  { code: null, libelle: "Toutes" },
];

interface Champs {
  financement: string;
  budget_line: string;
  project: string;
  label: string;
  amount: string;
  currency: string;
  expense_date: string;
}

const argent = (montant: string, devise: string) =>
  `${new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 0 }).format(
    Number(montant),
  )} ${devise}`;

export default function PageDepenses() {
  const { peut } = useAuth();
  const client = useQueryClient();

  const [statut, setStatut] = useState<string | null>("saisie");
  const [saisieOuverte, setSaisieOuverte] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);
  const [alerte, setAlerte] = useState<string | null>(null);

  const { register, handleSubmit, watch, reset, formState } = useForm<Champs>({
    defaultValues: {
      financement: "",
      budget_line: "",
      project: "",
      label: "",
      amount: "",
      currency: "",
      expense_date: new Date().toISOString().slice(0, 10),
    },
  });

  const financementChoisi = watch("financement");

  const liste = useQuery({
    queryKey: ["depenses", statut],
    queryFn: () =>
      api<PageResultats<Depense>>("/depenses/", {
        parametres: statut ? { statut } : undefined,
      }),
    placeholderData: (precedent) => precedent,
  });

  const conventions = useQuery({
    queryKey: ["financements", ""],
    queryFn: () => api<PageResultats<ConventionListe>>("/financements/"),
  });

  const projets = useQuery({
    queryKey: ["projets", ""],
    queryFn: () => api<PageResultats<ProjetListe>>("/projets/"),
  });

  const devises = useQuery({
    queryKey: ["devises"],
    queryFn: () => api<Devise[]>("/devises/"),
  });

  const lignes = useQuery({
    queryKey: ["lignes-budgetaires", financementChoisi],
    queryFn: () =>
      api<LigneBudgetaire[]>("/lignes-budgetaires/", {
        parametres: { financement: financementChoisi },
      }),
    enabled: financementChoisi !== "",
  });

  const rafraichir = () => {
    client.invalidateQueries({ queryKey: ["depenses"] });
    client.invalidateQueries({ queryKey: ["financements"] });
    client.invalidateQueries({ queryKey: ["tableau-de-bord"] });
  };

  const enregistrer = useMutation({
    mutationFn: (valeurs: Champs) =>
      api<Depense>("/depenses/", {
        methode: "POST",
        corps: {
          budget_line: Number(valeurs.budget_line),
          project: Number(valeurs.project),
          label: valeurs.label,
          amount: valeurs.amount,
          currency: Number(valeurs.currency),
          expense_date: valeurs.expense_date,
        },
      }),
    onSuccess: () => {
      reset();
      setSaisieOuverte(false);
      setErreur(null);
      rafraichir();
    },
    onError: (e) =>
      setErreur(e instanceof ErreurApi ? e.message : "La dépense a été refusée."),
  });

  const statuer = useMutation({
    mutationFn: ({ id, action }: { id: number; action: "valider" | "rejeter" }) =>
      api<Depense & { alerte?: string }>(`/depenses/${id}/${action}/`, {
        methode: "POST",
      }),
    onSuccess: (reponse) => {
      setAlerte(reponse.alerte ?? null);
      setErreur(null);
      rafraichir();
    },
    onError: (e) =>
      setErreur(e instanceof ErreurApi ? e.message : "L'action a échoué."),
  });

  const depenses = liste.data?.results ?? [];

  return (
    <div className="space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-title">Dépenses</h1>
          <p className="mt-1 text-body text-ink-muted">
            Toute dépense s&apos;impute sur une ligne budgétaire et doit tomber dans la
            période d&apos;éligibilité de la convention.
          </p>
        </div>
        {peut("depense.saisir") && (
          <button
            onClick={() => {
              setSaisieOuverte((ouverte) => !ouverte);
              setErreur(null);
            }}
            className="flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2.5 text-body font-semibold text-on-primary transition hover:bg-primary-strong"
          >
            <Plus className="h-4 w-4" />
            Nouvelle dépense
          </button>
        )}
      </header>

      {/* ---------------------------- saisie d'une depense ---------------------------- */}
      {saisieOuverte && (
        <form
          onSubmit={handleSubmit((v) => enregistrer.mutate(v))}
          className="rounded-card bg-surface p-6 shadow-sm"
        >
          <h2 className="text-heading">Enregistrer une dépense</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Champ libelle="Convention">
              <select {...register("financement", { required: true })} className={saisie}>
                <option value="">— Choisir —</option>
                {(conventions.data?.results ?? []).map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.contract_number} — {c.donor_name}
                  </option>
                ))}
              </select>
            </Champ>

            <Champ libelle="Ligne budgétaire">
              <select
                {...register("budget_line", { required: true })}
                disabled={!financementChoisi}
                className={saisie}
              >
                <option value="">— Choisir —</option>
                {(lignes.data ?? []).map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.code} — {l.label}
                  </option>
                ))}
              </select>
            </Champ>

            <Champ libelle="Projet imputé">
              <select {...register("project", { required: true })} className={saisie}>
                <option value="">— Choisir —</option>
                {(projets.data?.results ?? []).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.code}
                  </option>
                ))}
              </select>
            </Champ>

            <Champ libelle="Libellé">
              <input
                {...register("label", { required: true })}
                placeholder="Carburant mission Kara, mars"
                className={saisie}
              />
            </Champ>

            <Champ libelle="Montant">
              <input
                type="number"
                step="0.01"
                min={0}
                {...register("amount", { required: true })}
                className={saisie}
              />
            </Champ>

            <Champ libelle="Devise">
              <select {...register("currency", { required: true })} className={saisie}>
                <option value="">— Choisir —</option>
                {(devises.data ?? []).map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.code}
                  </option>
                ))}
              </select>
            </Champ>

            <Champ libelle="Date de la dépense">
              <input
                type="date"
                {...register("expense_date", { required: true })}
                className={saisie}
              />
            </Champ>
          </div>

          <div className="mt-4 flex gap-3">
            <button
              type="submit"
              disabled={enregistrer.isPending || !formState.isValid}
              className="rounded-lg bg-primary px-5 py-2.5 text-body font-semibold text-on-primary transition hover:bg-primary-strong disabled:opacity-50"
            >
              Enregistrer
            </button>
            <button
              type="button"
              onClick={() => setSaisieOuverte(false)}
              className="rounded-lg border border-border px-5 py-2.5 text-body text-ink transition hover:bg-surface-low"
            >
              Annuler
            </button>
          </div>
        </form>
      )}

      {erreur && (
        <p role="alert" className="rounded-lg bg-danger-soft px-4 py-3 text-body text-danger">
          {erreur}
        </p>
      )}

      {alerte && (
        <div className="flex items-start gap-2.5 rounded-lg border border-danger/25 bg-danger-soft px-4 py-3">
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-danger" />
          <p className="text-body text-danger">{alerte}</p>
          <button
            onClick={() => setAlerte(null)}
            aria-label="Masquer l'alerte"
            className="ml-auto text-danger"
          >
            <X className="h-4 w-4" />
          </button>
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
        ) : depenses.length === 0 ? (
          <p className="p-8 text-center text-body text-ink-muted">
            Aucune dépense dans cette catégorie.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-body">
              <thead>
                <tr className="border-b border-border text-left text-overline uppercase tracking-wide text-ink-muted">
                  <th className="px-4 py-3 font-semibold">Date</th>
                  <th className="px-4 py-3 font-semibold">Libellé</th>
                  <th className="px-4 py-3 font-semibold">Imputation</th>
                  <th className="px-4 py-3 text-right font-semibold">Montant</th>
                  <th className="px-4 py-3 font-semibold">Statut</th>
                  {peut("depense.valider") && (
                    <th className="px-4 py-3 font-semibold">Décision</th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {depenses.map((depense) => {
                  const badge = STATUT[depense.status];
                  return (
                    <tr key={depense.id} className="transition hover:bg-surface-low">
                      <td className="whitespace-nowrap px-4 py-3 text-ink-muted">
                        {depense.expense_date}
                      </td>
                      <td className="px-4 py-3">
                        <p className="text-ink">{depense.label}</p>
                        <p className="text-caption text-ink-muted">
                          Saisie par {depense.entered_by_name}
                        </p>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3">
                        <p className="font-mono text-caption text-ink">
                          {depense.budget_line_code}
                        </p>
                        <p className="font-mono text-caption text-ink-muted">
                          {depense.project_code}
                        </p>
                      </td>
                      <td className="whitespace-nowrap px-4 py-3 text-right text-ink">
                        {argent(depense.amount, depense.currency_code)}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`whitespace-nowrap rounded-full px-2.5 py-0.5 text-caption ${
                            badge?.style ?? "bg-surface-low text-ink-muted"
                          }`}
                        >
                          {badge?.libelle ?? depense.status_label}
                        </span>
                      </td>
                      {peut("depense.valider") && (
                        <td className="px-4 py-3">
                          {depense.status === "saisie" ? (
                            <div className="flex gap-1.5">
                              <button
                                disabled={statuer.isPending}
                                onClick={() =>
                                  statuer.mutate({ id: depense.id, action: "valider" })
                                }
                                aria-label="Valider la dépense"
                                className="rounded-lg bg-primary p-1.5 text-on-primary transition hover:bg-primary-strong disabled:opacity-50"
                              >
                                <Check className="h-3.5 w-3.5" />
                              </button>
                              <button
                                disabled={statuer.isPending}
                                onClick={() =>
                                  statuer.mutate({ id: depense.id, action: "rejeter" })
                                }
                                aria-label="Rejeter la dépense"
                                className="rounded-lg border border-danger/40 p-1.5 text-danger transition hover:bg-danger-soft disabled:opacity-50"
                              >
                                <X className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          ) : (
                            <span className="text-caption text-ink-muted">—</span>
                          )}
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

const saisie =
  "w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-body text-ink outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15";

function Champ({ libelle, children }: { libelle: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="text-caption text-ink-muted">{libelle}</label>
      <div className="mt-1">{children}</div>
    </div>
  );
}