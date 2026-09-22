import {
  afterEach,
  describe,
  expect,
  it,
  vi,
} from "vitest";

import {
  ApiError,
  searchArticles,
} from "./api";


afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});


describe("server API client", () => {
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

      const log = JSON.parse(
        consoleError.mock.calls[0]?.[0]
        as string,
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
