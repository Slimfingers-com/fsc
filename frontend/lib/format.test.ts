import { describe, expect, it } from "vitest";
import {
  allowedSearchParam,
  cleanSearchParam,
  label,
  percent,
  positivePage,
  safeExternalUrl,
} from "./format";

describe("frontend helpers", () => {
  it("normalizes search values", () => {
    expect(cleanSearchParam("  klima  ")).toBe("klima");
    expect(cleanSearchParam("   ")).toBeUndefined();
    expect(cleanSearchParam(["x"])).toBeUndefined();
  });

  it("normalizes page numbers", () => {
    expect(positivePage("3")).toBe(3);
    expect(positivePage("0")).toBe(1);
    expect(positivePage("x")).toBe(1);
  });

  it("labels analysis values", () => {
    expect(label("shared")).toBe("Mehrere unabhängige Quellen");
    expect(label("contradiction")).toBe("Widerspruch");
  });

  it("formats percentages", () => {
    expect(percent(0.82)).toContain("82");
  });

  it("rejects unsupported sort values", () => {
    expect(
      allowedSearchParam("hacked", ["relevance", "newest"], "relevance"),
    ).toBe("relevance");
    expect(
      allowedSearchParam("newest", ["relevance", "newest"], "relevance"),
    ).toBe("newest");
  });

  it("allows only http and https external links", () => {
    expect(safeExternalUrl("https://example.com/a")).toBe(
      "https://example.com/a",
    );
    expect(safeExternalUrl("javascript:alert(1)")).toBeNull();
    expect(safeExternalUrl("not a url")).toBeNull();
  });
});
