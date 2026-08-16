"use client";

import { useMutation } from "@tanstack/react-query";
import {
  Activity,
  Download,
  Globe2,
  LoaderCircle,
  ShieldCheck,
  Target,
  Users,
} from "lucide-react";
import { useState } from "react";

import { ErreurApi, telecharger } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface Export {
  cle: string;
  chemin: string;
  fichier: string;
  titre: string;
  description: string;
  icone: typeof Users;
  permission: string;
  contenu: string[];
}

const EXPORTS: Export[] = [
  {
    cle: "beneficiaires",
    chemin: "/exports/beneficiaires/",
    fichier: "kaya_beneficiaires.xlsx",
    titre: "Bénéficiaires",
    description:
      "Ménages et individus de votre périmètre, avec leur ventilation par sexe et par tranche d'âge.",
    icone: Users,
    permission: "beneficiaire.exporter",
    contenu: ["Feuille Ménages", "Feuille Individus", "Feuille Mentions"],
  },
  {
    cle: "activites",
    chemin: "/exports/activites/",
    fichier: "kaya_activites.xlsx",
    titre: "Activités terrain",
    description:
      "Toutes les activités, leur localisation administrative, leurs participants et leurs alertes qualité.",
    icone: Activity,
    permission: "export.realiser",
    contenu: ["Statut de validation", "Participants désagrégés", "Alertes qualité"],
  },
  {
    cle: "4w",
    chemin: "/exports/4w/",
    fichier: "kaya_4w.xlsx",
    titre: "Format 4W",
    description:
      "Who does What, Where, When — le format standard attendu par les clusters humanitaires. Activités validées uniquement.",
    icone: Globe2,
    permission: "export.realiser",
    contenu: ["Organisation et secteur", "Région, préfecture, localité", "Période et effectifs"],
  },
  {
    cle: "indicateurs",
    chemin: "/exports/indicateurs/",
    fichier: "kaya_indicateurs.xlsx",
    titre: "Indicateurs",
    description:
      "Cadre logique, cibles, taux d'atteinte comparés à l'attendu, et historique complet des relevés.",
    icone: Target,
    permission: "export.realiser",
    contenu: ["Feuille Indicateurs", "Feuille Relevés"],
  },
];

export default function PageExports() {
  const { peut } = useAuth();
  const nominatif = peut("beneficiaire.voir_donnees_nominatives");
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState<string | null>(null);

  const lancer = useMutation({
    mutationFn: async (element: Export) => {
      setEnCours(element.cle);
      await telecharger(element.chemin, element.fichier);
    },
    onSuccess: () => {
      setErreur(null);
      setEnCours(null);
    },
    onError: (e) => {
      setErreur(
        e instanceof ErreurApi ? e.message : "L'export n'a pas pu être généré.",
      );
      setEnCours(null);
    },
  });

  const disponibles = EXPORTS.filter((e) => peut(e.permission));

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-title">Exports</h1>
        <p className="mt-1 text-body text-ink-muted">
          Extractions au format Excel, limitées à votre périmètre de projets.
        </p>
      </header>

      <div
        className={`flex items-start gap-2.5 rounded-card border px-4 py-3 ${
          nominatif
            ? "border-warning/25 bg-warning-soft"
            : "border-info/20 bg-info-soft"
        }`}
      >
        <ShieldCheck
          className={`mt-0.5 h-4 w-4 shrink-0 ${nominatif ? "text-warning" : "text-info"}`}
        />
        <p className={`text-body ${nominatif ? "text-warning" : "text-info"}`}>
          {nominatif ? (
            <>
              Vos exports contiennent des <strong>données nominatives</strong>. Chaque
              téléchargement est journalisé — auteur, date, volume — et le journal ne
              peut être ni modifié ni purgé.
            </>
          ) : (
            <>
              Les identités sont remplacées par les codes d&apos;enregistrement dans vos
              exports, comme à l&apos;écran. La règle s&apos;applique au fichier produit,
              pas seulement à l&apos;affichage.
            </>
          )}
        </p>
      </div>

      {erreur && (
        <p role="alert" className="rounded-lg bg-danger-soft px-4 py-3 text-body text-danger">
          {erreur}
        </p>
      )}

      {disponibles.length === 0 ? (
        <p className="rounded-card bg-surface p-8 text-center text-body text-ink-muted shadow-sm">
          Aucun export n&apos;est ouvert à votre rôle.
        </p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {disponibles.map((element) => {
            const Icone = element.icone;
            const actif = enCours === element.cle;
            return (
              <article
                key={element.cle}
                className="flex flex-col rounded-card bg-surface p-6 shadow-sm"
              >
                <div className="flex items-start gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary-soft">
                    <Icone className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h2 className="text-heading">{element.titre}</h2>
                    <p className="mt-1 text-body text-ink-muted">{element.description}</p>
                  </div>
                </div>

                <ul className="mt-4 flex flex-wrap gap-1.5">
                  {element.contenu.map((ligne) => (
                    <li
                      key={ligne}
                      className="rounded bg-surface-low px-2 py-0.5 text-caption text-ink-muted"
                    >
                      {ligne}
                    </li>
                  ))}
                </ul>

                <button
                  onClick={() => lancer.mutate(element)}
                  disabled={enCours !== null}
                  className="mt-5 flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-body font-semibold text-on-primary transition hover:bg-primary-strong disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {actif ? (
                    <LoaderCircle className="h-4 w-4 animate-spin" />
                  ) : (
                    <Download className="h-4 w-4" />
                  )}
                  {actif ? "Génération…" : "Télécharger le fichier Excel"}
                </button>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}