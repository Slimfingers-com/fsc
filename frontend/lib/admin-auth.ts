import "server-only";

import { createHmac, randomBytes, timingSafeEqual } from "node:crypto";
import { cookies } from "next/headers";

const COOKIE_NAME = "fsc_admin_session";
const SESSION_TTL_SECONDS = 8 * 60 * 60;

function secret(name: "FSC_ADMIN_PASSWORD" | "FSC_ADMIN_SESSION_SECRET"): string {
  const value = process.env[name]?.trim();
  if (!value) {
    throw new Error(`${name} is not configured`);
  }
  return value;
}

function equalText(left: string, right: string): boolean {
  const a = Buffer.from(left);
  const b = Buffer.from(right);
  return a.length === b.length && timingSafeEqual(a, b);
}

function sign(payload: string): string {
  return createHmac("sha256", secret("FSC_ADMIN_SESSION_SECRET"))
    .update(payload)
    .digest("base64url");
}

export function verifyAdminPassword(candidate: string): boolean {
  return equalText(candidate, secret("FSC_ADMIN_PASSWORD"));
}

export function createAdminSessionToken(now = Date.now()): string {
  const expiresAt = Math.floor(now / 1000) + SESSION_TTL_SECONDS;
  const payload = `${expiresAt}.${randomBytes(24).toString("base64url")}`;
  return `${payload}.${sign(payload)}`;
}

export function verifyAdminSessionToken(token: string | undefined, now = Date.now()): boolean {
  if (!token) return false;
  const parts = token.split(".");
  if (parts.length !== 3) return false;
  const [expiresRaw, nonce, signature] = parts;
  const expiresAt = Number.parseInt(expiresRaw, 10);
  if (!Number.isSafeInteger(expiresAt) || expiresAt <= Math.floor(now / 1000) || !nonce) {
    return false;
  }
  return equalText(signature, sign(`${expiresRaw}.${nonce}`));
}

export async function hasAdminSession(): Promise<boolean> {
  const store = await cookies();
  return verifyAdminSessionToken(store.get(COOKIE_NAME)?.value);
}

export async function setAdminSession(): Promise<void> {
  const store = await cookies();
  store.set(COOKIE_NAME, createAdminSessionToken(), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    path: "/",
    maxAge: SESSION_TTL_SECONDS,
  });
}

export async function clearAdminSession(): Promise<void> {
  const store = await cookies();
  store.delete(COOKIE_NAME);
}
