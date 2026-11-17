import { NextResponse } from "next/server";

// Public monitoring must also check a live, uncached backend dependency.
// A recently cached news list must not conceal a sustained API outage.
export const dynamic = "force-dynamic";

const API_URL = (
  process.env.FSC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

const NO_CACHE_HEADERS = { "Cache-Control": "no-store, max-age=0" };

export async function GET() {
  try {
    const response = await fetch(`${API_URL}/health/ready`, {
      cache: "no-store",
      signal: AbortSignal.timeout(4_000),
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      throw new Error("Backend readiness check failed");
    }
    const status = (await response.json()) as { status?: string };
    if (status.status !== "ready") {
      throw new Error("Backend is not ready");
    }
    return NextResponse.json(
      { status: "ready" },
      { headers: NO_CACHE_HEADERS },
    );
  } catch {
    // Do not disclose internal addresses, database details or exceptions.
    return NextResponse.json(
      { status: "unavailable" },
      { status: 503, headers: NO_CACHE_HEADERS },
    );
  }
}
