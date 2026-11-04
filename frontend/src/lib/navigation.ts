import { computed, type ComputedRef } from "vue";
import { getAuth, isClerkConfigured } from "./clerk";

/**
 * Single source of truth for "where does Probar en vivo / Try it live go?".
 * Signed in -> studio. Signed out -> sign up first (the /live guard would
 * bounce back). Dev without Clerk key -> studio (fail-open, same as guard).
 */
export function useLiveTarget(): ComputedRef<string> {
  const auth = getAuth();
  return computed(() =>
    auth?.isSignedIn.value || !isClerkConfigured ? "/live" : "/sign-up",
  );
}

/** Non-reactive snapshot for contexts without setup() (same rule). */
export function liveTargetSnapshot(): string {
  const auth = getAuth();
  const signedIn = auth?.isSignedIn.value === true;
  return signedIn || !isClerkConfigured ? "/live" : "/sign-up";
}
