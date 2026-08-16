"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BellOff, CheckCheck, LoaderCircle, Mail, Monitor } from "lucide-react";
import { useState } from "react";

import { api } from "@/lib/api";
import type {
  NotificationKaya,
  PageResultats,
  PreferenceNotification,
} from "@/lib/types";

const quand = (iso: string) => {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (minutes < 60) return `il y a ${Math.max(minutes, 1)} min`;
  if (minutes < 1440) return `il y a ${Math.round(minutes / 60)} h`;
  return new Date(iso).toLocaleDateString("fr-FR");
};

export default function PageNotifications() {
  const client = useQueryClient();
  const [onglet, setOnglet] = useState<"liste" | "preferences">("liste");
  const [nonLuesSeules, setNonLuesSeules] = useState(false);

  const liste = useQuery({
    queryKey: ["notifications", nonLuesSeules],
    queryFn: () =>
      api<PageResultats<NotificationKaya>>("/notifications/", {
        parametres: nonLuesSeules ? { non_lues: "1" } : undefined,
      }),
    placeholderData: (precedent) => precedent,
  });

  const rafraichir = () => {
    client.invalidateQueries({ queryKey: ["notifications"] });
    client.invalidateQueries({ queryKey: ["notifications-compteur"] });
  };

  const marquerLue = useMutation({
    mutationFn: (id: number) =>
      api<NotificationKaya>(`/notifications/${id}/marquer-lue/`, { methode: "POST" }),
    onSuccess: rafraichir,
  });

  const toutMarquer = useMutation({
    mutationFn: () =>
      api<{ marquees: number }>("/notifications/tout-marquer-lu/", { methode: "POST" }),
    onSuccess: rafraichir,
  });

  const notifications = liste.data?.results ?? [];
  const nbNonLues = notifications.filter((n) => !n.is_read).length;

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-title">Notifications</h1>
          <p className="mt-1 text-body text-ink-muted">
            Ce qui vous concerne : validations attendues, échéances, alertes.
          </p>
        </div>
        {onglet === "liste" && nbNonLues > 0 && (
          <button
            onClick={() => toutMarquer.mutate()}
            disabled={toutMarquer.isPending}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-caption text-ink transition hover:bg-surface-low disabled:opacity-50"
          >
            <CheckCheck className="h-3.5 w-3.5" />
            Tout marquer comme lu
          </button>
        )}
      </header>

      <div className="flex gap-2">
        <Onglet actif={onglet === "liste"} onClick={() => setOnglet("liste")}>
          Reçues
        </Onglet>
        <Onglet actif={onglet === "preferences"} onClick={() => setOnglet("preferences")}>
          Préférences
        </Onglet>
      </div>

      {onglet === "liste" ? (
        <>
          <label className="flex items-center gap-2 text-caption text-ink-muted">
            <input
              type="checkbox"
              checked={nonLuesSeules}
              onChange={(e) => setNonLuesSeules(e.target.checked)}
              className="accent-[var(--color-primary)]"
            />
            N&apos;afficher que les non lues
          </label>

          <section className="rounded-card bg-surface shadow-sm">
            {liste.isLoading ? (
              <div className="flex h-48 items-center justify-center">
                <LoaderCircle className="h-5 w-5 animate-spin text-ink-muted" />
              </div>
            ) : notifications.length === 0 ? (
              <div className="p-10 text-center">
                <BellOff className="mx-auto h-8 w-8 text-ink-muted" />
                <p className="mt-3 text-body text-ink-muted">
                  Aucune notification{nonLuesSeules ? " non lue" : ""}.
                </p>
              </div>
            ) : (
              <ul className="divide-y divide-border">
                {notifications.map((notification) => (
                  <li
                    key={notification.id}
                    className={`flex gap-3 px-5 py-4 transition ${
                      notification.is_read ? "" : "bg-primary-soft/40"
                    }`}
                  >
                    <span
                      aria-hidden
                      className={`mt-2 h-2 w-2 shrink-0 rounded-full ${
                        notification.is_read ? "bg-transparent" : "bg-primary"
                      }`}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <p className="text-body font-semibold text-ink">
                          {notification.subject}
                        </p>
                        <span className="shrink-0 text-caption text-ink-muted">
                          {quand(notification.sent_at)}
                        </span>
                      </div>
                      <p className="mt-0.5 text-body text-ink-muted">
                        {notification.message}
                      </p>
                      <div className="mt-1.5 flex items-center gap-3">
                        <span className="rounded bg-surface-low px-2 py-0.5 text-caption text-ink-muted">
                          {notification.event_label}
                        </span>
                        {!notification.is_read && (
                          <button
                            onClick={() => marquerLue.mutate(notification.id)}
                            className="text-caption text-primary underline"
                          >
                            Marquer comme lue
                          </button>
                        )}
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : (
        <Preferences />
      )}
    </div>
  );
}

/* ------------------------------- preferences ------------------------------- */

function Preferences() {
  const client = useQueryClient();

  const disponibles = useQuery({
    queryKey: ["preferences-disponibles"],
    queryFn: () =>
      api<PreferenceNotification[]>("/preferences-notifications/disponibles/"),
  });

  const existantes = useQuery({
    queryKey: ["preferences-notifications"],
    queryFn: () => api<PreferenceNotification[]>("/preferences-notifications/"),
  });

  const enregistrer = useMutation({
    mutationFn: async ({
      event_type,
      in_app,
      by_email,
    }: {
      event_type: string;
      in_app: boolean;
      by_email: boolean;
    }) => {
      // une preference existe deja pour cet evenement : on la met a jour,
      // sinon on la cree — l'unicite (utilisateur, evenement) l'impose
      const existante = (existantes.data ?? []).find(
        (p) => p.event_type === event_type,
      );
      return api<PreferenceNotification>(
        existante
          ? `/preferences-notifications/${existante.id}/`
          : "/preferences-notifications/",
        {
          methode: existante ? "PATCH" : "POST",
          corps: { event_type, in_app, by_email },
        },
      );
    },
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ["preferences-notifications"] });
      client.invalidateQueries({ queryKey: ["preferences-disponibles"] });
    },
  });

  if (disponibles.isLoading) {
    return (
      <div className="flex h-48 items-center justify-center">
        <LoaderCircle className="h-5 w-5 animate-spin text-ink-muted" />
      </div>
    );
  }

  return (
    <section className="rounded-card bg-surface shadow-sm">
      <div className="border-b border-border px-5 py-4">
        <p className="text-body text-ink-muted">
          Choisissez les événements qui vous sont notifiés et par quel canal.
        </p>
      </div>
      <ul className="divide-y divide-border">
        {(disponibles.data ?? []).map((preference) => (
          <li
            key={preference.event_type}
            className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5"
          >
            <span className="text-body text-ink">{preference.event_label}</span>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-1.5 text-caption text-ink-muted">
                <input
                  type="checkbox"
                  checked={preference.in_app}
                  disabled={enregistrer.isPending}
                  onChange={(e) =>
                    enregistrer.mutate({
                      event_type: preference.event_type,
                      in_app: e.target.checked,
                      by_email: preference.by_email,
                    })
                  }
                  className="accent-[var(--color-primary)]"
                />
                <Monitor className="h-3.5 w-3.5" />
                Application
              </label>
              <label className="flex items-center gap-1.5 text-caption text-ink-muted">
                <input
                  type="checkbox"
                  checked={preference.by_email}
                  disabled={enregistrer.isPending}
                  onChange={(e) =>
                    enregistrer.mutate({
                      event_type: preference.event_type,
                      in_app: preference.in_app,
                      by_email: e.target.checked,
                    })
                  }
                  className="accent-[var(--color-primary)]"
                />
                <Mail className="h-3.5 w-3.5" />
                Email
              </label>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function Onglet({
  actif,
  onClick,
  children,
}: {
  actif: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-full px-4 py-1.5 text-caption transition ${
        actif ? "bg-primary text-on-primary" : "bg-surface text-ink-muted shadow-sm hover:text-ink"
      }`}
    >
      {children}
    </button>
  );
}