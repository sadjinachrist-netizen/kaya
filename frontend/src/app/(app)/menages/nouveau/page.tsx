"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  ArrowLeft,
  Check,
  Crosshair,
  LoaderCircle,
  Plus,
  Trash2,
  TriangleAlert,
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useFieldArray, useForm } from "react-hook-form";

import { api, ErreurApi } from "@/lib/api";
import type { PageResultats, ProjetListe } from "@/lib/types";

interface Vulnerabilite {
  id: number;
  code: string;
  label: string;
  weight: number;
}

interface ZoneOption {
  id: number;
  name: string;
  full_path: string;
  level_label: string;
}

interface Membre {
  first_name: string;
  last_name: string;
  sex: "M" | "F";
  birth_date: string;
  estimated_age: string;
  relation_to_head: string;
  is_head: boolean;
  is_enrolled: boolean;
  has_disability: boolean;
}

interface Formulaire {
  head_name: string;
  size: number;
  residence_status: string;
  latitude: string;
  longitude: string;
  gps_accuracy: string;
  project: string;
  consent_granted: boolean;
  consent_mode: string;
  members: Membre[];
}

const MEMBRE_VIDE: Membre = {
  first_name: "",
  last_name: "",
  sex: "F",
  birth_date: "",
  estimated_age: "",
  relation_to_head: "",
  is_head: false,
  is_enrolled: false,
  has_disability: false,
};

export default function PageNouveauMenage() {
  const [zone, setZone] = useState<ZoneOption | null>(null);
  const [rechercheZone, setRechercheZone] = useState("");
  const [requeteZone, setRequeteZone] = useState("");
  const [vulnerabilites, setVulnerabilites] = useState<number[]>([]);
  const [resultat, setResultat] = useState<{
    code: string;
    doublons: { menage: string; score: string }[];
  } | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    setValue,
    watch,
    formState: { errors },
  } = useForm<Formulaire>({
    defaultValues: {
      head_name: "",
      size: 1,
      residence_status: "resident",
      latitude: "",
      longitude: "",
      gps_accuracy: "",
      project: "",
      consent_granted: false,
      consent_mode: "oral",
      members: [{ ...MEMBRE_VIDE, is_head: true }],
    },
  });

  const { fields, append, remove } = useFieldArray({ control, name: "members" });
  const membres = watch("members");

  useEffect(() => {
    const minuteur = setTimeout(() => setRequeteZone(rechercheZone), 300);
    return () => clearTimeout(minuteur);
  }, [rechercheZone]);

  const zones = useQuery({
    queryKey: ["zones", requeteZone],
    queryFn: () => api<ZoneOption[]>("/zones/", { parametres: { search: requeteZone } }),
    enabled: requeteZone.length >= 2,
  });

  const criteres = useQuery({
    queryKey: ["vulnerabilites"],
    queryFn: () => api<Vulnerabilite[]>("/vulnerabilites/"),
  });

  const projets = useQuery({
    queryKey: ["projets", ""],
    queryFn: () => api<PageResultats<ProjetListe>>("/projets/"),
  });

  const enregistrer = useMutation({
    mutationFn: (valeurs: Formulaire) =>
      api<{ code: string; doublons_detectes: { menage: string; score: string }[] }>(
        "/menages/",
        {
          methode: "POST",
          corps: {
            head_name: valeurs.head_name,
            size: Number(valeurs.size),
            zone: zone?.id,
            residence_status: valeurs.residence_status,
            latitude: valeurs.latitude || null,
            longitude: valeurs.longitude || null,
            gps_accuracy: valeurs.gps_accuracy ? Number(valeurs.gps_accuracy) : null,
            vulnerabilities: vulnerabilites,
            ...(valeurs.project ? { project: Number(valeurs.project) } : {}),
            // identifiant genere par le client : c'est lui qui rend la
            // synchronisation idempotente si la saisie a lieu hors connexion
            client_uuid: crypto.randomUUID(),
            members: valeurs.members.map((m) => ({
              first_name: m.first_name,
              last_name: m.last_name,
              sex: m.sex,
              birth_date: m.birth_date || null,
              estimated_age: m.estimated_age ? Number(m.estimated_age) : null,
              relation_to_head: m.relation_to_head,
              is_head: m.is_head,
              is_enrolled: m.is_enrolled,
              has_disability: m.has_disability,
            })),
            consent: { granted: true, collection_mode: valeurs.consent_mode },
          },
        },
      ),
    onSuccess: (reponse) => {
      setResultat({ code: reponse.code, doublons: reponse.doublons_detectes ?? [] });
      setErreur(null);
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    onError: (e) =>
      setErreur(
        e instanceof ErreurApi ? e.message : "L'enregistrement a échoué.",
      ),
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

  const definirChef = (indice: number) =>
    membres.forEach((_, i) => setValue(`members.${i}.is_head`, i === indice));

  const nbChefs = membres.filter((m) => m.is_head).length;

  // ---------------------------------------------------------------- succes
  if (resultat) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <div className="rounded-card bg-surface p-8 text-center shadow-sm">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-success-soft">
            <Check className="h-6 w-6 text-success" />
          </div>
          <h1 className="mt-4 text-title">Ménage enregistré</h1>
          <p className="mt-1 text-body text-ink-muted">
            Identifiant attribué :{" "}
            <span className="font-mono text-ink">{resultat.code}</span>
          </p>
        </div>

        {resultat.doublons.length > 0 && (
          <div className="rounded-card border border-warning/25 bg-warning-soft p-5">
            <p className="flex items-center gap-2 text-body font-semibold text-warning">
              <TriangleAlert className="h-4 w-4" />
              {resultat.doublons.length} doublon
              {resultat.doublons.length > 1 ? "s" : ""} potentiel
              {resultat.doublons.length > 1 ? "s" : ""} détecté
              {resultat.doublons.length > 1 ? "s" : ""}
            </p>
            <p className="mt-1 text-caption text-warning">
              L&apos;enregistrement a été conservé. Le superviseur tranchera depuis la
              file d&apos;arbitrage.
            </p>
            <ul className="mt-3 space-y-1">
              {resultat.doublons.map((d) => (
                <li
                  key={d.menage}
                  className="flex justify-between gap-3 text-caption text-warning"
                >
                  <span className="font-mono">{d.menage}</span>
                  <span>{Math.round(Number(d.score) * 100)} % de similarité</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={() => {
              setResultat(null);
              window.location.reload();
            }}
            className="flex-1 rounded-lg bg-primary px-4 py-2.5 text-body font-semibold text-on-primary transition hover:bg-primary-strong"
          >
            Enregistrer un autre ménage
          </button>
          <Link
            href="/menages"
            className="flex-1 rounded-lg border border-border px-4 py-2.5 text-center text-body font-semibold text-ink transition hover:bg-surface-low"
          >
            Retour à la liste
          </Link>
        </div>
      </div>
    );
  }

  // --------------------------------------------------------------- saisie
  return (
    <form
      onSubmit={handleSubmit((v) => enregistrer.mutate(v))}
      className="mx-auto max-w-3xl space-y-5"
    >
      <Link
        href="/menages"
        className="inline-flex items-center gap-1.5 text-caption text-ink-muted transition hover:text-ink"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        Ménages
      </Link>

      <header>
        <h1 className="text-title">Enregistrer un ménage</h1>
        <p className="mt-1 text-body text-ink-muted">
          Le ménage est l&apos;unité d&apos;enregistrement : l&apos;assistance se
          planifie par ménage, les effectifs se comptent par individu.
        </p>
      </header>

      {/* ------------------------------ le menage ------------------------------ */}
      <Bloc titre="Le ménage">
        <div className="grid gap-4 sm:grid-cols-2">
          <Champ libelle="Chef de ménage" erreur={errors.head_name?.message}>
            <input
              {...register("head_name", {
                required: "Le nom du chef de ménage est obligatoire.",
                minLength: { value: 2, message: "Nom trop court." },
              })}
              placeholder="Nom et prénoms"
              className={saisie}
            />
          </Champ>

          <Champ libelle="Taille du ménage" erreur={errors.size?.message}>
            <input
              type="number"
              min={1}
              {...register("size", {
                required: "Indiquez la taille du ménage.",
                min: { value: 1, message: "Au moins une personne." },
              })}
              className={saisie}
            />
          </Champ>

          <Champ libelle="Statut de résidence">
            <select {...register("residence_status")} className={saisie}>
              <option value="resident">Résident</option>
              <option value="deplace">Déplacé interne</option>
              <option value="refugie">Réfugié</option>
              <option value="retourne">Retourné</option>
            </select>
          </Champ>

          <Champ libelle="Projet de rattachement">
            <select {...register("project")} className={saisie}>
              <option value="">— Aucun pour l&apos;instant —</option>
              {(projets.data?.results ?? []).map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} — {p.title}
                </option>
              ))}
            </select>
          </Champ>
        </div>

        {/* localite : recherche dans le referentiel geographique */}
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

        {/* position GPS */}
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

      {/* ------------------------------- membres ------------------------------- */}
      <Bloc
        titre="Membres du ménage"
        aide="Chaque individu alimente la désagrégation par sexe et par tranche d'âge."
      >
        {nbChefs !== 1 && (
          <p className="mb-3 text-caption text-danger">
            Désignez exactement un chef de ménage.
          </p>
        )}

        <div className="space-y-3">
          {fields.map((champ, indice) => (
            <div key={champ.id} className="rounded-lg border border-border p-4">
              <div className="flex items-center justify-between gap-3">
                <label className="flex items-center gap-2 text-caption text-ink-muted">
                  <input
                    type="radio"
                    name="chef"
                    checked={membres[indice]?.is_head ?? false}
                    onChange={() => definirChef(indice)}
                    className="accent-[var(--color-primary)]"
                  />
                  Chef de ménage
                </label>
                {fields.length > 1 && (
                  <button
                    type="button"
                    onClick={() => remove(indice)}
                    aria-label="Retirer ce membre"
                    className="text-ink-muted transition hover:text-danger"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                )}
              </div>

              <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <Champ
                  libelle="Prénom"
                  erreur={errors.members?.[indice]?.first_name?.message}
                >
                  <input
                    {...register(`members.${indice}.first_name`, {
                      required: "Prénom obligatoire.",
                    })}
                    className={saisie}
                  />
                </Champ>
                <Champ libelle="Nom">
                  <input {...register(`members.${indice}.last_name`)} className={saisie} />
                </Champ>
                <Champ libelle="Sexe">
                  <select {...register(`members.${indice}.sex`)} className={saisie}>
                    <option value="F">Féminin</option>
                    <option value="M">Masculin</option>
                  </select>
                </Champ>
                <Champ libelle="Date de naissance">
                  <input
                    type="date"
                    {...register(`members.${indice}.birth_date`)}
                    className={saisie}
                  />
                </Champ>
                <Champ libelle="ou âge estimé">
                  <input
                    type="number"
                    min={0}
                    max={120}
                    {...register(`members.${indice}.estimated_age`)}
                    className={saisie}
                  />
                </Champ>
                <Champ libelle="Lien avec le chef">
                  <input
                    {...register(`members.${indice}.relation_to_head`)}
                    placeholder="Épouse, fils, mère…"
                    className={saisie}
                  />
                </Champ>
              </div>

              <div className="mt-3 flex flex-wrap gap-4">
                <label className="flex items-center gap-2 text-caption text-ink-muted">
                  <input
                    type="checkbox"
                    {...register(`members.${indice}.is_enrolled`)}
                    className="accent-[var(--color-primary)]"
                  />
                  Scolarisé
                </label>
                <label className="flex items-center gap-2 text-caption text-ink-muted">
                  <input
                    type="checkbox"
                    {...register(`members.${indice}.has_disability`)}
                    className="accent-[var(--color-primary)]"
                  />
                  Situation de handicap
                </label>
              </div>
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={() => append({ ...MEMBRE_VIDE })}
          className="mt-3 flex items-center gap-1.5 rounded-lg border border-dashed border-border px-3 py-2 text-body text-ink-muted transition hover:border-primary hover:text-primary"
        >
          <Plus className="h-4 w-4" />
          Ajouter un membre
        </button>
      </Bloc>

      {/* ---------------------------- vulnerabilites ---------------------------- */}
      <Bloc titre="Critères de vulnérabilité" aide="Multi-sélection. Le score est calculé par le serveur.">
        {criteres.isLoading ? (
          <LoaderCircle className="h-4 w-4 animate-spin text-ink-muted" />
        ) : (
          <div className="grid gap-2 sm:grid-cols-2">
            {(criteres.data ?? []).map((critere) => (
              <label
                key={critere.id}
                className="flex items-center gap-2 text-body text-ink"
              >
                <input
                  type="checkbox"
                  checked={vulnerabilites.includes(critere.id)}
                  onChange={(e) =>
                    setVulnerabilites((precedent) =>
                      e.target.checked
                        ? [...precedent, critere.id]
                        : precedent.filter((v) => v !== critere.id),
                    )
                  }
                  className="accent-[var(--color-primary)]"
                />
                {critere.label}
              </label>
            ))}
          </div>
        )}
      </Bloc>

      {/* ----------------------------- consentement ----------------------------- */}
      <Bloc titre="Consentement">
        <label className="flex items-start gap-2.5 text-body text-ink">
          <input
            type="checkbox"
            {...register("consent_granted", {
              required: "Sans consentement, l'enregistrement est refusé.",
            })}
            className="mt-1 accent-[var(--color-primary)]"
          />
          <span>
            Le bénéficiaire a été informé de l&apos;usage de ses données et a donné son
            accord. Il peut le retirer à tout moment.
          </span>
        </label>
        {errors.consent_granted && (
          <p className="mt-1.5 text-caption text-danger">
            {errors.consent_granted.message}
          </p>
        )}

        <div className="mt-3 max-w-xs">
          <Champ libelle="Mode de recueil">
            <select {...register("consent_mode")} className={saisie}>
              <option value="oral">Oral</option>
              <option value="ecrit">Écrit</option>
              <option value="empreinte">Empreinte</option>
            </select>
          </Champ>
        </div>
      </Bloc>

      {erreur && (
        <p role="alert" className="rounded-lg bg-danger-soft px-4 py-3 text-body text-danger">
          {erreur}
        </p>
      )}

      <div className="flex gap-3">
        <button
          type="submit"
          disabled={enregistrer.isPending || !zone || nbChefs !== 1}
          className="flex items-center justify-center gap-2 rounded-lg bg-primary px-5 py-3 text-body font-semibold text-on-primary transition hover:bg-primary-strong disabled:cursor-not-allowed disabled:opacity-50"
        >
          {enregistrer.isPending && <LoaderCircle className="h-4 w-4 animate-spin" />}
          Enregistrer le ménage
        </button>
        <Link
          href="/menages"
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