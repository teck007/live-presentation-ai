<template>
  <div class="flex-1 bg-white text-slate-900 dark:bg-slate-950 dark:text-white">
    <main class="mx-auto grid max-w-6xl gap-8 px-4 py-16 md:grid-cols-2 md:px-8">
      <div>
        <p
          class="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-xs font-semibold text-slate-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-300"
        >
          <span class="size-2 rounded-full bg-amber-500" aria-hidden="true"></span>
          {{ t("trial.badge") }}
        </p>
        <h1 class="mt-4 text-3xl font-extrabold tracking-tight md:text-4xl">
          {{ t("trial.title") }}
        </h1>
        <p class="mt-4 max-w-md text-slate-600 dark:text-slate-300">
          {{ t("trial.text") }}
        </p>
        <RouterLink
          to="/"
          class="mt-6 inline-block rounded-xl border border-slate-300 px-5 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 dark:border-white/15 dark:text-slate-200 dark:hover:bg-white/10"
        >
          {{ t("auth.backHome") }}
        </RouterLink>
      </div>
      <div>
        <ContactForm />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n";
import ContactForm from "../components/landing/ContactForm.vue";

const { t } = useI18n({ useScope: "global" });
</script>
