import { describe, expect, it } from "vitest";
import { cleanSearchParam, label, percent, positivePage } from "./format";

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
});
