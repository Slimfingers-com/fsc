import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("./api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("./api")>();
  return { ...actual, listStories: vi.fn() };
});

import { ApiError, listStories } from "./api";
import { loadFeaturedStories } from "./featured-stories";

afterEach(() => vi.resetAllMocks());

describe("optional featured homepage stories", () => {
  it("skips the query when the panel will not be displayed", async () => {
    expect(await loadFeaturedStories(false)).toBeNull();
    expect(listStories).not.toHaveBeenCalled();
  });

  it("keeps the homepage usable on a temporary server-side failure", async () => {
    vi.mocked(listStories).mockRejectedValueOnce(
      new ApiError(504, "Backend-Zeitüberschreitung.", "correlation-1"),
    );
    expect(await loadFeaturedStories(true)).toBeNull();
    expect(listStories).toHaveBeenCalledWith({
      sort: "newest", page: 1, minSources: 2,
    });
  });

  it("does not hide client errors and implementation bugs", async () => {
    vi.mocked(listStories).mockRejectedValueOnce(new ApiError(400, "Invalid filter", "id"));
    await expect(loadFeaturedStories(true)).rejects.toMatchObject({ status: 400 });
    vi.mocked(listStories).mockRejectedValueOnce(new TypeError("Unexpected data"));
    await expect(loadFeaturedStories(true)).rejects.toThrow(TypeError);
  });

  it("preserves healthy results for the featured panel", async () => {
    const page = { items: [], total: 0, page: 1, page_size: 20, pages: 0 };
    vi.mocked(listStories).mockResolvedValueOnce(page);
    expect(await loadFeaturedStories(true)).toEqual(page);
  });
});
