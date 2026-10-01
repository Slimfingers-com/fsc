"use server";

import { redirect } from "next/navigation";
import { revalidatePath } from "next/cache";
import {
  clearAdminSession,
  hasAdminSession,
  setAdminSession,
  verifyAdminPassword,
} from "@/lib/admin-auth";
import { updateProvenanceReview } from "@/lib/admin-api";

export async function loginAdmin(formData: FormData) {
  const password = formData.get("password");
  if (typeof password !== "string" || !verifyAdminPassword(password)) {
    redirect("/admin/login?error=1");
  }
  await setAdminSession();
  redirect("/admin/provenance");
}

export async function logoutAdmin() {
  await clearAdminSession();
  redirect("/admin/login");
}

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
