<template>
  <div class="flex-1 bg-white text-slate-900 dark:bg-slate-950 dark:text-white">
    <main>
      <!-- Hero -->
      <section class="mx-auto grid max-w-6xl items-center gap-10 px-4 pb-16 pt-12 md:grid-cols-2 md:px-8 md:pt-20">
        <div>
          <p class="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-300">
            <span class="size-2 rounded-full bg-emerald-500" aria-hidden="true"></span>
            {{ t("landing.badge") }}
          </p>
          <h1 class="mt-4 text-4xl font-extrabold tracking-tight md:text-5xl">
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
        <LiveDemo />
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
              <p class="flex size-10 items-center justify-center rounded-2xl bg-slate-900 text-base font-bold text-white dark:bg-emerald-500 dark:text-slate-950" aria-hidden="true">
                {{ step.number }}
              </p>
              <h3 class="mt-4 font-bold">{{ step.title }}</h3>
              <p class="mt-1 text-sm text-slate-600 dark:text-slate-300">{{ step.text }}</p>
            </li>
          </ol>
        </div>
      </section>

      <!-- Features -->
      <section id="features" class="mx-auto max-w-6xl px-4 py-16 md:px-8" :aria-label="t('landing.featuresLabel')">
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
            <p class="text-2xl" aria-hidden="true">{{ feature.icon }}</p>
            <h3 class="mt-3 font-bold">{{ feature.title }}</h3>
            <p class="mt-1 text-sm text-slate-600 dark:text-slate-300">{{ feature.text }}</p>
          </li>
        </ul>
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
import LiveDemo from "../components/landing/LiveDemo.vue";
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

const features = computed(() => [
  {
    icon: "🎙️",
    title: t("landing.features.f1.title"),
    text: t("landing.features.f1.text"),
  },
  {
    icon: "🎨",
    title: t("landing.features.f2.title"),
    text: t("landing.features.f2.text"),
  },
  {
    icon: "🌈",
    title: t("landing.features.f3.title"),
    text: t("landing.features.f3.text"),
  },
  {
    icon: "🧹",
    title: t("landing.features.f4.title"),
    text: t("landing.features.f4.text"),
  },
  {
    icon: "🖼️",
    title: t("landing.features.f5.title"),
    text: t("landing.features.f5.text"),
  },
  {
    icon: "💻",
    title: t("landing.features.f6.title"),
    text: t("landing.features.f6.text"),
  },
]);
</script>
