// German-only presentation is a product preference, not a corpus restriction.
// Preserve international Article rows for backend Story clustering and analysis.
export function isGermanLanguage(code: string | null | undefined): boolean {
  return typeof code === "string" && /^de(?:$|[-_])/i.test(code);
}

export function germanArticles<T extends { language_code: string | null }>(
  articles: readonly T[],
): T[] {
  return articles.filter((article) => isGermanLanguage(article.language_code));
}
