"use client";

import { useQuery } from "@tanstack/react-query";
import { Bell, Leaf, LogOut, Search } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { NAVIGATION } from "@/lib/navigation";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { utilisateur, deconnecter, peut } = useAuth();
  const chemin = usePathname();

  // Le menu se construit a partir des permissions reelles de l'utilisateur.
  const entrees = NAVIGATION.filter((e) => !e.permission || peut(e.permission));

  const roleAffiche = utilisateur?.roles[0]?.label ?? "Utilisateur";

  // Compteur rafraichi toutes les minutes, sans intervention de l'utilisateur.
  const compteur = useQuery({
    queryKey: ["notifications-compteur"],
    queryFn: () => api<{ non_lues: number }>("/notifications/compteur/"),
    refetchInterval: 60_000,
  });

  const nonLues = compteur.data?.non_lues ?? 0;

  return (
    <div className="min-h-screen bg-background">
      {/* ------------------------- barre laterale ------------------------- */}
      <aside className="fixed left-0 top-0 z-40 flex h-full w-60 flex-col bg-primary text-on-primary">
        <div className="flex items-center gap-3 px-5 py-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-on-primary">
            <Leaf className="h-5 w-5 text-primary" strokeWidth={2.2} />
          </div>
          <span className="text-heading tracking-wide">KAYA</span>
        </div>

        <nav className="scrollbar-fine flex-1 overflow-y-auto py-2">
          {entrees.map((entree) => {
            const actif = chemin.startsWith(entree.chemin);
            const Icone = entree.icone;
            return (
              <Link
                key={entree.chemin}
                href={entree.chemin}
                aria-current={actif ? "page" : undefined}
                className={`flex items-center gap-3 border-l-4 px-5 py-3 text-body transition ${
                  actif
                    ? "border-on-primary bg-on-primary/10 font-semibold"
                    : "border-transparent text-on-primary/70 hover:bg-on-primary/5 hover:text-on-primary"
                }`}
              >
                <Icone className="h-5 w-5 shrink-0" />
                <span>{entree.libelle}</span>
              </Link>
            );
          })}
        </nav>

        <button
          onClick={deconnecter}
          className="flex items-center gap-3 border-t border-on-primary/10 px-5 py-4 text-body text-on-primary/60 transition hover:text-on-primary"
        >
          <LogOut className="h-5 w-5" />
          Déconnexion
        </button>
      </aside>

      {/* ---------------------------- en-tete ---------------------------- */}
      <div className="pl-60">
        <header className="fixed left-60 right-0 top-0 z-30 flex h-14 items-center justify-between gap-4 border-b border-border bg-surface/90 px-6 backdrop-blur">
          <div className="relative max-w-md flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted" />
            <input
              type="search"
              placeholder="Rechercher un ménage, une activité…"
              className="w-full rounded-lg bg-surface-low py-2 pl-9 pr-3 text-body outline-none transition focus:ring-2 focus:ring-info/15"
            />
          </div>

          <div className="flex items-center gap-4">
            <Link
              href="/notifications"
              aria-label={
                nonLues > 0 ? `${nonLues} notifications non lues` : "Notifications"
              }
              className="relative p-2 text-ink-muted transition hover:text-ink"
            >
              <Bell className="h-5 w-5" />
              {nonLues > 0 && (
                <span className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold leading-none text-white">
                  {nonLues > 99 ? "99+" : nonLues}
                </span>
              )}
            </Link>
            <div className="flex items-center gap-3 border-l border-border pl-4">
              <div className="text-right">
                <p className="text-body font-semibold leading-tight">
                  {utilisateur?.full_name}
                </p>
                <p className="text-caption text-ink-muted">{roleAffiche}</p>
              </div>
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-caption font-semibold text-on-primary">
                {utilisateur?.first_name?.[0]}
                {utilisateur?.last_name?.[0]}
              </div>
            </div>
          </div>
        </header>

        <main className="px-6 pb-10 pt-20">
          <p className="mb-5 rounded-card border border-warning/25 bg-warning-soft px-4 py-2.5 text-caption text-warning">
            Environnement de démonstration — toutes les données sont fictives et
            générées automatiquement. La base est réinitialisée chaque nuit.
          </p>
          {children}
        </main>
      </div>
    </div>
  );
}