import { ApiError, listStories } from "./api";

/** Featured Stories are optional editorial content, not a prerequisite for news. */
export async function loadFeaturedStories(visible: boolean) {
  if (!visible) return null;

  try {
    return await listStories({ sort: "newest", page: 1, minSources: 2 });
  } catch (error) {
    // The API client has already logged the request ID and failure. Keep the
    // main news feed usable during a transient Story-listing backend problem.
    // Do not disguise validation/authorization errors or programming defects.
    if (error instanceof ApiError && error.status >= 500) {
      return null;
    }
    throw error;
  }
}
