<template>
  <article class="flex h-full min-h-full flex-col items-center justify-center overflow-hidden bg-[var(--base,var(--slide-base))] p-8 text-center text-[var(--text,var(--slide-text))] md:p-12">
    <p v-if="kicker" class="line-clamp-1 kicker">{{ kicker }}</p>
    <h3 class="mt-2 line-clamp-2 h-display">{{ title }}</h3>
    <p v-if="subtitle" class="mt-4 line-clamp-3 max-w-2xl subtitle">{{ subtitle }}</p>
    <p v-else-if="text" class="mt-4 line-clamp-3 max-w-2xl subtitle">{{ text }}</p>
  </article>
</template>

<script setup lang="ts">
// Hero cover: centered opening or topic-change slide, no list content.
defineProps<{
  title: string;
  text: string;
  kicker?: string;
  subtitle?: string;
  keywords?: string[];
  bullets?: string[];
  cards?: unknown;
  stats?: unknown;
  chips?: unknown;
  steps?: unknown;
  code?: string;
  image?: string;
}>();
</script>
