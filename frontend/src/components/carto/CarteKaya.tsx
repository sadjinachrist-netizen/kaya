"use client";

import "leaflet/dist/leaflet.css";
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip } from "react-leaflet";

export interface PointSite {
  id: number;
  projet: string;
  projet_id: number;
  titre: string;
  statut: string;
  localite: string;
  latitude: number;
  longitude: number;
  population_cible: number | null;
}

export interface PointActivite {
  id: number;
  code: string;
  type: string;
  date: string;
  projet: string;
  localite: string;
  agent: string;
  latitude: number;
  longitude: number;
}

export interface PointCouverture {
  prefecture: string;
  chemin: string;
  menages: number;
  latitude: number;
  longitude: number;
}

interface Props {
  sites: PointSite[];
  activites: PointActivite[];
  couverture: PointCouverture[];
  couches: { sites: boolean; activites: boolean; couverture: boolean };
}

/** Rayon proportionnel a la racine du volume : c'est l'aire qui doit
 *  representer la quantite, pas le rayon. */
const rayon = (menages: number) => Math.max(10, Math.sqrt(menages) * 4);

export default function CarteKaya({ sites, activites, couverture, couches }: Props) {
  return (
    <MapContainer
      center={[8.6, 0.95]}
      zoom={7}
      scrollWheelZoom
      style={{ height: "100%", width: "100%" }}
      className="rounded-card"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
      />

      {/* -------- densite de menages, dessinee en premier pour rester dessous -------- */}
      {couches.couverture &&
        couverture.map((zone) => (
          <CircleMarker
            key={`couverture-${zone.prefecture}`}
            center={[zone.latitude, zone.longitude]}
            radius={rayon(zone.menages)}
            pathOptions={{
              color: "#1f4e79",
              weight: 1,
              fillColor: "#1f4e79",
              fillOpacity: 0.18,
            }}
          >
            <Tooltip direction="top">
              <strong>{zone.prefecture}</strong> — {zone.menages} ménages
            </Tooltip>
          </CircleMarker>
        ))}

      {/* ---------------------------- sites d'intervention ---------------------------- */}
      {couches.sites &&
        sites.map((site) => (
          <CircleMarker
            key={`site-${site.id}`}
            center={[site.latitude, site.longitude]}
            radius={7}
            pathOptions={{
              color: "#ffffff",
              weight: 2,
              fillColor: "#004429",
              fillOpacity: 1,
            }}
          >
            <Popup>
              <p style={{ margin: 0, fontWeight: 600 }}>{site.titre}</p>
              <p style={{ margin: "2px 0 0", fontFamily: "monospace", fontSize: 12 }}>
                {site.projet} · {site.statut}
              </p>
              <p style={{ margin: "6px 0 0", fontSize: 12 }}>
                Localité : {site.localite}
                {site.population_cible !== null && (
                  <>
                    <br />
                    Population cible : {site.population_cible.toLocaleString("fr-FR")}
                  </>
                )}
              </p>
            </Popup>
          </CircleMarker>
        ))}

      {/* ------------------------------ activites validees ------------------------------ */}
      {couches.activites &&
        activites.map((activite) => (
          <CircleMarker
            key={`activite-${activite.id}`}
            center={[activite.latitude, activite.longitude]}
            radius={4}
            pathOptions={{
              color: "#a5761a",
              weight: 1,
              fillColor: "#a5761a",
              fillOpacity: 0.85,
            }}
          >
            <Popup>
              <p style={{ margin: 0, fontWeight: 600 }}>{activite.type}</p>
              <p style={{ margin: "2px 0 0", fontFamily: "monospace", fontSize: 12 }}>
                {activite.code} · {activite.projet}
              </p>
              <p style={{ margin: "6px 0 0", fontSize: 12 }}>
                {activite.date} — {activite.localite}
                <br />
                Saisie par {activite.agent}
              </p>
            </Popup>
          </CircleMarker>
        ))}
    </MapContainer>
  );
}