import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { hasAdminSession } from "@/lib/admin-auth";
import { loginAdmin } from "../actions";

export const metadata: Metadata = { title: "Admin-Anmeldung" };
export const dynamic = "force-dynamic";

type Props = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

export default async function AdminLoginPage({ searchParams }: Props) {
  if (await hasAdminSession()) redirect("/admin/provenance");
  const params = await searchParams;
  const failed = params.error === "1";
  return (
    <section className="section top-space admin-login">
      <p className="eyebrow">Interner Bereich</p>
      <h1>Admin-Anmeldung</h1>
      <p className="lead">Zugriff auf die Provenance-Prüfung.</p>
      <form action={loginAdmin} className="card admin-login-form">
        <label>
          Passwort
          <input name="password" type="password" autoComplete="current-password" required />
        </label>
        {failed ? <p className="admin-error">Anmeldung fehlgeschlagen.</p> : null}
        <button type="submit">Anmelden</button>
      </form>
    </section>
  );
}
