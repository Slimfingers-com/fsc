import Link from "next/link";

type Props = {
  page: number;
  pages: number;
  pathname: string;
  searchParams?: Record<string, string | undefined>;
};

function pageHref(
  pathname: string,
  page: number,
  values: Record<string, string | undefined>,
): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value) params.set(key, value);
  }
  params.set("page", String(page));
  return `${pathname}?${params.toString()}`;
}

export function Pagination({
  page,
  pages,
  pathname,
  searchParams = {},
}: Props) {
  if (pages <= 1) return null;
  return (
    <nav className="pagination" aria-label="Seitennavigation">
      {page > 1 ? (
        <Link className="button secondary" href={pageHref(pathname, page - 1, searchParams)}>
          ← Zurück
        </Link>
      ) : <span />}
      <span>Seite <strong>{page}</strong> von <strong>{pages}</strong></span>
      {page < pages ? (
        <Link className="button secondary" href={pageHref(pathname, page + 1, searchParams)}>
          Weiter →
        </Link>
      ) : <span />}
    </nav>
  );
}
