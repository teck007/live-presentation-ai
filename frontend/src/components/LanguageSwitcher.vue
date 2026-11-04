<template>
  <div
    class="inline-flex items-center rounded-xl border border-slate-300/60 bg-white/70 p-0.5 text-xs font-semibold dark:border-white/10 dark:bg-white/5"
    role="group"
    :aria-label="t('a11y.language')"
  >
    <button
      v-for="code in supported"
      :key="code"
      type="button"
      :aria-pressed="code === locale"
      :aria-label="code === 'es' ? t('a11y.spanish') : t('a11y.english')"
      :title="code === 'es' ? t('a11y.spanish') : t('a11y.english')"
      class="rounded-lg px-2.5 py-1.5 uppercase tracking-wide transition"
      :class="
        code === locale
          ? 'bg-slate-900 text-white dark:bg-emerald-500 dark:text-slate-950'
          : 'text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white'
      "
      @click="setLanguage(code)"
    >
      {{ code }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from "vue-i18n";
import { useLanguage } from "../composables/useLanguage";

// Compact ES|EN switcher. Sits next to ThemeToggle in the navbar;
// the switch is reactive app-wide (no reload).
const { t } = useI18n({ useScope: "global" });
const { locale, supported, setLanguage } = useLanguage();
</script>
