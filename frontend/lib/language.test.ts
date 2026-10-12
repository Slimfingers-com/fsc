import { describe, expect, it } from "vitest";
import { germanArticles, isGermanLanguage } from "./language";

describe("public German-language presentation", () => {
  it("accepts German originals and their regional language tags", () => {
    expect(isGermanLanguage("de")).toBe(true);
    expect(isGermanLanguage("de-DE")).toBe(true);
    expect(isGermanLanguage("de_AT")).toBe(true);
  });

  it("excludes foreign-only or unknown language codes", () => {
    for (const code of ["en", "fr", "nl", "den", "", null, undefined]) {
      expect(isGermanLanguage(code)).toBe(false);
    }
  });

  it("returns only German originals without mutating source data", () => {
    const articles = [
      { article_id: "de", language_code: "de" },
      { article_id: "en", language_code: "en" },
      { article_id: "fr", language_code: "fr" },
    ];
    expect(germanArticles(articles).map((item) => item.article_id)).toEqual(["de"]);
    expect(articles).toHaveLength(3);
    expect(germanArticles([{ language_code: "fr" }])).toEqual([]);
  });
});
