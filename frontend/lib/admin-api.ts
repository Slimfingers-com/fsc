import "server-only";

import type { ProvenanceReviewPage, ProvenanceReviewStatus } from "./types";

const API_URL = (process.env.FSC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

function adminKey(): string {
  const value = process.env.SOURCE_ADMIN_API_KEY?.trim();
  if (!value) throw new Error("SOURCE_ADMIN_API_KEY is not configured for frontend");
  return value;
}

async function adminRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-FSC-Admin-Key": adminKey(),
      ...init?.headers,
    },
  });
  if (!response.ok) throw new Error(`Admin backend request failed: HTTP ${response.status}`);
  return await response.json() as T;
}

export async function listProvenanceReviewQueue(
  status: ProvenanceReviewStatus,
  offset: number,
  limit = 25,
): Promise<ProvenanceReviewPage> {
  const params = new URLSearchParams({
    review_status: status,
    offset: String(offset),
    limit: String(limit),
  });
  return adminRequest<ProvenanceReviewPage>(
    `/article-provenance/review-queue?${params.toString()}`,
  );
}

export async function updateProvenanceReview(
  articleId: string,
  provenanceId: string,
  reviewStatus: ProvenanceReviewStatus,
): Promise<void> {
  await adminRequest(
    `/articles/${encodeURIComponent(articleId)}/provenance/${encodeURIComponent(provenanceId)}`,
    {
      method: "PATCH",
      body: JSON.stringify({ review_status: reviewStatus }),
    },
  );
}
