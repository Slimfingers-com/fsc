import Link from "next/link";

export default function NotFound() {
  return (
    <section className="empty-state top-space">
      <p className="eyebrow">404</p><h1>Nicht gefunden</h1>
      <p>Die angeforderte Story oder Seite existiert nicht mehr.</p>
      <Link className="button" href="/">Zur Suche</Link>
    </section>
  );
}
