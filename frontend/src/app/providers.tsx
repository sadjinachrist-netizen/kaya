"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

import { FournisseurAuth } from "@/lib/auth";
import { ErreurApi } from "@/lib/api";

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            refetchOnWindowFocus: false,
            retry: (tentatives, erreur) => {
              // Inutile de reessayer une erreur de droits ou de saisie
              if (erreur instanceof ErreurApi && erreur.statut < 500) return false;
              return tentatives < 2;
            },
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={client}>
      <FournisseurAuth>{children}</FournisseurAuth>
    </QueryClientProvider>
  );
}