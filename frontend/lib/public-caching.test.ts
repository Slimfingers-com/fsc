import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

/**
 * A page-level force-dynamic silently overrides fetch(..., {
 *   next: { revalidate: 60 }
 * }) in Next.js (it is equivalent to force-no-store).
 *
 * These two pages must stay request-rendered via searchParams, but they
 * must not disable the deliberately small public Data Cache globally.
 */
describe("public editorial caching configuration", () => {
  for (const path of ["../app/page.tsx", "../app/stories/page.tsx"]) {
    it(`${path} remains request-rendered without forcing all fetches uncached`, () => {
      const source = readFileSync(new URL(path, import.meta.url), "utf8");
      expect(source).not.toMatch(/export\s+const\s+dynamic\s*=\s*["']force-dynamic["']/);
      expect(source).toContain("await searchParams");
    });
  }
});
