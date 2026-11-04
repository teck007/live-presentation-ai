<template>
  <div class="flex flex-1 items-center justify-center bg-white px-4 py-12 text-slate-900 dark:bg-slate-950 dark:text-white">
    <main class="w-full max-w-md text-center">
      <RouterLink
        to="/"
        class="text-sm font-medium text-slate-500 transition hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
      >
        {{ t("auth.backHome") }}
      </RouterLink>
      <h1 class="mt-4 text-2xl font-extrabold tracking-tight">{{ t("auth.signUpTitle") }}</h1>
      <p class="mt-2 text-sm text-slate-600 dark:text-slate-300">
        {{ t("auth.signUpSubtitle") }}
      </p>
      <div class="mt-6 flex justify-center">
        <SignUp
          v-if="isClerkConfigured"
          sign-in-url="/sign-in"
          :force-redirect-url="redirectUrl"
        />
        <p
          v-else
          class="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200"
          role="status"
        >
          {{ t("auth.devNoAuth") }}
        </p>
      </div>
      <p class="mt-6 text-sm text-slate-500 dark:text-slate-400">
        {{ t("auth.hasAccount") }}
        <RouterLink to="/sign-in" class="font-semibold text-slate-900 underline dark:text-white">
          {{ t("auth.signInTitle") }}
        </RouterLink>
      </p>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { SignUp } from "@clerk/vue";
import { getAuth, isClerkConfigured } from "../lib/clerk";

const { t } = useI18n({ useScope: "global" });
const route = useRoute();
const router = useRouter();

// Honor the guard's ?redirect= when it is a safe internal path.
const redirectUrl = computed(() => {
  const raw = route.query.redirect;
  if (typeof raw === "string" && raw.startsWith("/") && !raw.startsWith("//")) {
    return raw;
  }
  return "/live";
});

const auth = getAuth();
// Already signed in: skip the form.
watch(
  () => auth?.isSignedIn.value,
  (signedIn) => {
    if (signedIn) void router.replace(redirectUrl.value);
  },
  { immediate: true },
);
</script>
