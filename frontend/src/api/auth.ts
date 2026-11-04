/**
 * Auth helpers for protected backend calls (Clerk JWT + 24h trial).
 * The UI never sees expires_at: only { active } leaves this module.
 */

const RAW_BASE = import.meta.env.VITE_API_BASE_URL;
export const API_BASE_URL =
  typeof RAW_BASE === "string" && RAW_BASE.trim()
    ? RAW_BASE.trim()
    : "http://localhost:8000";

export type GetTokenFn = () => Promise<string | null>;

/** Backend answered 401: missing/invalid session, user must sign in. */
export class AuthRequiredError extends Error {
  readonly status = 401;
  constructor(
    message = "Tu sesión expiró o es inválida. Iniciá sesión de nuevo.",
  ) {
    super(message);
    this.name = "AuthRequiredError";
  }
}

/** Backend answered 403: the 24h trial ended. Never leaks expires_at. */
export class TrialExpiredError extends Error {
  readonly status = 403;
  constructor(
    message = "Tu prueba de 24 horas finalizó. Escribinos y la extendemos.",
  ) {
    super(message);
    this.name = "TrialExpiredError";
  }
}

/** Authorization header for a fresh Clerk token (empty when signed out). */
export async function authHeaders(
  getToken?: GetTokenFn,
): Promise<Record<string, string>> {
  if (!getToken) return {};
  try {
    const token = await getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

/** Maps HTTP auth statuses to typed errors (generic messages, no leaks). */
export function throwForAuthStatus(status: number): void {
  if (status === 401) throw new AuthRequiredError();
  if (status === 403) throw new TrialExpiredError();
}

export interface TrialStatus {
  active: boolean;
}

/**
 * GET /api/trial/status with Bearer token.
 * 401 -> AuthRequiredError (must sign in). Other failures -> Error.
 */
export async function fetchTrialStatus(
  getToken?: GetTokenFn,
): Promise<TrialStatus> {
  const response = await fetch(`${API_BASE_URL}/api/trial/status`, {
    headers: await authHeaders(getToken),
  });
  if (response.status === 401) throw new AuthRequiredError();
  if (!response.ok) throw new Error(`Error ${response.status}`);
  const data = (await response.json()) as { active?: unknown };
  return { active: data.active === true };
}
