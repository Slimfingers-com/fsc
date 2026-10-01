import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { hasAdminSession } from "@/lib/admin-auth";

export const metadata: Metadata = { title: "Admin-Anmeldung" };
export const dynamic = "force-dynamic";

export default async function AdminLoginPage() {
  if (await hasAdminSession()) redirect("/admin/provenance");
  return (
    <section className="section top-space admin-login">
      <p className="eyebrow">Interner Bereich</p>
      <h1>Admin-Anmeldung</h1>
      <p className="lead">Anmeldung über den europäischen FSC Identity Provider.</p>
      <a className="button" href="/api/auth/signin/zitadel?callbackUrl=/admin/provenance">
        Mit ZITADEL anmelden
      </a>
    </section>
  );
}
