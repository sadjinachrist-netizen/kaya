"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Check,
  Crosshair,
  LoaderCircle,
  Paperclip,
  Send,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";

import { api, ErreurApi, televerser } from "@/lib/api";
import type { ActiviteDetail, PageResultats, PieceJointe, ProjetListe } from "@/lib/types";

interface ZoneOption {
  id: number;
  name: string;
  full_path: string;
  level_label: string;
}

interface Formulaire {
  project: string;
  type: string;
  activity_date: string;
  description: string;
  results: string;
  latitude: string;
  longitude: string;
  gps_accuracy: string;
}

const TYPES = [
  { code: "formation", libelle: "Formation" },
  { code: "sensibilisation", libelle: "Sensibilisation" },
  { code: "distribution", libelle: "Distribution" },
  { code: "visite", libelle: "Visite de suivi" },
  { code: "reunion", libelle: "Réunion communautaire" },
  { code: "enquete", libelle: "Enquête" },
];

const TRANCHES = [
  { cle: "0_5", libelle: "0 – 5 ans" },
  { cle: "6_17", libelle: "6 – 17 ans" },
  { cle: "18_59", libelle: "18 – 59 ans" },
  { cle: "60_plus", libelle: "60 ans et +" },
];

const PARTICIPANTS_VIDES = Object.fromEntries(
  TRANCHES.map((t) => [t.cle, { h: "", f: "" }]),
) as Record<string, { h: string; f: string }>;

export default function PageNouvelleActivite() {
  const [zone, setZone] = useState<ZoneOption | null>(null);
  const [rechercheZone, setRechercheZone] = useState("");
  const [requeteZone, setRequeteZone] = useState("");
  const [participants, setParticipants] = useState(PARTICIPANTS_VIDES);
  const [creee, setCreee] = useState<ActiviteDetail | null>(null);
  const [pieces, setPieces] = useState<PieceJointe[]>([]);
  const [erreur, setErreur] = useState<string | null>(null);

  // mesure du temps de saisie : c'est cette valeur qui alimente le controle
  // qualite "saisie anormalement rapide" cote serveur
  const debutSaisie = useRef(Date.now());

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<Formulaire>({
    defaultValues: {
      project: "",
      type: "sensibilisation",
      activity_date: new Date().toISOString().slice(0, 10),
      description: "",
      results: "",
      latitude: "",
      longitude: "",
      gps_accuracy: "",
    },
  });

  useEffect(() => {
    const minuteur = setTimeout(() => setRequeteZone(rechercheZone), 300);
    return () => clearTimeout(minuteur);
  }, [rechercheZone]);

  const zones = useQuery({
    queryKey: ["zones", requeteZone],
    queryFn: () => api<ZoneOption[]>("/zones/", { parametres: { search: requeteZone } }),
    enabled: requeteZone.length >= 2,
  });

  const projets = useQuery({
    queryKey: ["projets", ""],
    queryFn: () => api<PageResultats<ProjetListe>>("/projets/"),
  });

  const enregistrer = useMutation({
    mutationFn: (valeurs: Formulaire) => {
      const hommes = TRANCHES.reduce((t, x) => t + Number(participants[x.cle].h || 0), 0);
      const femmes = TRANCHES.reduce((t, x) => t + Number(participants[x.cle].f || 0), 0);
      const ventilation = Object.fromEntries(
        TRANCHES.map((x) => [
          x.cle,
          { hommes: Number(participants[x.cle].h || 0), femmes: Number(participants[x.cle].f || 0) },
        ]),
      );

      return api<ActiviteDetail>("/activites/", {
        methode: "POST",
        corps: {
          project: Number(valeurs.project),
          type: valeurs.type,
          activity_date: valeurs.activity_date,
          zone: zone?.id,
          description: valeurs.description,
          results: valeurs.results,
          latitude: valeurs.latitude || null,
          longitude: valeurs.longitude || null,
          gps_accuracy: valeurs.gps_accuracy ? Number(valeurs.gps_accuracy) : null,
          entry_duration_seconds: Math.round((Date.now() - debutSaisie.current) / 1000),
          client_uuid: crypto.randomUUID(),
          participations:
            hommes + femmes > 0
              ? [{ household: null, males_count: hommes, females_count: femmes, age_breakdown: ventilation }]
              : [],
        },
      });
    },
    onSuccess: (activite) => {
      setCreee(activite);
      setErreur(null);
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    onError: (e) =>
      setErreur(e instanceof ErreurApi ? e.message : "L'enregistrement a échoué."),
  });

  const joindre = useMutation({
    mutationFn: (fichier: File) => {
      const corps = new FormData();
      corps.append("file", fichier);
      corps.append("caption", fichier.name);
      return televerser<PieceJointe>(`/activites/${creee!.id}/piece-jointe/`, corps);
    },
    onSuccess: (piece) => {
      setPieces((precedent) => [...precedent, piece]);
      setErreur(null);
    },
    onError: (e) =>
      setErreur(e instanceof ErreurApi ? e.message : "Le fichier a été refusé."),
  });

  const soumettre = useMutation({
    mutationFn: () =>
      api<ActiviteDetail>(`/activites/${creee!.id}/soumettre/`, { methode: "POST" }),
    onSuccess: (activite) => setCreee(activite),
    onError: (e) =>
      setErreur(e instanceof ErreurApi ? e.message : "La soumission a échoué."),
  });

  const capturerPosition = () => {
    if (!navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setValue("latitude", position.coords.latitude.toFixed(6));
        setValue("longitude", position.coords.longitude.toFixed(6));
        setValue("gps_accuracy", Math.round(position.coords.accuracy).toString());
      },
      () => setErreur("Position indisponible — autorisez la géolocalisation."),
    );
  };

  // ------------------------------------------- etape 2 : pieces et soumission
  if (creee) {
    const soumise = creee.status === "soumise";
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <div className="rounded-card bg-surface p-8 text-center shadow-sm">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-success-soft">
            <Check className="h-6 w-6 text-success" />
          </div>
          <h1 className="mt-4 text-title">
            {soumise ? "Activité soumise" : "Activité enregistrée"}
          </h1>
          <p className="mt-1 text-body text-ink-muted">
            <span className="font-mono text-ink">{creee.code}</span> —{" "}
            {soumise
              ? "elle attend désormais la décision du superviseur."
              : "elle est en brouillon : joignez vos pièces avant de la soumettre."}
          </p>
        </div>

        {!soumise && (
          <div className="rounded-card bg-surface p-6 shadow-sm">
            <h2 className="flex items-center gap-2 text-heading">
              <Paperclip className="h-4 w-4 text-ink-muted" />
              Pièces justificatives
            </h2>
            <p className="mt-0.5 text-caption text-ink-muted">
              Photos, listes de présence scannées, documents PDF.
            </p>

            <input
              type="file"
              accept="image/*,application/pdf"
              disabled={joindre.isPending}
              onChange={(e) => {
                const fichier = e.target.files?.[0];
                if (fichier) joindre.mutate(fichier);
                e.target.value = "";
              }}
              className="mt-3 block w-full text-body text-ink-muted file:mr-3 file:rounded-lg file:border-0 file:bg-primary file:px-4 file:py-2 file:text-body file:font-semibold file:text-on-primary hover:file:bg-primary-strong"
            />

            {pieces.length > 0 && (
              <ul className="mt-3 divide-y divide-border">
                {pieces.map((piece) => (
                  <li key={piece.id} className="flex justify-between gap-3 py-2 text-body">
                    <span className="truncate text-ink">{piece.caption}</span>
                    <span className="shrink-0 text-caption text-ink-muted">
                      {Math.round(piece.size / 1024)} Ko
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {erreur && (
          <p role="alert" className="rounded-lg bg-danger-soft px-4 py-3 text-body text-danger">
            {erreur}
          </p>
        )}

        <div className="flex gap-3">
          {!soumise && (
            <button
              onClick={() => soumettre.mutate()}
              disabled={soumettre.isPending}
              className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-primary px-4 py-2.5 text-body font-semibold text-on-primary transition hover:bg-primary-strong disabled:opacity-60"
            >
              <Send className="h-4 w-4" />
              Soumettre à validation
            </button>
          )}
          <Link
            href="/activites"
            className="flex-1 rounded-lg border border-border px-4 py-2.5 text-center text-body font-semibold text-ink transition hover:bg-surface-low"
          >
            {soumise ? "Retour à la liste" : "Garder en brouillon"}
          </Link>
        </div>
      </div>
    );
  }

  // ----------------------------------------------------- etape 1 : la saisie
  return (
    <form
      onSubmit={handleSubmit((v) => enregistrer.mutate(v))}
      className="mx-auto max-w-3xl space-y-5"
    >
      <Link
        href="/activites"
        className="inline-flex items-center gap-1.5 text-caption text-ink-muted transition hover:text-ink"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Activités
      </Link>

      <header>
        <h1 className="text-title">Enregistrer une activité</h1>
        <p className="mt-1 text-body text-ink-muted">
          La date de réalisation est saisissable : une activité menée la semaine
          dernière s&apos;enregistre à sa vraie date.
        </p>
      </header>

      <Bloc titre="L'activité">
        <div className="grid gap-4 sm:grid-cols-2">
          <Champ libelle="Projet" erreur={errors.project?.message}>
            <select
              {...register("project", { required: "Sélectionnez un projet." })}
              className={saisie}
            >
              <option value="">— Choisir —</option>
              {(projets.data?.results ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} — {p.title}
                </option>
              ))}
            </select>
          </Champ>

          <Champ libelle="Type d'activité">
            <select {...register("type")} className={saisie}>
              {TYPES.map((t) => (
                <option key={t.code} value={t.code}>
                  {t.libelle}
                </option>
              ))}
            </select>
          </Champ>

          <Champ libelle="Date de réalisation" erreur={errors.activity_date?.message}>
            <input
              type="date"
              max={new Date().toISOString().slice(0, 10)}
              {...register("activity_date", { required: "Date obligatoire." })}
              className={saisie}
            />
          </Champ>
        </div>

        <div className="mt-4">
          <label className="text-caption text-ink-muted">Localité</label>
          {zone ? (
            <div className="mt-1 flex items-center justify-between gap-3 rounded-lg border border-primary/30 bg-primary-soft px-3 py-2.5">
              <div>
                <p className="text-body text-ink">{zone.name}</p>
                <p className="text-caption text-ink-muted">{zone.full_path}</p>
              </div>
              <button
                type="button"
                onClick={() => setZone(null)}
                className="text-caption text-primary underline"
              >
                Changer
              </button>
            </div>
          ) : (
            <>
              <input
                value={rechercheZone}
                onChange={(e) => setRechercheZone(e.target.value)}
                placeholder="Tapez au moins deux lettres…"
                className={`mt-1 ${saisie}`}
              />
              {zones.data && zones.data.length > 0 && (
                <ul className="mt-1 max-h-52 overflow-y-auto rounded-lg border border-border">
                  {zones.data.slice(0, 30).map((z) => (
                    <li key={z.id}>
                      <button
                        type="button"
                        onClick={() => {
                          setZone(z);
                          setRechercheZone("");
                        }}
                        className="flex w-full flex-col items-start px-3 py-2 text-left transition hover:bg-surface-low"
                      >
                        <span className="text-body text-ink">
                          {z.name}{" "}
                          <span className="text-caption text-ink-muted">
                            ({z.level_label})
                          </span>
                        </span>
                        <span className="text-caption text-ink-muted">{z.full_path}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </div>

        <div className="mt-4 space-y-4">
          <Champ libelle="Description" erreur={errors.description?.message}>
            <textarea
              rows={3}
              {...register("description", {
                required: "Décrivez le déroulé de l'activité.",
                minLength: { value: 10, message: "Description trop courte." },
              })}
              placeholder="Déroulé, thèmes abordés, intervenants…"
              className={saisie}
            />
          </Champ>
          <Champ libelle="Résultats obtenus">
            <textarea
              rows={2}
              {...register("results")}
              placeholder="Ce qui a changé, ce qui a été distribué, engagements pris…"
              className={saisie}
            />
          </Champ>
        </div>

        <div className="mt-4 flex flex-wrap items-end gap-3">
          <button
            type="button"
            onClick={capturerPosition}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-body text-ink transition hover:bg-surface-low"
          >
            <Crosshair className="h-4 w-4" />
            Capturer la position
          </button>
          <input {...register("latitude")} placeholder="Latitude" className={`w-32 ${saisie}`} />
          <input {...register("longitude")} placeholder="Longitude" className={`w-32 ${saisie}`} />
          <input
            {...register("gps_accuracy")}
            placeholder="Précision (m)"
            className={`w-32 ${saisie}`}
          />
        </div>
      </Bloc>

      <Bloc
        titre="Participants"
        aide="Ventilation par sexe et par tranche d'âge — le format attendu par l'ensemble des bailleurs."
      >
        <div className="overflow-x-auto">
          <table className="w-full text-body">
            <thead>
              <tr className="text-left text-caption uppercase tracking-wide text-ink-muted">
                <th className="pb-2 font-semibold">Tranche</th>
                <th className="pb-2 font-semibold">Hommes</th>
                <th className="pb-2 font-semibold">Femmes</th>
              </tr>
            </thead>
            <tbody>
              {TRANCHES.map((tranche) => (
                <tr key={tranche.cle}>
                  <td className="py-1.5 pr-3 text-ink-muted">{tranche.libelle}</td>
                  {(["h", "f"] as const).map((sexe) => (
                    <td key={sexe} className="py-1.5 pr-3">
                      <input
                        type="number"
                        min={0}
                        value={participants[tranche.cle][sexe]}
                        onChange={(e) =>
                          setParticipants((precedent) => ({
                            ...precedent,
                            [tranche.cle]: {
                              ...precedent[tranche.cle],
                              [sexe]: e.target.value,
                            },
                          }))
                        }
                        className={`w-24 ${saisie}`}
                      />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <button
          type="button"
          onClick={() => setParticipants(PARTICIPANTS_VIDES)}
          className="mt-3 flex items-center gap-1.5 text-caption text-ink-muted transition hover:text-danger"
        >
          <Trash2 className="h-3.5 w-3.5" />
          Réinitialiser le tableau
        </button>
      </Bloc>

      {erreur && (
        <p role="alert" className="rounded-lg bg-danger-soft px-4 py-3 text-body text-danger">
          {erreur}
        </p>
      )}

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={enregistrer.isPending || !zone}
          className="flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-3 text-body font-semibold text-on-primary transition hover:bg-primary-strong disabled:cursor-not-allowed disabled:opacity-50"
        >
          {enregistrer.isPending && <LoaderCircle className="h-4 w-4 animate-spin" />}
          Enregistrer en brouillon
        </button>
        <Link
          href="/activites"
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

function Bloc({
  titre,
  aide,
  children,
}: {
  titre: string;
  aide?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-card bg-surface p-6 shadow-sm">
      <h2 className="text-heading">{titre}</h2>
      {aide && <p className="mt-0.5 text-caption text-ink-muted">{aide}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

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