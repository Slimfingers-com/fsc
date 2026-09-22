import { cache } from "react";

import type {
  Page,
  SearchHit,
  StoryAnalysis,
  StoryDetail,
  StorySummary,
} from "./types";

const API_URL = (
  process.env.FSC_API_URL
  ?? "http://localhost:8000"
).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
    public readonly requestId: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function logFailure(
  *,
  requestId,
  path,
  status,
  durationMs,
  errorName,
}: {
  requestId: string;
  path: string;
  status: number;
  durationMs: number;
  errorName?: string;
}) {
  console.error(
    JSON.stringify({
      event: "frontend_api_error",
      request_id: requestId,
      path,
      status,
      duration_ms: durationMs,
      ...(errorName
        ? { error_name: errorName }
        : {}),
    }),
  );
}

async function request<T>(
  path: string,
  params?: URLSearchParams,
): Promise<T> {
  const suffix = params?.size
    ? `?${params.toString()}`
    : "";
  const requestId = crypto.randomUUID();
  const started = Date.now();

  let response: Response;
  try {
    response = await fetch(
      `${API_URL}${path}${suffix}`,
      {
        cache: "no-store",
        signal: AbortSignal.timeout(
          8_000
        ),
        headers: {
          Accept: "application/json",
          "X-Request-ID": requestId,
        },
      },
    );
  } catch (error) {
    const durationMs = (
      Date.now() - started
    );
    const errorName = (
      error instanceof Error
        ? error.name
        : "UnknownError"
    );
    const isTimeout = (
      errorName === "TimeoutError"
      || errorName === "AbortError"
    );
    const status = isTimeout
      ? 504
      : 503;

    logFailure({
      requestId,
      path,
      status,
      durationMs,
      errorName,
    });

    throw new ApiError(
      status,
      isTimeout
        ? "Backend-Zeitüberschreitung."
        : "Backend ist nicht erreichbar.",
      requestId,
    );
  }

  const responseRequestId = (
    response.headers.get(
      "X-Request-ID"
    )
    ?? requestId
  );

  if (!response.ok) {
    let message = (
      `Backend antwortete mit HTTP ${response.status}`
    );
    try {
      const body = (
        await response.json()
      ) as {
        detail?: string;
      };
      if (body.detail) {
        message = body.detail;
      }
    } catch {
      // Keep the status fallback
      // for non-JSON responses.
    }

    logFailure({
      requestId: responseRequestId,
      path,
      status: response.status,
      durationMs: (
        Date.now() - started
      ),
    });

    throw new ApiError(
      response.status,
      message,
      responseRequestId,
    );
  }

  return (
    await response.json()
  ) as T;
}

function set(
  params: URLSearchParams,
  key: string,
  value: string
  | number
  | undefined,
) {
  if (
    value !== undefined
    && value !== ""
  ) {
    params.set(
      key,
      String(value),
    );
  }
}

export async function searchArticles(
  options: {
    q?: string;
    sort?: string;
    page?: number;
  },
): Promise<Page<SearchHit>> {
  const params = new URLSearchParams();
  set(params, "q", options.q);
  set(
    params,
    "sort",
    options.sort ?? "relevance",
  );
  set(
    params,
    "page",
    options.page ?? 1,
  );
  return request<Page<SearchHit>>(
    "/search",
    params,
  );
}

export async function listStories(
  options: {
    sort?: string;
    page?: number;
    minSources?: number;
  },
): Promise<Page<StorySummary>> {
  const params = new URLSearchParams();
  set(
    params,
    "sort",
    options.sort ?? "newest",
  );
  set(
    params,
    "page",
    options.page ?? 1,
  );
  set(
    params,
    "min_sources",
    options.minSources ?? 1,
  );
  return request<Page<StorySummary>>(
    "/stories",
    params,
  );
}

export const getStory = cache(
  async (
    storyId: string,
  ): Promise<StoryDetail> => (
    request<StoryDetail>(
      `/stories/${encodeURIComponent(
        storyId,
      )}`,
    )
  ),
);

export async function getStoryAnalysis(
  storyId: string,
): Promise<StoryAnalysis | null> {
  try {
    return await request<StoryAnalysis>(
      `/stories/${encodeURIComponent(
        storyId,
      )}/analysis`,
    );
  } catch (error) {
    if (
      error instanceof ApiError
      && error.status === 404
    ) {
      return null;
    }
    throw error;
  }
}
