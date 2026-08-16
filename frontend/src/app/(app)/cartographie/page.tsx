"use client";

import { useQuery } from "@tanstack/react-query";
import { LoaderCircle } from "lucide-react";
import dynamic from "next/dynamic";
import { useState } from "react";

import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type {
  PointActivite,
  PointCouverture,
  PointSite,
} from "@/components/carto/CarteKaya";

// Leaflet touche a `window` : la carte ne peut pas etre rendue cote serveur.
const CarteKaya = dynamic(() => import("@/components/carto/CarteKaya"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full items-center justify-center rounded-card bg-surface">
      <LoaderCircle className="h-6 w-6 animate-spin text-ink-muted" />
    </div>
  ),
});

export default function PageCartographie() {
  const { peut } = useAuth();
  const [couches, setCouches] = useState({
    sites: true,
    activites: true,
    couverture: true,
  });

  const sites = useQuery({
    queryKey: ["carto-sites"],
    queryFn: () => api<PointSite[]>("/carto/sites/"),
  });

  const activites = useQuery({
    queryKey: ["carto-activites"],
    queryFn: () => api<PointActivite[]>("/carto/activites/"),
    enabled: peut("activite.consulter"),
  });

  const couverture = useQuery({
    queryKey: ["carto-couverture"],
    queryFn: () => api<PointCouverture[]>("/carto/couverture/"),
    enabled: peut("beneficiaire.consulter"),
  });

  const totalMenages = (couverture.data ?? []).reduce((s, z) => s + z.menages, 0);

  const basculer = (couche: keyof typeof couches) =>
    setCouches((precedent) => ({ ...precedent, [couche]: !precedent[couche] }));

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-title">Cartographie</h1>
        <p className="mt-1 text-body text-ink-muted">
          Sites d&apos;intervention, points de collecte et densité de bénéficiaires,
          restreints à votre périmètre.
        </p>
      </header>

      <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
        <div className="h-[600px] overflow-hidden rounded-card shadow-sm">
          <CarteKaya
            sites={sites.data ?? []}
            activites={activites.data ?? []}
            couverture={couverture.data ?? []}
            couches={couches}
          />
        </div>

        <aside className="space-y-4">
          <section className="rounded-card bg-surface p-5 shadow-sm">
            <h2 className="text-heading">Couches</h2>
            <div className="mt-3 space-y-3">
              <Couche
                actif={couches.sites}
                onChange={() => basculer("sites")}
                pastille="bg-primary"
                libelle="Sites d'intervention"
                total={sites.data?.length ?? 0}
              />
              {peut("activite.consulter") && (
                <Couche
                  actif={couches.activites}
                  onChange={() => basculer("activites")}
                  pastille="bg-warning"
                  libelle="Activités validées"
                  total={activites.data?.length ?? 0}
                />
              )}
              {peut("beneficiaire.consulter") && (
                <Couche
                  actif={couches.couverture}
                  onChange={() => basculer("couverture")}
                  pastille="bg-info/40"
                  libelle="Densité de ménages"
                  total={couverture.data?.length ?? 0}
                />
              )}
            </div>
          </section>

          {peut("beneficiaire.consulter") && (couverture.data?.length ?? 0) > 0 && (
            <section className="rounded-card bg-surface p-5 shadow-sm">
              <h2 className="text-heading">Couverture</h2>
              <p className="mt-0.5 text-caption text-ink-muted">
                {totalMenages.toLocaleString("fr-FR")} ménages sur{" "}
                {couverture.data!.length} préfecture
                {couverture.data!.length > 1 ? "s" : ""}.
              </p>
              <ul className="mt-3 space-y-1.5">
                {couverture.data!.slice(0, 8).map((zone) => (
                  <li
                    key={zone.prefecture}
                    className="flex items-baseline justify-between gap-2 text-body"
                  >
                    <span className="truncate text-ink">{zone.prefecture}</span>
                    <span className="shrink-0 text-caption text-ink-muted">
                      {zone.menages}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <p className="rounded-card bg-surface-low p-4 text-caption text-ink-muted">
            Les ménages ne sont jamais représentés individuellement : leur position
            exacte permettrait de retrouver un foyer. Seule la densité par préfecture
            est cartographiée.
          </p>
        </aside>
      </div>
    </div>
  );
}

function Couche({
  actif,
  onChange,
  pastille,
  libelle,
  total,
}: {
  actif: boolean;
  onChange: () => void;
  pastille: string;
  libelle: string;
  total: number;
}) {
  return (
    <label className="flex items-center gap-2.5">
      <input
        type="checkbox"
        checked={actif}
        onChange={onChange}
        className="accent-[var(--color-primary)]"
      />
      <span className={`h-3 w-3 shrink-0 rounded-full ${pastille}`} />
      <span className="flex-1 text-body text-ink">{libelle}</span>
      <span className="text-caption text-ink-muted">{total}</span>
    </label>
  );
}