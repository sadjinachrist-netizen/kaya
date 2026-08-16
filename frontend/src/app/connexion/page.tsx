"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff, Leaf, LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { ErreurApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const schema = z.object({
  email: z.string().min(1, "Renseignez votre adresse email.").email("Adresse email invalide."),
  motDePasse: z.string().min(1, "Renseignez votre mot de passe."),
});

type Formulaire = z.infer<typeof schema>;

const COMPTES_DEMO = [
  { email: "agent.demo@kaya.tg", role: "Agent terrain", couleur: "bg-info" },
  { email: "superviseur.demo@kaya.tg", role: "Superviseur", couleur: "bg-warning" },
  { email: "chef.demo@kaya.tg", role: "Chef de projet", couleur: "bg-success" },
  { email: "direction.demo@kaya.tg", role: "Direction", couleur: "bg-primary" },
  { email: "bailleur.demo@kaya.tg", role: "Bailleur", couleur: "bg-danger" },
];

const MOT_DE_PASSE_DEMO = "Demo2026Kaya";

export default function PageConnexion() {
  const { connecter, utilisateur, chargement } = useAuth();
  const router = useRouter();
  const [visible, setVisible] = useState(false);
  const [erreurGlobale, setErreurGlobale] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<Formulaire>({ resolver: zodResolver(schema) });

  useEffect(() => {
    if (!chargement && utilisateur) router.replace("/tableau-de-bord");
  }, [chargement, utilisateur, router]);

  async function envoyer(valeurs: Formulaire) {
    setErreurGlobale(null);
    try {
      await connecter(valeurs.email, valeurs.motDePasse);
      router.replace("/tableau-de-bord");
    } catch (erreur) {
      setErreurGlobale(
        erreur instanceof ErreurApi ? erreur.message : "Connexion impossible.",
      );
    }
  }

  function remplir(email: string) {
    setValue("email", email);
    setValue("motDePasse", MOT_DE_PASSE_DEMO);
    setErreurGlobale(null);
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-background px-4 py-6">
      <div className="grid w-full max-w-4xl overflow-hidden rounded-card bg-surface shadow-lg md:grid-cols-2">
        {/* ---------------- panneau de presentation ---------------- */}
        <section className="hidden flex-col justify-between bg-primary p-8 text-on-primary md:flex">
          <div>
            <div className="flex h-11 w-11 items-center justify-center rounded-lg bg-on-primary/95">
              <Leaf className="h-6 w-6 text-primary" strokeWidth={2.2} />
            </div>
            <h1 className="mt-6 text-heading leading-snug">
              Plateforme de gestion et de suivi de projets humanitaires
            </h1>
            <p className="mt-3 text-body text-on-primary/70">
              Solidarité Développement Togo
            </p>
          </div>

          <dl className="mt-8 grid grid-cols-3 gap-3">
            {[
              ["8", "projets"],
              ["560", "personnes"],
              ["5", "régions"],
            ].map(([valeur, libelle]) => (
              <div key={libelle}>
                <dt className="text-heading">{valeur}</dt>
                <dd className="text-overline uppercase tracking-wide text-on-primary/60">
                  {libelle}
                </dd>
              </div>
            ))}
          </dl>
        </section>

        {/* ---------------------- formulaire ---------------------- */}
        <section className="p-7 sm:p-8">
            <h2 className="text-heading text-primary">Connexion</h2>

          <form onSubmit={handleSubmit(envoyer)} className="mt-5 space-y-4" noValidate>
            <div>
              <label htmlFor="email" className="text-body font-medium text-ink">
                Adresse email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="username"
                placeholder="prenom.nom@kaya.tg"
                {...register("email")}
                className="mt-1 w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 text-body outline-none transition focus:border-info focus:ring-2 focus:ring-info/15"
              />
              {errors.email && (
                <p className="mt-1 text-caption text-danger">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label htmlFor="motDePasse" className="text-body font-medium text-ink">
                Mot de passe
              </label>
              <div className="relative mt-1">
                <input
                  id="motDePasse"
                  type={visible ? "text" : "password"}
                  autoComplete="current-password"
                  {...register("motDePasse")}
                  className="w-full rounded-lg border border-border bg-surface px-3.5 py-2.5 pr-10 text-body outline-none transition focus:border-info focus:ring-2 focus:ring-info/15"
                />
                <button
                  type="button"
                  onClick={() => setVisible((v) => !v)}
                  aria-label={visible ? "Masquer le mot de passe" : "Afficher le mot de passe"}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-muted transition hover:text-ink"
                >
                  {visible ? <EyeOff className="h-4.5 w-4.5" /> : <Eye className="h-4.5 w-4.5" />}
                </button>
              </div>
              {errors.motDePasse && (
                <p className="mt-1 text-caption text-danger">{errors.motDePasse.message}</p>
              )}
            </div>

            {erreurGlobale && (
              <div
                role="alert"
                className="rounded-lg border border-danger/25 bg-danger-soft px-3.5 py-2.5 text-body text-danger"
              >
                {erreurGlobale}
              </div>
            )}

            <button
              type="submit"
              disabled={isSubmitting}
              className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-body font-semibold text-on-primary transition hover:bg-primary-strong disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting && <LoaderCircle className="h-4 w-4 animate-spin" />}
              {isSubmitting ? "Connexion…" : "Se connecter"}
            </button>
          </form>

          {/* ------------------ comptes de demonstration ------------------ */}
          <div className="mt-5 rounded-lg bg-surface-low p-3.5">
            <p className="text-overline uppercase tracking-wide text-ink-muted">
              Comptes de démonstration — cliquez pour remplir
            </p>
            <ul className="mt-2">
              {COMPTES_DEMO.map((compte) => (
                <li key={compte.email}>
                  <button
                    type="button"
                    onClick={() => remplir(compte.email)}
                    className="flex w-full items-center gap-2.5 rounded px-2 py-1 text-left transition hover:bg-surface"
                  >
                    <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${compte.couleur}`} />
                    <span className="font-mono text-caption text-ink">{compte.email}</span>
                    <span className="ml-auto text-caption text-ink-muted">{compte.role}</span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    </main>
  );
}