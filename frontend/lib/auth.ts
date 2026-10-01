import "server-only";

import type { NextAuthOptions } from "next-auth";

function required(name: "ZITADEL_ISSUER" | "ZITADEL_CLIENT_ID" | "ZITADEL_CLIENT_SECRET"): string {
  const value = process.env[name]?.trim();
  if (!value) throw new Error(`${name} is not configured`);
  return value;
}

export const authOptions: NextAuthOptions = {
  secret: process.env.NEXTAUTH_SECRET,
  session: { strategy: "jwt", maxAge: 8 * 60 * 60 },
  providers: [
    {
      id: "zitadel",
      name: "ZITADEL",
      type: "oauth",
      wellKnown: `${process.env.ZITADEL_ISSUER ?? "https://invalid.example"}/.well-known/openid-configuration`,
      clientId: process.env.ZITADEL_CLIENT_ID ?? "unconfigured",
      clientSecret: process.env.ZITADEL_CLIENT_SECRET ?? "unconfigured",
      authorization: { params: { scope: "openid email profile" } },
      idToken: true,
      checks: ["pkce", "state"],
      profile(profile) {
        return {
          id: profile.sub,
          name: profile.name ?? profile.preferred_username ?? profile.email,
          email: profile.email,
          image: profile.picture,
        };
      },
    },
  ],
  pages: { signIn: "/admin/login" },
  callbacks: {
    async signIn({ user }) {
      const allowed = process.env.FSC_ADMIN_EMAIL?.trim().toLowerCase();
      return Boolean(allowed && user.email?.toLowerCase() === allowed);
    },
    async session({ session, token }) {
      if (session.user) session.user.email = token.email ?? session.user.email;
      return session;
    },
  },
};