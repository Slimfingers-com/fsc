import type { Metadata } from "next";
import Link from "next/link";
import { listReadyAnalyses } from "@/lib/api";
import { formatDate } from "@/lib/format";

export const metadata: Metadata = {
  title: "Fertige Analysen",
  description:
    "Bereits vollständig aufbereitete deutschsprachige Nachrichtenanalysen: Aussagen und Originalquellen im Vergleich.",
};

export const dynamic = "force-dynamic";

export default async function AnalysenPage() {
  const stories = await listReadyAnalyses(6);

  return (
    <section className="section top-space">
      <div className="section-heading">
        <div>
          <p className="eyebrow">AUSSAGEN UND QUELLEN IM VERGLEICH</p>
          <h1>Fertige Analysen</h1>
          <p className="lead compact">
            Hier findest du bereits abgeschlossene Aussagenvergleiche.
            Jede Auswahl wurde auf einen aktuellen Analysestand geprüft
            und enthält Beiträge von mindestens zwei deutschsprachigen Medien.
          </p>
        </div>
        <Link href="/stories" className="text-link">
          Alle Ereignisse ansehen <span aria-hidden="true">↗</span>
        </Link>
      </div>

      {stories.length ? (
        <div className="story-grid" style={{ marginTop: "1.6rem" }}>
          {stories.map((story) => (
            <Link
              key={story.story_id}
              className="card story-card"
              href={`/stories/${story.story_id}/analysis`}
            >
              <div className="meta-row">
                <span>FERTIG AUSGEWERTET</span>
                <span>{formatDate(story.last_article_at)}</span>
              </div>
              <h2>{story.title}</h2>
              <p>
                {story.source_count} deutschsprachige Medien ·{" "}
                {story.article_count} Berichte
              </p>
              <span className="text-link">
                Aussagen vergleichen <span aria-hidden="true">↗</span>
              </span>
            </Link>
          ))}
        </div>
      ) : (
        <div className="empty top-space">
          Aktuell gibt es noch keine vollständig abgeglichenen
          Ereignisse mit mindestens zwei deutschsprachigen Medien.
          Die Verarbeitung läuft weiter.
        </div>
      )}

      <div className="section top-space">
        <h2>Was bedeutet „fertig ausgewertet“?</h2>
        <p className="section-description">
          FSC hat die Aussagen, Belege, Übereinstimmungen und Abdeckung
          dieses Ereignisses vollständig verarbeitet. Das ist kein
          Wahrheitsurteil: Auch bei einer fertigen Analyse können Aussagen
          nur von einem Medium stammen oder Unterschiede unbestätigt bleiben.
          Neue Berichte können eine erneute Aufbereitung erforderlich machen.
        </p>
      </div>
    </section>
  );
}
