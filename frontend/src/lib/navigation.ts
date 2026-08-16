import {
  Building2,
  ClipboardCheck,
  Copy,
  LayoutDashboard,
  Map,
  Receipt,
  ShieldCheck,
  Target,
  Users,
  Wallet,
  MapPin,
  Download,
} from "lucide-react";

export interface Entree {
  libelle: string;
  chemin: string;
  icone: typeof LayoutDashboard;
  /** Permission requise ; absente = visible par tous les connectes. */
  permission?: string;
}

export const NAVIGATION: Entree[] = [
  { libelle: "Tableau de bord", chemin: "/tableau-de-bord", icone: LayoutDashboard },
  { libelle: "Projets", chemin: "/projets", icone: Building2, permission: "projet.consulter" },
  { libelle: "Validation", chemin: "/validation", icone: ClipboardCheck, permission: "activite.valider" },
  { libelle: "Ménages", chemin: "/menages", icone: Users, permission: "beneficiaire.consulter" },
  { libelle: "Activités", chemin: "/activites", icone: Map, permission: "activite.consulter" },
  { libelle: "Cartographie", chemin: "/cartographie", icone: MapPin, permission: "projet.consulter" },
  { libelle: "Doublons", chemin: "/doublons", icone: Copy, permission: "doublon.arbitrer" },
  { libelle: "Indicateurs", chemin: "/indicateurs", icone: Target, permission: "indicateur.consulter" },
  { libelle: "Financements", chemin: "/financements", icone: Wallet, permission: "financement.consulter" },
  { libelle: "Dépenses", chemin: "/depenses", icone: Receipt, permission: "budget.consulter" },
  { libelle: "Exports", chemin: "/exports", icone: Download, permission: "export.realiser" },
  { libelle: "Habilitations", chemin: "/habilitations", icone: ShieldCheck, permission: "role.gerer" },
];