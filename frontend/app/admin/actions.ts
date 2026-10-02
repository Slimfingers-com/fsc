"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import { hasAdminSession } from "@/lib/admin-auth";
import { updateProvenanceReview } from "@/lib/admin-api";

export async function reviewProvenance(formData: FormData) {
  if (!(await hasAdminSession())) redirect("/admin/login");
  const articleId = formData.get("article_id");
  const provenanceId = formData.get("provenance_id");
  const status = formData.get("review_status");
  if (
    typeof articleId !== "string"
    || typeof provenanceId !== "string"
    || (status !== "pending" && status !== "verified" && status !== "rejected")
  ) {
    throw new Error("Invalid provenance review action");
  }
  await updateProvenanceReview(articleId, provenanceId, status);
  revalidatePath("/admin/provenance");
}
