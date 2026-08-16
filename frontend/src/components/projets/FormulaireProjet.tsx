"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { api, ErreurApi } from "@/lib/api";
import type { ProjetDetail } from "@/lib/types";

interface Secteur {
  id: number;
  code: string;
  label: string;
}

interface Champs {
  code: string;
  title: string;
  description: string;
  start_date: string;
  end_date: string;
  target_beneficiaries: number;
}

export default function FormulaireProjet({ projet }: { projet?: ProjetDetail }) {
  const router = useRouter();
  const modification = projet !== undefined;

  const [secteurs, setSecteurs] = useState<number[]>(projet?.sectors ?? []);
  const [erreur, setErreur] = useState<string | null>(null);
  const [erreursChamp, setErreursChamp] = useState<Record<string, string[]>>({});

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<Champs>({
    defaultValues: {
      code: projet?.code ?? "",
      title: projet?.title ?? "",
      description: projet?.description ?? "",
      start_date: projet?.start_date ?? "",
      end_date: projet?.end_date ?? "",
      target_beneficiaries: projet?.target_beneficiaries ?? 0,
    },
  });

  const referentiel = useQuery({
    queryKey: ["secteurs"],
    queryFn: () => api<Secteur[]>("/secteurs/"),
  });

  const enregistrer = useMutation({
    mutationFn: (valeurs: Champs) =>
      api<ProjetDetail>(modification ? `/projets/${projet!.id}/` : "/projets/", {
        methode: modification ? "PATCH" : "POST",
        corps: {
          code: valeurs.code,
          title: valeurs.title,
          description: valeurs.description,
          start_date: valeurs.start_date,
          end_date: valeurs.end_date,
          target_beneficiaries: Number(valeurs.target_beneficiaries),
          sectors: secteurs,
        },
      }),
    onSuccess: (enregistre) => router.push(`/projets/${enregistre.id}`),
    onError: (e) => {
      if (e instanceof ErreurApi) {
        setErreur(e.message);
        setErreursChamp(e.parChamp);
      } else {
        setErreur("L'enregistrement a échoué.");
      }
    },
  });

  return (
    <form
      onSubmit={handleSubmit((v) => enregistrer.mutate(v))}
      className="mx-auto max-w-3xl space-y-5"
    >
      <header>
        <h1 className="text-title">
          {modification ? "Modifier le projet" : "Nouveau projet"}
        </h1>
        <p className="mt-1 text-body text-ink-muted">
          {modification
            ? "Le statut ne se modifie pas ici : il évolue par le cycle de vie, depuis la fiche du projet."
            : "Le projet est créé en brouillon. Il faudra le soumettre pour instruction depuis sa fiche."}
        </p>
      </header>

      <section className="rounded-card bg-surface p-6 shadow-sm">
        <div className="grid gap-4 sm:grid-cols-2">
          <Champ
            libelle="Code projet"
            erreur={errors.code?.message ?? erreursChamp.code?.[0]}
          >
            <input
              {...register("code", {
                required: "Le code est obligatoire.",
                pattern: {
                  value: /^[-\w]+$/,
                  message: "Lettres, chiffres et tirets uniquement.",
                },
              })}
              placeholder="PRJ-2026-013"
              className={saisie}
            />
          </Champ>

          <Champ
            libelle="Bénéficiaires visés"
            erreur={erreursChamp.target_beneficiaries?.[0]}
          >
            <input
              type="number"
              min={0}
              {...register("target_beneficiaries")}
              className={saisie}
            />
          </Champ>
        </div>

        <div className="mt-4">
          <Champ
            libelle="Intitulé"
            erreur={errors.title?.message ?? erreursChamp.title?.[0]}
          >
            <input
              {...register("title", { required: "L'intitulé est obligatoire." })}
              placeholder="Renforcement de la sécurité alimentaire dans la Kara"
              className={saisie}
            />
          </Champ>
        </div>

        <div className="mt-4">
          <Champ libelle="Description">
            <textarea
              rows={4}
              {...register("description")}
              placeholder="Contexte, population ciblée, approche retenue…"
              className={saisie}
            />
          </Champ>
        </div>

        <div className="mt-4 grid gap-4 sm:grid-cols-2">
          <Champ
            libelle="Date de début"
            erreur={errors.start_date?.message ?? erreursChamp.start_date?.[0]}
          >
            <input
              type="date"
              {...register("start_date", { required: "Date obligatoire." })}
              className={saisie}
            />
          </Champ>
          <Champ
            libelle="Date de fin prévue"
            erreur={errors.end_date?.message ?? erreursChamp.end_date?.[0]}
          >
            <input
              type="date"
              {...register("end_date", { required: "Date obligatoire." })}
              className={saisie}
            />
          </Champ>
        </div>
      </section>

      <section className="rounded-card bg-surface p-6 shadow-sm">
        <h2 className="text-heading">Secteurs d&apos;intervention</h2>
        <p className="mt-0.5 text-caption text-ink-muted">
          Nomenclature humanitaire — un projet peut relever de plusieurs secteurs.
        </p>
        {referentiel.isLoading ? (
          <LoaderCircle className="mt-3 h-4 w-4 animate-spin text-ink-muted" />
        ) : (
          <div className="mt-4 grid gap-2 sm:grid-cols-2">
            {(referentiel.data ?? []).map((secteur) => (
              <label key={secteur.id} className="flex items-center gap-2 text-body text-ink">
                <input
                  type="checkbox"
                  checked={secteurs.includes(secteur.id)}
                  onChange={(e) =>
                    setSecteurs((precedent) =>
                      e.target.checked
                        ? [...precedent, secteur.id]
                        : precedent.filter((s) => s !== secteur.id),
                    )
                  }
                  className="accent-[var(--color-primary)]"
                />
                {secteur.label}
              </label>
            ))}
          </div>
        )}
        {erreursChamp.sectors && (
          <p className="mt-2 text-caption text-danger">{erreursChamp.sectors[0]}</p>
        )}
      </section>

      {erreur && (
        <p role="alert" className="rounded-lg bg-danger-soft px-4 py-3 text-body text-danger">
          {erreur}
        </p>
      )}

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={enregistrer.isPending || secteurs.length === 0}
          className="flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-3 text-body font-semibold text-on-primary transition hover:bg-primary-strong disabled:cursor-not-allowed disabled:opacity-50"
        >
          {enregistrer.isPending && <LoaderCircle className="h-4 w-4 animate-spin" />}
          {modification ? "Enregistrer les modifications" : "Créer le projet"}
        </button>
        <Link
          href={modification ? `/projets/${projet!.id}` : "/projets"}
          className="rounded-lg border border-border px-5 py-3 text-body text-ink transition hover:bg-surface-low"
        >
          Annuler
        </Link>
      </div>
    </form>
  );
}

const saisie =
  "w-full rounded-lg border border-border bg-surface px-3 py-2.5 text-body text-ink outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15";

function Champ({
  libelle,
  erreur,
  children,
}: {
  libelle: string;
  erreur?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="text-caption text-ink-muted">{libelle}</label>
      <div className="mt-1">{children}</div>
      {erreur && <p className="mt-1 text-caption text-danger">{erreur}</p>}
    </div>
  );
}