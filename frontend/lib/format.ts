export function formatDate(value: string | null): string {
  if (!value) return "Unbekannt";
  return new Intl.DateTimeFormat("de-DE", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Europe/Berlin",
  }).format(new Date(value));
}

export function label(value: string): string {
  const labels: Record<string, string> = {
    shared: "Mehrere unabhängige Quellen",
    single_source: "Ein unabhängiger Quellenverbund",
    contradiction: "Widerspruch",
    no_attributed_perspective: "Keine attribuierte Perspektive",
    limited_independent_content_sources: "Begrenzte unabhängige Quellenabdeckung",
    signal_without_content_coverage: "Signal ohne Inhaltsabdeckung",
    primary_source: "Primärquelle",
    official_data: "Offizielle Daten",
    study: "Studie",
    direct_quote: "Direktes Zitat",
    press_release: "Pressemitteilung",
    independent_reporting: "Unabhängige Berichterstattung",
    context: "Kontext",
    supports: "Unterstützt",
    exact: "Exakt",
    lexical: "Lexikalisch ähnlich",
  };
  return labels[value] ?? value.replaceAll("_", " ");
}

export function percent(value: number): string {
  return new Intl.NumberFormat("de-DE", {
    style: "percent",
    maximumFractionDigits: 0,
  }).format(value);
}

export function cleanSearchParam(
  value: string | string[] | undefined,
): string | undefined {
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  return trimmed || undefined;
}

export function positivePage(value: string | undefined): number {
  const parsed = Number.parseInt(value ?? "1", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 1;
}
