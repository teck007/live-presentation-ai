import type { App } from "vue";
import { useAuth } from "@clerk/vue";

// Publishable key (public, safe for frontend). Never put the secret here.
const RAW_KEY = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
export const CLERK_PUBLISHABLE_KEY =
  typeof RAW_KEY === "string" ? RAW_KEY.trim() : "";
export const isClerkConfigured = CLERK_PUBLISHABLE_KEY.length > 0;

let appInstance: App | null = null;

/** Called once in main.ts so router guards can use Clerk outside setup(). */
export function registerApp(app: App): void {
  appInstance = app;
}

type AuthState = ReturnType<typeof useAuth>;
let cachedAuth: AuthState | null = null;

/**
 * Safe Clerk auth accessor. Works in setup() and in router guards
 * (via app.runWithContext). Returns null when Clerk is not configured
 * (dev without env) or the plugin failed to install.
 */
export function getAuth(): AuthState | null {
  if (!isClerkConfigured) return null;
  if (cachedAuth) return cachedAuth;
  try {
    cachedAuth = appInstance
      ? appInstance.runWithContext(() => useAuth())
      : useAuth();
  } catch {
    cachedAuth = null;
  }
  return cachedAuth;
}

/**
 * Waits until Clerk finishes loading (session restored). Resolves null
 * when Clerk is not configured or still unloaded after the timeout.
 */
export async function waitForClerkLoad(
  timeoutMs = 8000,
): Promise<AuthState | null> {
  const auth = getAuth();
  if (!auth) return null;
  if (auth.isLoaded.value) return auth;
  const start = Date.now();
  while (!auth.isLoaded.value && Date.now() - start < timeoutMs) {
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  return auth.isLoaded.value ? auth : null;
}
