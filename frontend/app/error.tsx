"use client";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & {
    digest?: string;
  };
  reset: () => void;
}) {
  return (
    <section className="empty-state top-space">
      <p className="eyebrow">
        Verbindung fehlgeschlagen
      </p>
      <h1>
        Die Daten konnten nicht
        geladen werden.
      </h1>
      <p>
        Das Backend ist momentan nicht
        erreichbar oder hat die Anfrage
        abgelehnt.
      </p>
      {error.digest ? (
        <p className="support-reference">
          Referenz: {error.digest}
        </p>
      ) : null}
      <button
        onClick={() => reset()}
      >
        Erneut versuchen
      </button>
    </section>
  );
}
