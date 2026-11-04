import { createRouter, createWebHistory } from "vue-router";
import { isClerkConfigured, waitForClerkLoad } from "../lib/clerk";
import { AuthRequiredError, fetchTrialStatus } from "../api/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "landing",
      component: () => import("../views/LandingView.vue"),
      meta: { showNavLinks: "landing" },
    },
    {
      path: "/live",
      name: "live",
      component: () => import("../views/LiveView.vue"),
      meta: { showNavLinks: "live" },
    },
    {
      path: "/sign-in",
      name: "sign-in",
      component: () => import("../views/SignInView.vue"),
      meta: { showNavLinks: "minimal" },
    },
    {
      path: "/sign-up",
      name: "sign-up",
      component: () => import("../views/SignUpView.vue"),
      meta: { showNavLinks: "minimal" },
    },
    {
      path: "/trial-expired",
      name: "trial-expired",
      component: () => import("../views/TrialExpiredView.vue"),
      meta: { showNavLinks: "minimal" },
    },
  ],
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) return savedPosition;
    // Anchor links from the persistent navbar (RouterLink with hash).
    if (to.hash) return { el: to.hash };
    return { top: 0 };
  },
});

// /live needs sign-in + active 24h trial. /trial-expired has no guard
// (it is the dead-end: no redirect loop possible).
router.beforeEach(async (to) => {
  if (to.name !== "live") return true;
  if (!isClerkConfigured) {
    console.warn("[auth] Clerk key missing: /live open in dev (fail-open).");
    return true;
  }
  const auth = await waitForClerkLoad();
  if (!auth || !auth.isSignedIn.value) {
    return { name: "sign-in", query: { redirect: to.fullPath } };
  }
  try {
    const status = await fetchTrialStatus(() => auth.getToken.value());
    if (!status.active) return { name: "trial-expired" };
    return true;
  } catch (error) {
    // Invalid session -> sign in again. Any other failure (network, 5xx)
    // fails open: the backend still enforces auth+trial per request.
    if (error instanceof AuthRequiredError) {
      return { name: "sign-in", query: { redirect: to.fullPath } };
    }
    console.error("[auth] trial status check failed:", error);
    return true;
  }
});

export default router;
