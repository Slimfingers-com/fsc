"use client";

import { signIn, signOut } from "next-auth/react";

export function AdminSignInButton() {
  return (
    <button
      type="button"
      className="button"
      onClick={() => void signIn("zitadel", { callbackUrl: "/admin/provenance" })}
    >
      Mit ZITADEL anmelden
    </button>
  );
}

export function AdminSignOutButton() {
  return (
    <button
      type="button"
      className="button secondary"
      onClick={() => void signOut({ callbackUrl: "/admin/login" })}
    >
      Abmelden
    </button>
  );
}
