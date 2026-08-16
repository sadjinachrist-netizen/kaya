"use client";

import { LoaderCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { AppShell } from "@/components/AppShell";
import { useAuth } from "@/lib/auth";

export default function LayoutApplication({
  children,
}: {
  children: React.ReactNode;
}) {
  const { utilisateur, chargement } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!chargement && !utilisateur) router.replace("/connexion");
  }, [chargement, utilisateur, router]);

  if (chargement || !utilisateur) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoaderCircle className="h-6 w-6 animate-spin text-ink-muted" />
      </div>
    );
  }

  return <AppShell>{children}</AppShell>;
}