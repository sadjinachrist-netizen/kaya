"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState } from "react";

import { api, ErreurApi, jetons } from "./api";
import type { Etendue, ReponseConnexion, Utilisateur } from "./types";

interface ContexteAuth {
  utilisateur: Utilisateur | null;
  chargement: boolean;
  connecter: (email: string, motDePasse: string) => Promise<void>;
  deconnecter: () => Promise<void>;
  /** Vrai si l'utilisateur detient la permission, quelle que soit son etendue. */
  peut: (code: string) => boolean;
  /** Etendue de la permission : "global", "portee", ou null. */
  etendue: (code: string) => Etendue | null;
}

const Contexte = createContext<ContexteAuth | null>(null);

export function FournisseurAuth({ children }: { children: React.ReactNode }) {
  const [utilisateur, setUtilisateur] = useState<Utilisateur | null>(null);
  const [chargement, setChargement] = useState(true);
  const router = useRouter();

  // Au chargement, on tente de restaurer la session depuis le jeton stocke
  useEffect(() => {
    let annule = false;
    (async () => {
      if (!jetons.acces()) {
        setChargement(false);
        return;
      }
      try {
        const moi = await api<Utilisateur>("/auth/me");
        if (!annule) setUtilisateur(moi);
      } catch {
        jetons.effacer();
      } finally {
        if (!annule) setChargement(false);
      }
    })();
    return () => {
      annule = true;
    };
  }, []);

  const connecter = useCallback(
    async (email: string, motDePasse: string) => {
      const reponse = await api<ReponseConnexion>("/auth/login", {
        methode: "POST",
        corps: { email, password: motDePasse },
        publique: true,
      });
      jetons.enregistrer(reponse.access, reponse.refresh);
      setUtilisateur(reponse.user);
    },
    [],
  );

  const deconnecter = useCallback(async () => {
    const refresh = jetons.rafraichissement();
    if (refresh) {
      try {
        await api("/auth/logout", { methode: "POST", corps: { refresh } });
      } catch (erreur) {
        // Une deconnexion ne doit jamais bloquer l'utilisateur
        if (!(erreur instanceof ErreurApi)) throw erreur;
      }
    }
    jetons.effacer();
    setUtilisateur(null);
    router.push("/connexion");
  }, [router]);

  const etendue = useCallback(
    (code: string): Etendue | null => utilisateur?.permissions[code] ?? null,
    [utilisateur],
  );

  const peut = useCallback(
    (code: string) => etendue(code) !== null,
    [etendue],
  );

  return (
    <Contexte.Provider
      value={{ utilisateur, chargement, connecter, deconnecter, peut, etendue }}
    >
      {children}
    </Contexte.Provider>
  );
}

export function useAuth() {
  const contexte = useContext(Contexte);
  if (!contexte) {
    throw new Error("useAuth doit etre utilise dans un FournisseurAuth.");
  }
  return contexte;
}