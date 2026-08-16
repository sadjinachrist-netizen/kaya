"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  CalendarDays,
  Leaf,
  LoaderCircle,
  MapPin,
  ShieldCheck,
} from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface Organisation {
  nom: string;
  sigle: string;
  adresse: string;
  telephone: string;
  email: string;
  mentions_legales: string;
}

interface Chiffres {
  projets_en_cours: number;
  projets_total: number;
  personnes_accompagnees: number;
  menages: number;
  localites: number;
  regions: number;
  bailleurs: number;
  activites_realisees: number;
}

interface ProjetPublic {
  id: number;
  code: string;
  titre: string;
  description: string;
  secteurs: string[];
  regions: string[];
  debut: string;
  fin: string;
  statut: string;
  en_cours: boolean;
  beneficiaires_vises: number;
}

interface SecteurPublic {
  code: string;
  label: string;
  nb_projets: number;
}

const publique = { publique: true } as const;
const annee = (iso: string) => new Date(iso).getFullYear();
const nombre = (n: number) => n.toLocaleString("fr-FR");

export default function Portail() {
  const { utilisateur } = useAuth();

  const organisation = useQuery({
    queryKey: ["portail-organisation"],
    queryFn: () => api<Organisation>("/portail/organisation/", publique),
  });
  const chiffres = useQuery({
    queryKey: ["portail-chiffres"],
    queryFn: () => api<Chiffres>("/portail/chiffres/", publique),
  });
  const projets = useQuery({
    queryKey: ["portail-projets"],
    queryFn: () => api<ProjetPublic[]>("/portail/projets/", publique),
  });
  const secteurs = useQuery({
    queryKey: ["portail-secteurs"],
    queryFn: () => api<SecteurPublic[]>("/portail/secteurs/", publique),
  });

  const ong = organisation.data;
  const c = chiffres.data;

  return (
    <div className="min-h-screen bg-background">
      {/* ------------------------------- en-tete ------------------------------- */}
      <header className="sticky top-0 z-40 border-b border-border bg-surface/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary">
              <Leaf className="h-5 w-5 text-on-primary" strokeWidth={2.2} />
            </div>
            <div className="leading-tight">
              <p className="text-body font-semibold uppercase tracking-wide text-ink">
                {ong?.sigle || "SDT"}
              </p>
              <p className="text-caption text-ink-muted">{ong?.nom}</p>
            </div>
          </div>

          <nav className="hidden items-center gap-6 md:flex">
            <a href="#zones" className="text-body text-ink-muted transition hover:text-ink">
              Zones d&apos;intervention
            </a>
            <a href="#projets" className="text-body text-ink-muted transition hover:text-ink">
              Nos projets
            </a>
            <a href="#transparence" className="text-body text-ink-muted transition hover:text-ink">
              Transparence
            </a>
            <a href="#contact" className="text-body text-ink-muted transition hover:text-ink">
              Contact
            </a>
          </nav>

          <Link
            href={utilisateur ? "/tableau-de-bord" : "/connexion"}
            className="shrink-0 rounded-lg bg-primary px-4 py-2 text-body font-semibold text-on-primary transition hover:bg-primary-strong"
          >
            {utilisateur ? "Ouvrir la plateforme" : "Espace membre"}
          </Link>
        </div>
      </header>

      {/* -------------------------------- bandeau -------------------------------- */}
      <section className="relative">
        <div className="absolute inset-0">
          <Image
            src="/portail-hero.png"
            alt=""
            fill
            priority
            className="object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-r from-background via-background/85 to-background/30" />
        </div>

        <div className="relative mx-auto grid max-w-6xl gap-8 px-6 py-20 lg:grid-cols-[1.1fr_360px] lg:items-center">
          <div>
            <h1 className="max-w-xl text-display leading-tight text-ink">
              Agir pour un développement durable et solidaire au Togo.
            </h1>
            <p className="mt-4 max-w-lg text-body-lg text-ink-muted">
              Notre organisation intervient aux côtés des communautés locales dans
              l&apos;eau et l&apos;assainissement, la santé, la nutrition, la sécurité
              alimentaire et l&apos;éducation.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <a
                href="#projets"
                className="flex items-center gap-2 rounded-lg bg-primary px-5 py-3 text-body font-semibold text-on-primary transition hover:bg-primary-strong"
              >
                Découvrir nos actions
                <ArrowRight className="h-4 w-4" />
              </a>
              <a
                href="#transparence"
                className="rounded-lg border border-border bg-surface px-5 py-3 text-body font-semibold text-ink transition hover:bg-surface-low"
              >
                Notre redevabilité
              </a>
            </div>
          </div>

          {/* carte de chiffres */}
          <div className="rounded-card bg-surface p-7 shadow-lg">
            {chiffres.isLoading || !c ? (
              <div className="flex h-40 items-center justify-center">
                <LoaderCircle className="h-5 w-5 animate-spin text-ink-muted" />
              </div>
            ) : (
              <dl className="divide-y divide-border">
                <Chiffre valeur={nombre(c.projets_en_cours)} libelle="Projets en cours d'exécution" />
                <Chiffre
                  valeur={`${nombre(c.personnes_accompagnees)}+`}
                  libelle="Personnes accompagnées"
                />
                <Chiffre valeur={nombre(c.regions)} libelle="Régions d'intervention couvertes" />
              </dl>
            )}
          </div>
        </div>
      </section>

      {/* --------------------------- zones d'intervention --------------------------- */}
      <section id="zones" className="border-t border-border bg-surface-low/40">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <h2 className="text-title text-info">Nos zones d&apos;intervention</h2>
          <p className="mt-1 text-body text-ink-muted">
            Déploiement de nos équipes sur le territoire national.
          </p>

          <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_1.2fr]">
            <div className="rounded-card bg-surface p-8 shadow-sm">
              {c && (
                <div className="grid grid-cols-2 gap-6">
                  <Bloc valeur={nombre(c.regions)} libelle="régions" />
                  <Bloc valeur={nombre(c.localites)} libelle="localités couvertes" />
                  <Bloc valeur={nombre(c.menages)} libelle="ménages accompagnés" />
                  <Bloc valeur={nombre(c.activites_realisees)} libelle="activités réalisées" />
                </div>
              )}
              <p className="mt-8 border-t border-border pt-5 text-caption text-ink-muted">
                Les effectifs publiés sont arrondis à la baisse. Aucune donnée
                permettant d&apos;identifier une personne n&apos;est diffusée.
              </p>
            </div>

            <div className="space-y-3">
              {(secteurs.data ?? []).map((secteur) => (
                <article
                  key={secteur.code}
                  className="flex items-start gap-4 rounded-card bg-surface p-5 shadow-sm"
                >
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary-soft">
                    <Leaf className="h-4 w-4 text-primary" />
                  </div>
                  <div>
                    <h3 className="text-body font-semibold text-info">{secteur.label}</h3>
                    <p className="mt-0.5 text-caption text-ink-muted">
                      {secteur.nb_projets} projet{secteur.nb_projets > 1 ? "s" : ""} en
                      portefeuille.
                    </p>
                  </div>
                </article>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* -------------------------------- projets -------------------------------- */}
      <section id="projets">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <h2 className="text-title text-info">Nos projets</h2>
          <p className="mt-1 text-body text-ink-muted">
            Aperçu de nos interventions récentes et en cours.
          </p>

          {projets.isLoading ? (
            <div className="flex h-48 items-center justify-center">
              <LoaderCircle className="h-5 w-5 animate-spin text-ink-muted" />
            </div>
          ) : (
            <div className="mt-8 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
              {(projets.data ?? []).map((projet) => (
                <article
                  key={projet.id}
                  className="flex flex-col overflow-hidden rounded-card bg-surface shadow-sm"
                >
                  <div className="relative flex h-28 items-end bg-gradient-to-br from-primary to-primary-strong p-4">
                    <span
                      className={`absolute right-3 top-3 rounded-full px-2.5 py-0.5 text-caption ${
                        projet.en_cours
                          ? "bg-on-primary text-primary"
                          : "bg-on-primary/25 text-on-primary"
                      }`}
                    >
                      {projet.statut}
                    </span>
                    <p className="font-mono text-caption text-on-primary/80">
                      {projet.code}
                    </p>
                  </div>

                  <div className="flex flex-1 flex-col p-5">
                    <h3 className="text-heading leading-snug text-ink">{projet.titre}</h3>
                    {projet.description && (
                      <p className="mt-2 line-clamp-3 text-body text-ink-muted">
                        {projet.description}
                      </p>
                    )}

                    <dl className="mt-auto space-y-1.5 pt-4 text-caption text-ink-muted">
                      {projet.secteurs.length > 0 && (
                        <div className="flex items-start gap-1.5">
                          <Leaf className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                          {projet.secteurs.join(", ")}
                        </div>
                      )}
                      {projet.regions.length > 0 && (
                        <div className="flex items-start gap-1.5">
                          <MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                          {projet.regions.join(", ")}
                        </div>
                      )}
                      <div className="flex items-center gap-1.5">
                        <CalendarDays className="h-3.5 w-3.5 shrink-0" />
                        {annee(projet.debut)} – {annee(projet.fin)}
                      </div>
                    </dl>
                  </div>
                </article>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ------------------------------ transparence ------------------------------ */}
      <section id="transparence" className="border-t border-border bg-surface-low/40">
        <div className="mx-auto max-w-6xl px-6 py-16">
          <div className="flex items-start gap-4">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary-soft">
              <ShieldCheck className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2 className="text-title text-info">Transparence et redevabilité</h2>
              <p className="mt-1 max-w-2xl text-body text-ink-muted">
                Notre activité est intégralement financée par des bailleurs
                institutionnels et privés, envers lesquels nous sommes tenus de
                justifier l&apos;emploi de chaque financement.
              </p>
            </div>
          </div>

          {c && (
            <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <Carte valeur={nombre(c.bailleurs)} libelle="Bailleurs partenaires" />
              <Carte valeur={nombre(c.projets_total)} libelle="Projets publiés" />
              <Carte valeur={nombre(c.activites_realisees)} libelle="Activités validées sur le terrain" />
              <Carte valeur={nombre(c.menages)} libelle="Ménages enregistrés" />
            </div>
          )}

          <div className="mt-8 grid gap-4 md:grid-cols-3">
            <Engagement
              titre="Consentement systématique"
              texte="Aucun ménage n'est enregistré sans son accord explicite au traitement de ses données, recueilli et daté."
            />
            <Engagement
              titre="Données personnelles protégées"
              texte="Les identités ne sont accessibles qu'aux personnes habilitées. Elles ne figurent ni sur ce portail, ni dans les exports transmis aux bailleurs."
            />
            <Engagement
              titre="Traçabilité intégrale"
              texte="Chaque création, modification et consultation sensible est journalisée dans un registre que personne ne peut modifier."
            />
          </div>
        </div>
      </section>

      {/* ---------------------------------- pied ---------------------------------- */}
      <footer id="contact" className="border-t border-border bg-surface">
        <div className="mx-auto grid max-w-6xl gap-8 px-6 py-12 md:grid-cols-3">
          <div>
            <h3 className="text-heading text-ink">{ong?.nom}</h3>
            <p className="mt-2 max-w-sm text-body text-ink-muted">
              Organisation non gouvernementale dédiée au renforcement des capacités
              locales et au développement durable des communautés rurales au Togo.
            </p>
          </div>

          <div>
            <h4 className="text-caption uppercase tracking-wide text-ink-muted">Contact</h4>
            <address className="mt-2 space-y-1 text-body not-italic text-ink">
              {ong?.adresse && <p>{ong.adresse}</p>}
              {ong?.email && <p>{ong.email}</p>}
              {ong?.telephone && <p>{ong.telephone}</p>}
            </address>
          </div>

          <div>
            <h4 className="text-caption uppercase tracking-wide text-ink-muted">Plateforme</h4>
            <p className="mt-2 text-body text-ink-muted">
              Les équipes de terrain, la coordination et les bailleurs accèdent à leur
              espace dédié.
            </p>
            <Link
              href="/connexion"
              className="mt-3 inline-flex items-center gap-1.5 text-body font-semibold text-primary underline-offset-4 hover:underline"
            >
              Se connecter
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>

        <div className="border-t border-border">
          <div className="mx-auto max-w-6xl px-6 py-5 text-caption text-ink-muted">
            <p>
              {ong?.nom} — organisation fictive servant de cadre à la plateforme Kaya.
              Les données présentées sont des données de démonstration.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

/* --------------------------------- fragments --------------------------------- */

function Chiffre({ valeur, libelle }: { valeur: string; libelle: string }) {
  return (
    <div className="py-4 first:pt-0 last:pb-0">
      <dt className="text-display leading-none text-ink">{valeur}</dt>
      <dd className="mt-1.5 text-caption uppercase tracking-wide text-ink-muted">
        {libelle}
      </dd>
    </div>
  );
}

function Bloc({ valeur, libelle }: { valeur: string; libelle: string }) {
  return (
    <div>
      <p className="text-title leading-none text-primary">{valeur}</p>
      <p className="mt-1 text-caption text-ink-muted">{libelle}</p>
    </div>
  );
}

function Carte({ valeur, libelle }: { valeur: string; libelle: string }) {
  return (
    <div className="rounded-card bg-surface p-5 shadow-sm">
      <p className="text-title leading-none text-ink">{valeur}</p>
      <p className="mt-1.5 text-caption text-ink-muted">{libelle}</p>
    </div>
  );
}

function Engagement({ titre, texte }: { titre: string; texte: string }) {
  return (
    <article className="rounded-card bg-surface p-5 shadow-sm">
      <h3 className="text-body font-semibold text-ink">{titre}</h3>
      <p className="mt-1.5 text-body text-ink-muted">{texte}</p>
    </article>
  );
}