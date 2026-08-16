/** Types renvoyes par l'API Kaya. */

export type Etendue = "global" | "portee";

export interface Role {
  code: string;
  label: string;
}

export interface Utilisateur {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string;
  roles: Role[];
  permissions: Record<string, Etendue>;
  mfa_required: boolean;
  is_staff: boolean;
  is_superuser: boolean;
  last_login: string | null;
}

export interface ReponseConnexion {
  access: string;
  refresh: string;
  user: Utilisateur;
}

export interface PageResultats<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type StatutIndicateur = "atteint" | "en_cours" | "en_retard";

export interface TableauDeBord {
  role: string | null;
  tuiles: Record<string, number>;
  [autre: string]: unknown;
}



export interface IndicateurResume {
  id: number;
  code: string;
  titre: string;
  unite: string;
  cible: string;
  atteint: string;
  taux: number;
  attendu: number;
  statut: StatutIndicateur;
}

export interface LigneBudget {
  convention: string;
  bailleur: string;
  montant: string;
  devise: string;
  consomme: number;
  temps_ecoule: number;
  ecart: number;
  alerte: "sous_consommation" | "sur_consommation" | null;
}

export type TrancheSadd = { hommes: number; femmes: number; total: number };
export type Sadd = Record<string, TrancheSadd>;

export interface EcheanceResume {
  id: number;
  type: string;
  convention: string;
  echeance: string;
  jours_restants: number;
  alerte: string | null;
}

export interface ActiviteAValider {
  id: number;
  code: string;
  projet: string;
  type: string;
  date: string;
  zone: string;
  agent: string;
  alertes: string[];
}

export interface TableauProjet extends TableauDeBord {
  indicateurs: {
    repartition: Record<StatutIndicateur, number>;
    detail: IndicateurResume[];
  };
  budget: LigneBudget[];
  sadd: Sadd;
  echeances: EcheanceResume[];
}

export interface TableauSuperviseur extends TableauDeBord {
  file_validation: ActiviteAValider[];
  par_agent: {
    agent__username: string;
    agent__first_name: string;
    agent__last_name: string;
    total: number;
    validees: number;
    rejetees: number;
  }[];
}

export interface ActiviteListe {
  id: number;
  code: string;
  project: number;
  project_code: string;
  type: string;
  type_label: string;
  activity_date: string;
  zone: number;
  zone_name: string;
  status: string;
  status_label: string;
  agent: number;
  agent_name: string;
  nb_alertes: number;
  created_at: string;
}

export interface PieceJointe {
  id: number;
  file: string;
  mime_type: string;
  size: number;
  caption: string;
  uploaded_at: string;
}

export interface ActiviteDetail extends ActiviteListe {
  description: string;
  results: string;
  latitude: string | null;
  longitude: string | null;
  gps_accuracy: number | null;
  attachments: PieceJointe[];
  alertes_qualite: string[];
  participants_totaux: { hommes: number; femmes: number; total: number };
  transitions_possibles: string[];
  est_modifiable: boolean;
  submitted_at: string | null;
  validated_by_name: string | null;
  validated_at: string | null;
  rejection_reason: string;
  entry_duration_seconds: number | null;
  client_uuid: string | null;
}


export interface ProjetListe {
  id: number;
  code: string;
  title: string;
  status: string;
  status_label: string;
  sectors: string[];
  start_date: string;
  end_date: string;
  manager: number;
  manager_name: string;
  target_beneficiaries: number;
  progress_rate: string;
}

export interface SiteIntervention {
  id: number;
  zone: number;
  zone_name: string;
  zone_path: string;
  latitude: string | null;
  longitude: string | null;
  target_population: number | null;
}

export interface MembreEquipe {
  id: number;
  user: number;
  user_name: string;
  project_role: string;
  role_label: string;
  start_date: string;
  end_date: string | null;
  is_active: boolean;
}

export interface ProjetDetail {
  id: number;
  code: string;
  title: string;
  description: string;
  sectors: number[];
  sector_labels: string[];
  start_date: string;
  end_date: string;
  status: string;
  status_label: string;
  target_beneficiaries: number;
  progress_rate: string;
  avancement: {
    temporel: number;
    indicateurs: number | null;
    budgetaire: number | null;
  };
  manager: number;
  manager_name: string;
  sites: SiteIntervention[];
  members: MembreEquipe[];
  transitions_possibles: string[];
  created_at: string;
  updated_at: string;
}


export interface MenageListe {
  id: number;
  code: string;
  head_name: string;
  size: number;
  nb_membres: number;
  zone: number;
  zone_name: string;
  residence_status: string;
  validation_status: string;
  registered_at: string;
}

export interface TableauAgent {
  role: string;
  tuiles: Record<string, number>;
  collecte_du_mois: { menages: number; activites: number };
  a_corriger: {
    id: number;
    code: string;
    projet: string;
    date: string;
    motif: string;
  }[];
  mes_projets: { id: number; code: string; title: string; status: string }[];
}


export interface ResumeMenage {
  id: number;
  code: string;
  head_name: string;
  size: number;
  zone: string;
  registered_at: string;
  registered_by: string;
}

export interface Doublon {
  id: number;
  menage_a: ResumeMenage;
  menage_b: ResumeMenage;
  score: string;
  status: string;
  reviewed_by: number | null;
  reviewed_at: string | null;
}


export interface IndicateurListe {
  id: number;
  code: string;
  title: string;
  unit: string;
  unit_label: string;
  baseline: string;
  target: string;
  frequency: string;
  computation_mode: string;
  project: number;
  project_code: string;
  element: number;
  element_code: string;
  valeur_atteinte: string;
  taux_atteinte: number;
  statut_atteinte: string;
  taux_attendu: number;
}

export interface Releve {
  id: number;
  indicator: number;
  indicator_code: string;
  period_start: string;
  period_end: string;
  achieved_value: string;
  comment: string;
  evidence: string | null;
  status: string;
  taux_atteinte: number;
  entered_by: number;
  entered_by_name: string;
  validated_by: number | null;
  created_at: string;
}

export interface IndicateurDetail extends IndicateurListe {
  definition: string;
  verification_source: string;
  computation_source: string;
  owner: number | null;
  owner_name: string;
  disaggregations: { id: number; dimension: string; dimension_label: string }[];
  readings: Releve[];
  valeur_calculee: string | null;
}


export interface ConventionListe {
  id: number;
  contract_number: string;
  title: string;
  donor: number;
  donor_name: string;
  amount: string;
  currency: number;
  currency_code: string;
  status: string;
  status_label: string;
  eligibility_start: string;
  eligibility_end: string;
  taux_consommation: number;
  taux_temps_ecoule: number;
  ecart_rythme: number;
  alerte_rythme: string;
}

export interface LigneBudgetaire {
  id: number;
  grant: number;
  code: string;
  label: string;
  category: string;
  category_label: string;
  budgeted_amount: string;
  parent: number | null;
  nb_enfants: number;
  montant_depense: string;
  montant_disponible: string;
  taux_consommation: number;
  est_depassee: boolean;
}

export interface Echeance {
  id: number;
  grant: number;
  type: string;
  type_label: string;
  due_date: string;
  status: string;
  status_label: string;
  submitted_at: string | null;
  document: string | null;
  jours_restants: number;
  alerte: string;
}

export interface Tranche {
  id: number;
  grant: number;
  amount: string;
  expected_date: string;
  received_date: string | null;
  status: string;
  status_label: string;
}

export interface ConventionDetail extends ConventionListe {
  signature_date: string;
  document: string | null;
  created_at: string;
  quote_part_totale: string;
  budget_total: string;
  montant_depense: string;
  montant_disponible: string;
  project_links: {
    id: number;
    grant: number;
    project: number;
    project_code: string;
    project_title: string;
    share_percent: string;
  }[];
  budget_lines: LigneBudgetaire[];
  deadlines: Echeance[];
  installments: Tranche[];
}

export interface Depense {
  id: number;
  budget_line: number;
  budget_line_code: string;
  project: number;
  project_code: string;
  label: string;
  amount: string;
  currency: number;
  currency_code: string;
  expense_date: string;
  receipt: string | null;
  status: string;
  status_label: string;
  entered_by: number;
  entered_by_name: string;
  validated_by: number | null;
  created_at: string;
}

export interface Devise {
  id: number;
  code: string;
  name: string;
  symbol: string;
  is_base: boolean;
}


export interface NotificationKaya {
  id: number;
  event_type: string;
  event_label: string;
  subject: string;
  message: string;
  channel: string;
  object_type: string;
  object_id: number | null;
  is_read: boolean;
  read_at: string | null;
  sent_at: string;
}

export interface PreferenceNotification {
  id?: number;
  event_type: string;
  event_label: string;
  in_app: boolean;
  by_email: boolean;
}



/** Telechargement d'un fichier protege.
 *  Un <a href> ne peut pas porter le jeton : il faut passer par fetch,
 *  puis fabriquer un lien temporaire vers le blob recu. */
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