<template>
  <header class="sticky top-0 z-50 border-b border-slate-200 bg-white/80 backdrop-blur dark:border-white/10 dark:bg-slate-950/80">
    <nav class="mx-auto flex h-16 max-w-6xl items-center gap-4 px-4 md:px-8" :aria-label="t('nav.main')">
      <RouterLink to="/" class="flex items-center gap-2 font-bold tracking-tight text-slate-900 dark:text-white">
        <span class="flex size-8 items-center justify-center rounded-xl bg-emerald-500 text-lg text-white" aria-hidden="true">◉</span>
        <span>{{ t("nav.brand") }}</span>
      </RouterLink>
      <div v-if="variant === 'landing'" class="ml-6 hidden items-center gap-6 text-sm font-medium text-slate-600 md:flex dark:text-slate-300">
        <RouterLink :to="{ path: '/', hash: '#como-funciona' }" class="transition hover:text-slate-900 dark:hover:text-white">
          {{ t("nav.howItWorks") }}
        </RouterLink>
        <RouterLink :to="{ path: '/', hash: '#features' }" class="transition hover:text-slate-900 dark:hover:text-white">
          {{ t("nav.features") }}
        </RouterLink>
        <RouterLink :to="{ path: '/', hash: '#faq' }" class="transition hover:text-slate-900 dark:hover:text-white">
          {{ t("nav.faq") }}
        </RouterLink>
        <RouterLink :to="{ path: '/', hash: '#contacto' }" class="transition hover:text-slate-900 dark:hover:text-white">
          {{ t("nav.contact") }}
        </RouterLink>
      </div>
      <div v-else-if="variant === 'live'" class="ml-6 hidden items-center gap-6 text-sm font-medium text-slate-600 md:flex dark:text-slate-300">
        <RouterLink to="/" class="transition hover:text-slate-900 dark:hover:text-white">
          {{ t("nav.home") }}
        </RouterLink>
        <span
          v-if="statusLabel"
          class="rounded-full px-3 py-1 text-xs font-medium"
          :class="statusPillClass"
          role="status"
        >
          {{ statusLabel }}
        </span>
      </div>
      <div class="ml-auto flex items-center gap-2">
        <LanguageSwitcher />
        <ThemeToggle />
        <template v-if="!isClerkConfigured">
          <RouterLink
            :to="liveTarget"
            class="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 dark:bg-emerald-500 dark:text-slate-950 dark:hover:bg-emerald-400"
          >
            {{ t("nav.tryLive") }}
          </RouterLink>
        </template>
        <template v-else-if="signedIn">
          <UserButton />
        </template>
        <template v-else>
          <RouterLink
            to="/sign-in"
            class="hidden rounded-xl px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 sm:inline-block dark:text-slate-200 dark:hover:bg-white/10"
          >
            {{ t("nav.signIn") }}
          </RouterLink>
          <RouterLink
            :to="liveTarget"
            class="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700 dark:bg-emerald-500 dark:text-slate-950 dark:hover:bg-emerald-400"
          >
            {{ t("nav.tryLive") }}
          </RouterLink>
        </template>
      </div>
    </nav>
  </header>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RouterLink, useRoute } from "vue-router";
import { useI18n } from "vue-i18n";
import { UserButton } from "@clerk/vue";
import LanguageSwitcher from "./LanguageSwitcher.vue";
import ThemeToggle from "./ThemeToggle.vue";
import { getAuth, isClerkConfigured } from "../lib/clerk";
import { useLiveTarget } from "../lib/navigation";

// Persistent navbar: single unified logo (the ◉ variant), contextual links
// from route.meta.showNavLinks ('landing' | 'live' | 'minimal'), theme +
// language controls, and Clerk auth (graceful without a publishable key).
// UserButton is statically imported but only rendered when Clerk is
// configured and the user is signed in, so dev without key never breaks.
withDefaults(
  defineProps<{
    statusLabel?: string;
    statusPillClass?: string;
  }>(),
  { statusLabel: "", statusPillClass: "" },
);

const { t } = useI18n({ useScope: "global" });
const route = useRoute();
const variant = computed(() => {
  const meta = route.meta.showNavLinks;
  return meta === "landing" || meta === "live" ? meta : "minimal";
});

const auth = getAuth();
const signedIn = computed(() => auth?.isSignedIn.value === true);
const liveTarget = useLiveTarget();
</script>
