import "server-only";

import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";

export async function hasAdminSession(): Promise<boolean> {
  const session = await getServerSession(authOptions);
  const allowed = process.env.FSC_ADMIN_EMAIL?.trim().toLowerCase();
  return Boolean(allowed && session?.user?.email?.toLowerCase() === allowed);
}
