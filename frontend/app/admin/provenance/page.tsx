import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { AdminSignOutButton } from "@/components/admin-auth-buttons";
import { hasAdminSession } from "@/lib/admin-auth";
import { listProvenanceReviewQueue } from "@/lib/admin-api";
import { safeExternalUrl } from "@/lib/format";
import type { ProvenanceReviewStatus } from "@/lib/types";
import { reviewProvenance } from "../actions";

export const metadata: Metadata = { title: "Provenance Review" };
export const dynamic = "force-dynamic";

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };
const statuses: ProvenanceReviewStatus[] = ["pending", "verified", "rejected"];

function one(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value;
}

export default async function ProvenanceReviewPage({ searchParams }: Props) {
  if (!(await hasAdminSession())) redirect("/admin/login");
  const raw = await searchParams;
  const rawStatus = one(raw.status);
  const status: ProvenanceReviewStatus = statuses.includes(rawStatus as ProvenanceReviewStatus)
    ? rawStatus as ProvenanceReviewStatus : "pending";
  const page = Math.max(1, Number.parseInt(one(raw.page) ?? "1", 10) || 1);
  const limit = 25;
  const result = await listProvenanceReviewQueue(status, (page - 1) * limit, limit);
  const pages = Math.max(1, Math.ceil(result.total / limit));

  return (
    <section className="section top-space">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Administration</p>
          <h1>Provenance Review</h1>
          <p className="lead compact">{result.total} Einträge mit Status {status}.</p>
        </div>
        <AdminSignOutButton />
      </div>
      <nav className="admin-tabs" aria-label="Review-Status">
        {statuses.map((item) => (
          <Link key={item} className={item === status ? "active" : ""} href={`/admin/provenance?status=${item}`}>
            {item}
          </Link>
        ))}
      </nav>
      <div className="stack">
        {result.items.map((item) => (
          <article className="card provenance-card" key={item.provenance_id}>
            <div className="provenance-heading">
              <div>
                <p className="eyebrow">{item.upstream_source_name} → {item.publisher_source_name}</p>
                <h3>{item.article_title ?? "Artikel ohne Titel"}</h3>
              </div>
              <strong className="confidence">{Math.round(item.confidence * 100)} %</strong>
            </div>
            <div className="meta-row">
              <span>{item.relation_kind}</span><span>{item.detection_method}</span>
              <span>{item.article_author ?? "Autor unbekannt"}</span>
              <span>{item.article_published_at ? new Date(item.article_published_at).toLocaleString("de-DE") : "Datum unbekannt"}</span>
            </div>
            {item.notes ? <p>{item.notes}</p> : null}
            <div className="card-actions">
              {safeExternalUrl(item.article_url) ? <a className="button secondary" href={safeExternalUrl(item.article_url)!} target="_blank" rel="noreferrer">Original öffnen</a> : null}
              {statuses.filter((target) => target !== item.review_status).map((target) => (
                <form action={reviewProvenance} key={target}>
                  <input type="hidden" name="article_id" value={item.article_id} />
                  <input type="hidden" name="provenance_id" value={item.provenance_id} />
                  <input type="hidden" name="review_status" value={target} />
                  <button className={target === "verified" ? "" : "button secondary"} type="submit">{target}</button>
                </form>
              ))}
            </div>
          </article>
        ))}
        {result.items.length === 0 ? <div className="empty">Keine Einträge.</div> : null}
      </div>
      <div className="pagination">
        {page > 1 ? <Link className="button secondary" href={`/admin/provenance?status=${status}&page=${page - 1}`}>Zurück</Link> : <span />}
        <span>Seite {page} von {pages}</span>
        {page < pages ? <Link className="button secondary" href={`/admin/provenance?status=${status}&page=${page + 1}`}>Weiter</Link> : <span />}
      </div>
    </section>
  );
}
