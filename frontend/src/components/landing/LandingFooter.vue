<template>
  <footer class="border-t border-slate-200 dark:border-white/10">
    <div class="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 py-8 text-sm text-slate-500 md:flex-row md:px-8 dark:text-slate-400">
      <p>{{ t("landing.footerRights", { year }) }}</p>
      <nav class="flex items-center gap-5" :aria-label="t('landing.footerLegal')">
        <a href="#" class="transition hover:text-slate-900 dark:hover:text-white">{{ t("landing.footerTerms") }}</a>
        <a href="#" class="transition hover:text-slate-900 dark:hover:text-white">{{ t("landing.footerPrivacy") }}</a>
        <a href="#contacto" class="transition hover:text-slate-900 dark:hover:text-white">{{ t("nav.contact") }}</a>
      </nav>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n";

const { t } = useI18n({ useScope: "global" });
const year = new Date().getFullYear();
</script>
