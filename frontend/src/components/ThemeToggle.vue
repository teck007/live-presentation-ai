<template>
  <button
    type="button"
    :aria-label="ariaLabel"
    :aria-pressed="isDark"
    :title="title"
    class="inline-flex items-center justify-center rounded-xl border border-slate-300/60 bg-white/70 p-2 text-slate-700 transition hover:bg-white dark:border-white/10 dark:bg-white/5 dark:text-slate-200 dark:hover:bg-white/10"
    @click="toggle"
  >
    <svg v-if="isDark" class="size-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M10 2a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0V3a1 1 0 0 1 1-1Zm4.24 2.76a1 1 0 0 1 1.42 0l.7.7a1 1 0 1 1-1.41 1.42l-.71-.71a1 1 0 0 1 0-1.41ZM18 9a1 1 0 0 1 0 2h-1a1 1 0 1 1 0-2h1ZM5.05 4.76a1 1 0 0 1 0 1.41l-.7.71a1 1 0 1 1-1.42-1.42l.71-.7a1 1 0 0 1 1.41 0ZM10 6a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm-7 3a1 1 0 0 1 0 2H2a1 1 0 1 1 0-2h1Zm12 0a1 1 0 0 1 0 2h-1a1 1 0 1 1 0-2h1ZM5.05 13.83a1 1 0 0 1 1.41 0l.71.7a1 1 0 1 1-1.42 1.42l-.7-.71a1 1 0 0 1 0-1.41Zm8.49 0a1 1 0 0 1 0 1.41l-.7.71a1 1 0 1 1-1.42-1.42l.71-.7a1 1 0 0 1 1.41 0ZM10 15a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0v-1a1 1 0 0 1 1-1Z" />
    </svg>
    <svg v-else class="size-5" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M16.5 13.5A7.5 7.5 0 0 1 6.5 3.5a.75.75 0 0 0-.9-.98A8.5 8.5 0 1 0 17.48 14.4a.75.75 0 0 0-.98-.9Z" />
    </svg>
  </button>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useI18n } from "vue-i18n";
import { useTheme } from "../composables/useTheme";

// Reusable a11y theme toggle. Ready for the future landing page.
const { resolved, toggle } = useTheme();
const { t } = useI18n({ useScope: "global" });

const isDark = computed(() => resolved.value === "dark");
const ariaLabel = computed(() =>
  isDark.value ? t("a11y.themeToLight") : t("a11y.themeToDark"),
);
const title = computed(() =>
  isDark.value ? t("a11y.themeDarkActive") : t("a11y.themeLightActive"),
);
</script>
