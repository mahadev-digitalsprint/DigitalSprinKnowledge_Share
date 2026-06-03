"use client";

export type UserRole = "admin" | "employee";

export type FrontendAuthContext = {
  userId: string;
  role: UserRole;
  collections: string[];
  token?: string;
  email?: string;
  fullName?: string;
};

export const RBAC_STORAGE_KEY = "rag-ui-rbac";

const DEFAULT_AUTH: FrontendAuthContext = {
  userId: "local-dev-user",
  role: "admin",
  collections: ["*"],
};

export function loadAuthContext(): FrontendAuthContext {
  if (typeof window === "undefined") return DEFAULT_AUTH;
  try {
    const raw = window.localStorage.getItem(RBAC_STORAGE_KEY);
    if (!raw) return DEFAULT_AUTH;
    const parsed = JSON.parse(raw) as Partial<FrontendAuthContext>;
    const role: UserRole = parsed.role === "employee" ? "employee" : "admin";
    const userId = parsed.userId?.trim() || DEFAULT_AUTH.userId;
    const collections = Array.isArray(parsed.collections) && parsed.collections.length > 0
      ? parsed.collections
      : DEFAULT_AUTH.collections;
    return { userId, role, collections };
  } catch {
    return DEFAULT_AUTH;
  }
}

export function saveAuthContext(auth: FrontendAuthContext): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(RBAC_STORAGE_KEY, JSON.stringify(auth));
}

export function buildAuthHeaders(auth: FrontendAuthContext): Record<string, string> {
  const headers: Record<string, string> = {
    "x-user-id": auth.userId,
    "x-user-role": auth.role,
    "x-user-collections": auth.collections.join(","),
  };
  if (auth.token) headers.authorization = `Bearer ${auth.token}`;
  return headers;
}

export function buildAuthQuery(auth: FrontendAuthContext): string {
  const params = new URLSearchParams();
  params.set("user_id", auth.userId);
  params.set("user_role", auth.role);
  params.set("user_collections", auth.collections.join(","));
  return params.toString();
}
