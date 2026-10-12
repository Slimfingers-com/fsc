import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  ApiError,
  listStories,
  searchArticles,
} from "./api";


afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});


describe("server API client", () => {

  it("restricts both public discovery APIs to German member content", async () => {
    const fetchMock = vi.fn().mockImplementation(
      async () => new Response(JSON.stringify({
        items: [], total: 0, page: 1, page_size: 20, pages: 0,
      }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await searchArticles({ q: "Berlin" });
    await listStories({ page: 1, minSources: 2 });

    const urls = fetchMock.mock.calls.map(([url]) => new URL(String(url)));
    expect(urls.map((url) => url.pathname)).toEqual(["/search", "/stories"]);
    expect(urls.every((url) => url.searchParams.get("language") === "de")).toBe(true);
    expect(urls[1].searchParams.get("min_sources")).toBe("2");
  });
  it(
    "sends a correlation ID to FastAPI",
    async () => {
      const fetchMock = vi.fn(
        async (
          _input: RequestInfo | URL,
          _init?: RequestInit,
        ) => new Response(
          JSON.stringify({
            items: [],
            total: 0,
            page: 1,
            page_size: 20,
            pages: 0,
          }),
          {
            status: 200,
            headers: {
              "Content-Type": "application/json",
              "X-Request-ID": "backend-request-id",
            },
          },
        ),
      );
      vi.stubGlobal(
        "fetch",
        fetchMock,
      );

      await searchArticles({
        q: "test",
      });

      const init = (
        fetchMock.mock.calls[0]?.[1]
      );
      if (!init) {
        throw new Error(
          "fetch init missing",
        );
      }
      const headers = new Headers(
        init.headers,
      );
      expect(
        headers.get("X-Request-ID"),
      ).toMatch(
        /^[0-9a-f-]{36}$/,
      );
    },
  );

  it(
    "turns a backend timeout into a correlated API error",
    async () => {
      const timeout = new Error(
        "timed out",
      );
      timeout.name = "TimeoutError";
      vi.stubGlobal(
        "fetch",
        vi.fn().mockRejectedValue(
          timeout,
        ),
      );
      const consoleError = vi
        .spyOn(
          console,
          "error",
        )
        .mockImplementation(
          () => undefined,
        );

      let captured: unknown;
      try {
        await searchArticles({
          q: "private search text",
        });
      } catch (error) {
        captured = error;
      }

      expect(
        captured,
      ).toBeInstanceOf(
        ApiError,
      );
      expect(
        captured,
      ).toMatchObject({
        status: 504,
        message: (
          "Backend-Zeitüberschreitung."
        ),
      });

      const rawLog = (
        consoleError.mock.calls[0]?.[0]
      );
      if (
        typeof rawLog !== "string"
      ) {
        throw new Error(
          "structured log missing",
        );
      }
      const log = JSON.parse(
        rawLog,
      );
      expect(
        log.event,
      ).toBe(
        "frontend_api_error",
      );
      expect(
        log.path,
      ).toBe(
        "/search",
      );
      expect(
        JSON.stringify(log),
      ).not.toContain(
        "private search text",
      );
      expect(
        log.request_id,
      ).toMatch(
        /^[0-9a-f-]{36}$/,
      );
    },
  );
});
