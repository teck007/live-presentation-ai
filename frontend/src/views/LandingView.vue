<template>
  <div class="flex-1 bg-white text-slate-900 dark:bg-slate-950 dark:text-white">
    <main>
      <!-- Hero -->
      <section class="mx-auto grid max-w-6xl items-center gap-10 px-4 pb-16 pt-12 md:grid-cols-12 md:px-8 md:pt-20">
        <div class="md:col-span-5">
          <p class="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-300">
            <span class="size-2 rounded-full bg-emerald-500" aria-hidden="true"></span>
            {{ t("landing.badge") }}
          </p>
          <h1 class="mt-4 text-5xl font-extrabold tracking-tight md:text-6xl">
            {{ t("landing.heroTitle") }}
          </h1>
          <p class="mt-4 max-w-lg text-lg text-slate-600 dark:text-slate-300">
            {{ t("landing.heroSubtitle") }}
          </p>
          <div class="mt-6 flex flex-wrap gap-3">
            <RouterLink
              :to="liveTarget"
              class="rounded-xl bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-700 dark:bg-emerald-500 dark:text-slate-950 dark:hover:bg-emerald-400"
            >
              {{ t("landing.createCta") }}
            </RouterLink>
            <RouterLink
              :to="{ path: '/', hash: '#como-funciona' }"
              class="rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 dark:border-white/15 dark:text-slate-200 dark:hover:bg-white/10"
            >
              {{ t("landing.seeHow") }}
            </RouterLink>
          </div>
        </div>
        <div class="md:col-span-7">
          <ExamplePresentation />
        </div>
      </section>

      <!-- Steps -->
      <section id="como-funciona" class="border-y border-slate-200 bg-slate-50 dark:border-white/10 dark:bg-slate-900/50" :aria-label="t('landing.stepsLabel')">
        <div class="mx-auto max-w-6xl px-4 py-16 md:px-8">
          <h2 class="text-center text-2xl font-bold tracking-tight md:text-3xl">{{ t("landing.stepsTitle") }}</h2>
          <p class="mx-auto mt-2 max-w-xl text-center text-slate-600 dark:text-slate-300">
            {{ t("landing.stepsSubtitle") }}
          </p>
          <ol class="mt-10 grid gap-6 md:grid-cols-3">
            <li
              v-for="step in steps"
              :key="step.title"
              class="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-slate-900"
            >
              <p class="flex size-10 items-center justify-center rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-600 text-base font-extrabold text-white shadow-md shadow-emerald-500/20" aria-hidden="true">
                {{ step.number }}
              </p>
              <h3 class="mt-4 font-bold">{{ step.title }}</h3>
              <p class="mt-1 text-sm text-slate-600 dark:text-slate-300">{{ step.text }}</p>
            </li>
          </ol>
        </div>
      </section>

      <!-- Features -->
      <section id="features" class="border-y border-slate-200 bg-slate-50 dark:border-white/10 dark:bg-slate-900/50" :aria-label="t('landing.featuresLabel')">
        <div class="mx-auto max-w-6xl px-4 py-16 md:px-8">
          <h2 class="text-center text-2xl font-bold tracking-tight md:text-3xl">{{ t("landing.featuresTitle") }}</h2>
          <p class="mx-auto mt-2 max-w-xl text-center text-slate-600 dark:text-slate-300">
            {{ t("landing.featuresSubtitle") }}
          </p>
          <ul class="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <li
              v-for="feature in features"
              :key="feature.title"
              class="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-slate-900"
            >
              <span class="flex size-11 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" aria-hidden="true">
                <svg class="size-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path :d="feature.iconPath" /></svg>
              </span>
              <h3 class="mt-3 font-bold">{{ feature.title }}</h3>
              <p class="mt-1 text-sm text-slate-600 dark:text-slate-300">{{ feature.text }}</p>
            </li>
          </ul>
        </div>
      </section>

      <!-- FAQ -->
      <section id="faq" class="mx-auto max-w-3xl px-4 py-16 md:px-8" :aria-label="t('landing.faq.label')">
        <p class="text-center text-xs font-semibold uppercase tracking-widest text-emerald-600 dark:text-emerald-400">
          {{ t("landing.faq.label") }}
        </p>
        <h2 class="mt-2 text-center text-2xl font-bold tracking-tight md:text-3xl">{{ t("landing.faq.title") }}</h2>
        <p class="mx-auto mt-2 max-w-xl text-center text-slate-600 dark:text-slate-300">
          {{ t("landing.faq.subtitle") }}
        </p>
        <div class="mt-8 space-y-3">
          <details
            v-for="item in faqs"
            :key="item.q"
            class="group rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm dark:border-white/10 dark:bg-slate-900"
          >
            <summary class="cursor-pointer list-none font-semibold marker:hidden [&::-webkit-details-marker]:hidden">
              <span class="flex items-center justify-between gap-4">
                {{ item.q }}
                <svg class="size-5 shrink-0 text-slate-400 transition-transform group-open:rotate-180" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"><path d="M5.3 7.3 10 12l4.7-4.7 1.4 1.4L10 14.8 3.9 8.7z" /></svg>
              </span>
            </summary>
            <p class="mt-2 text-sm text-slate-600 dark:text-slate-300">{{ item.a }}</p>
          </details>
        </div>
      </section>

      <!-- Final CTA -->
      <section class="border-t border-slate-200 dark:border-white/10" :aria-label="t('landing.ctaLabel')">
        <div class="mx-auto max-w-6xl px-4 py-16 text-center md:px-8">
          <h2 class="text-2xl font-bold tracking-tight md:text-3xl">{{ t("landing.ctaTitle") }}</h2>
          <p class="mx-auto mt-2 max-w-xl text-slate-600 dark:text-slate-300">
            {{ t("landing.ctaText") }}
          </p>
          <RouterLink
            :to="liveTarget"
            class="mt-6 inline-block rounded-xl bg-slate-900 px-6 py-3 text-sm font-semibold text-white transition hover:bg-slate-700 dark:bg-emerald-500 dark:text-slate-950 dark:hover:bg-emerald-400"
          >
            {{ t("landing.ctaButton") }}
          </RouterLink>
        </div>
      </section>

      <!-- Contact -->
      <section id="contacto" class="border-t border-slate-200 bg-slate-50 dark:border-white/10 dark:bg-slate-900/50" :aria-label="t('nav.contact')">
        <div class="mx-auto grid max-w-6xl gap-8 px-4 py-16 md:grid-cols-2 md:px-8">
          <div>
            <h2 class="text-2xl font-bold tracking-tight md:text-3xl">{{ t("landing.contactTitle") }}</h2>
            <p class="mt-2 max-w-md text-slate-600 dark:text-slate-300">
              {{ t("landing.contactText") }}
            </p>
          </div>
          <ContactForm />
        </div>
      </section>
    </main>

    <LandingFooter />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import { useI18n } from "vue-i18n";
import ContactForm from "../components/landing/ContactForm.vue";
import LandingFooter from "../components/landing/LandingFooter.vue";
import ExamplePresentation from "../components/landing/ExamplePresentation.vue";
import { useLiveTarget } from "../lib/navigation";

const { t } = useI18n({ useScope: "global" });

// Signed in -> studio. Signed out -> sign up first (guard would bounce).
// Dev without Clerk key -> studio (fail-open, same as the /live guard).
const liveTarget = useLiveTarget();

// Catalog-driven content: icons live here, copy lives in locales (es/en)
// so the language switch re-renders without reload.
const steps = computed(() => [
  {
    number: "1",
    title: t("landing.steps.s1.title"),
    text: t("landing.steps.s1.text"),
  },
  {
    number: "2",
    title: t("landing.steps.s2.title"),
    text: t("landing.steps.s2.text"),
  },
  {
    number: "3",
    title: t("landing.steps.s3.title"),
    text: t("landing.steps.s3.text"),
  },
]);

// Simple stroke icons (currentColor): mic, layouts grid, palette,
// shield filter, image sparkles, browser monitor.
const features = computed(() => [
  {
    iconPath: "M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3Z M19 10v2a7 7 0 0 1-14 0v-2 M12 19v4 M8 23h8",
    title: t("landing.features.f1.title"),
    text: t("landing.features.f1.text"),
  },
  {
    iconPath: "M3 3h7v7H3Z M14 3h7v7h-7Z M14 14h7v7h-7Z M3 14h7v7H3Z",
    title: t("landing.features.f2.title"),
    text: t("landing.features.f2.text"),
  },
  {
    iconPath: "M12 2a10 10 0 1 0 0 20c1.6 0 2.5-1 2.5-2.2 0-1.6 1.2-2.3 2.5-2.3h1.8a3.7 3.7 0 0 0 3.7-3.7C22.5 7 17.5 2 12 2Z M7.5 10.5h.01 M11 7.5h.01 M15.5 8.5h.01",
    title: t("landing.features.f3.title"),
    text: t("landing.features.f3.text"),
  },
  {
    iconPath: "M12 2 4 5v6c0 5 3.5 8.6 8 11 4.5-2.4 8-6 8-11V5Z M9 11.5l2 2 4-4.5",
    title: t("landing.features.f4.title"),
    text: t("landing.features.f4.text"),
  },
  {
    iconPath: "M3 5h18v14H3Z M8.5 10h.01 M3 17l5-5 4 4 3-3 6 6",
    title: t("landing.features.f5.title"),
    text: t("landing.features.f5.text"),
  },
  {
    iconPath: "M3 4h18v12H3Z M8 20h8 M12 16v4",
    title: t("landing.features.f6.title"),
    text: t("landing.features.f6.text"),
  },
]);

const faqs = computed(() => [1, 2, 3, 4, 5, 6].map((n) => ({
  q: t(`landing.faq.q${n}`),
  a: t(`landing.faq.a${n}`),
})));
</script>
