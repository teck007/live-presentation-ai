<template>
  <article class="flex h-full min-h-full flex-col items-center justify-center overflow-hidden bg-[var(--base,var(--slide-base))] p-8 text-center text-[var(--text,var(--slide-text))] md:p-12">
    <span class="h-1 w-16 rounded-full bg-[var(--accent,var(--slide-accent))]" aria-hidden="true"></span>
    <h3 class="mt-4 line-clamp-2 h-slide">{{ title }}</h3>
    <p v-if="text" class="mt-3 line-clamp-3 max-w-xl subtitle">{{ text }}</p>
  </article>
</template>

<script setup lang="ts">
// Separator: full-bleed minimal break for pauses or section changes.
defineProps<{
  title: string;
  text: string;
  keywords?: string[];
  kicker?: string;
  subtitle?: string;
  bullets?: string[];
  cards?: unknown;
  stats?: unknown;
  chips?: unknown;
  steps?: unknown;
  code?: string;
  image?: string;
}>();
</script>
