/** Client HTTP de l'API Kaya : jetons, rafraichissement, erreurs typees. */

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000/api";

const CLE_ACCES = "kaya.acces";
const CLE_RAFRAICHISSEMENT = "kaya.rafraichissement";

const navigateur = () => typeof window !== "undefined";

export const jetons = {
  acces: () => (navigateur() ? localStorage.getItem(CLE_ACCES) : null),
  rafraichissement: () =>
    navigateur() ? localStorage.getItem(CLE_RAFRAICHISSEMENT) : null,
  enregistrer(acces: string, rafraichissement: string) {
    if (!navigateur()) return;
    localStorage.setItem(CLE_ACCES, acces);
    localStorage.setItem(CLE_RAFRAICHISSEMENT, rafraichissement);
  },
  effacer() {
    if (!navigateur()) return;
    localStorage.removeItem(CLE_ACCES);
    localStorage.removeItem(CLE_RAFRAICHISSEMENT);
  },
};

export class ErreurApi extends Error {
  statut: number;
  details: unknown;

  constructor(statut: number, message: string, details?: unknown) {
    super(message);
    this.name = "ErreurApi";
    this.statut = statut;
    this.details = details;
  }

  /** Messages d'erreur par champ, tels que renvoyes par DRF. */
  get parChamp(): Record<string, string[]> {
    if (this.details && typeof this.details === "object" && !Array.isArray(this.details)) {
      return this.details as Record<string, string[]>;
    }
    return {};
  }
}

function messageLisible(statut: number, corps: unknown): string {
  if (corps && typeof corps === "object") {
    const donnees = corps as Record<string, unknown>;
    if (typeof donnees.detail === "string") return donnees.detail;
    const premier = Object.values(donnees)[0];
    if (Array.isArray(premier) && typeof premier[0] === "string") return premier[0];
  }
  if (statut === 401) return "Session expiree, veuillez vous reconnecter.";
  if (statut === 403) return "Vous n'avez pas les droits necessaires.";
  if (statut === 404) return "Ressource introuvable.";
  if (statut >= 500) return "Le serveur a rencontre une erreur.";
  return "La requete a echoue.";
}

/** Une seule tentative de rafraichissement a la fois. */
let rafraichissementEnCours: Promise<boolean> | null = null;

async function rafraichirJeton(): Promise<boolean> {
  const refresh = jetons.rafraichissement();
  if (!refresh) return false;

  if (!rafraichissementEnCours) {
    rafraichissementEnCours = (async () => {
      try {
        const reponse = await fetch(`${BASE}/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh }),
        });
        if (!reponse.ok) {
          jetons.effacer();
          return false;
        }
        const donnees = await reponse.json();
        jetons.enregistrer(donnees.access, donnees.refresh ?? refresh);
        return true;
      } catch {
        jetons.effacer();
        return false;
      } finally {
        rafraichissementEnCours = null;
      }
    })();
  }
  return rafraichissementEnCours;
}

interface Options {
  methode?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  corps?: unknown;
  /** Requete publique : aucun jeton envoye, aucun rafraichissement tente. */
  publique?: boolean;
  parametres?: Record<string, string | number | undefined | null>;
}

export async function api<T>(chemin: string, options: Options = {}): Promise<T> {
  const { methode = "GET", corps, publique = false, parametres } = options;

  let url = `${BASE}${chemin}`;
  if (parametres) {
    const filtres = Object.entries(parametres)
      .filter(([, v]) => v !== undefined && v !== null && v !== "")
      .map(([k, v]) => [k, String(v)]);
    if (filtres.length) url += `?${new URLSearchParams(filtres as string[][])}`;
  }

  const envoyer = async (): Promise<Response> => {
    const entetes: Record<string, string> = {};
    if (corps !== undefined) entetes["Content-Type"] = "application/json";
    if (!publique) {
      const acces = jetons.acces();
      if (acces) entetes.Authorization = `Bearer ${acces}`;
    }
    return fetch(url, {
      method: methode,
      headers: entetes,
      body: corps === undefined ? undefined : JSON.stringify(corps),
    });
  };

  let reponse = await envoyer();

  // Jeton expire : on rafraichit une fois, puis on rejoue la requete
  if (reponse.status === 401 && !publique && jetons.rafraichissement()) {
    if (await rafraichirJeton()) {
      reponse = await envoyer();
    }
  }

  if (reponse.status === 204) return undefined as T;

  const texte = await reponse.text();
  const donnees = texte ? JSON.parse(texte) : null;

  if (!reponse.ok) {
    throw new ErreurApi(reponse.status, messageLisible(reponse.status, donnees), donnees);
  }
  return donnees as T;
}


/** Envoi de fichier : on laisse le navigateur poser lui-meme le Content-Type,
 *  car lui seul connait la frontiere (boundary) du corps multipart. */
export async function televerser<T>(chemin: string, donnees: FormData): Promise<T> {
  const envoyer = async (): Promise<Response> => {
    const entetes: Record<string, string> = {};
    const acces = jetons.acces();
    if (acces) entetes.Authorization = `Bearer ${acces}`;
    return fetch(`${BASE}${chemin}`, { method: "POST", headers: entetes, body: donnees });
  };

  let reponse = await envoyer();
  if (reponse.status === 401 && jetons.rafraichissement()) {
    if (await rafraichirJeton()) reponse = await envoyer();
  }

  const texte = await reponse.text();
  const corps = texte ? JSON.parse(texte) : null;
  if (!reponse.ok) {
    throw new ErreurApi(reponse.status, messageLisible(reponse.status, corps), corps);
  }
  return corps as T;
}


/** Telechargement d'un fichier protege.
 *  Un <a href> ne peut pas porter le jeton d'authentification : il faut
 *  passer par fetch, puis fabriquer un lien temporaire vers le blob recu. */
export async function telecharger(chemin: string, nomParDefaut: string): Promise<void> {
  const envoyer = async (): Promise<Response> => {
    const entetes: Record<string, string> = {};
    const acces = jetons.acces();
    if (acces) entetes.Authorization = `Bearer ${acces}`;
    return fetch(`${BASE}${chemin}`, { headers: entetes });
  };

  let reponse = await envoyer();
  if (reponse.status === 401 && jetons.rafraichissement()) {
    if (await rafraichirJeton()) reponse = await envoyer();
  }

  if (!reponse.ok) {
    const texte = await reponse.text();
    const corps = texte ? JSON.parse(texte) : null;
    throw new ErreurApi(reponse.status, messageLisible(reponse.status, corps), corps);
  }

  const disposition = reponse.headers.get("Content-Disposition") ?? "";
  const trouve = /filename="?([^";]+)"?/.exec(disposition);

  const blob = await reponse.blob();
  const url = URL.createObjectURL(blob);
  const lien = document.createElement("a");
  lien.href = url;
  lien.download = trouve ? trouve[1] : nomParDefaut;
  document.body.appendChild(lien);
  lien.click();
  lien.remove();
  URL.revokeObjectURL(url);
}